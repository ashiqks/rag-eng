"""Vertex AI Search evaluation harness.

Reads a CSV of (question_id, question, reference_answer), queries the
Vertex AI Search engine for each row in parallel, then scores the responses
with Vertex AI Gen AI Evaluation Service across 5 metrics:

  * faithfulness        -> groundedness (built-in)
  * answer_relevancy    -> question_answering_relevance (built-in)
  * answer_correctness  -> question_answering_correctness (built-in)
  * context_precision   -> custom PointwiseMetric (see metrics.py)
  * context_recall      -> custom PointwiseMetric (see metrics.py)

All configuration is loaded from environment variables (see .env.example) and
can be overridden via CLI flags.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.auth
import google.auth.transport.requests
import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

import vertexai
from vertexai.evaluation import EvalTask

from configs import apply_overlay, get_config, list_configs
from metrics import (
    build_answer_correctness,
    build_answer_relevancy,
    build_context_precision,
    build_context_recall,
    faithfulness_metric,
)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    load_dotenv(here / ".env")

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gcp-project-id", default=os.getenv("GCP_PROJECT_ID"))
    p.add_argument("--gcp-region", default=os.getenv("GCP_REGION", "us-central1"))
    p.add_argument("--search-project-id", default=os.getenv("SEARCH_PROJECT_ID"))
    p.add_argument("--search-location", default=os.getenv("SEARCH_LOCATION", "global"))
    p.add_argument("--search-collection", default=os.getenv("SEARCH_COLLECTION", "default_collection"))
    p.add_argument("--search-engine-id", default=os.getenv("SEARCH_ENGINE_ID"))
    p.add_argument("--search-serving-config", default=os.getenv("SEARCH_SERVING_CONFIG", "default_search"))
    p.add_argument("--judge-model", default=os.getenv("JUDGE_MODEL", "gemini-2.5-pro"))
    p.add_argument("--concurrency", type=int, default=int(os.getenv("EVAL_CONCURRENCY", "8")))
    p.add_argument(
        "--questions-csv",
        default=os.getenv("EVAL_QUESTIONS_CSV", str(here / "eval_questions.csv")),
    )
    p.add_argument(
        "--runs-dir",
        default=os.getenv("EVAL_RUNS_DIR", str(here / "runs")),
    )
    p.add_argument("--proxy", default=os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY"),
                   help="HTTPS proxy (e.g. http://proxy.example.com:8080). "
                        "Required if VPC-SC perimeter allow-lists a corporate proxy.")
    p.add_argument(
        "--config",
        default=os.getenv("EVAL_CONFIG", "preview+prompt"),
        choices=list_configs(),
        help=(
            "Named search/answer configuration to apply (see configs.py). "
            "'preview+prompt' is the sweep winner; 'baseline' reproduces "
            "the historical default request body."
        ),
    )
    p.add_argument("--dry-run", action="store_true", help="Query the app but skip Vertex Eval scoring.")
    cfg = p.parse_args()

    missing = [k for k in ("gcp_project_id", "search_project_id", "search_engine_id") if not getattr(cfg, k)]
    if missing:
        sys.exit(f"ERROR: missing required config: {missing}. Set env vars or pass CLI flags.")
    cfg.search_project_id = cfg.search_project_id or cfg.gcp_project_id

    # Resolve I/O paths so the harness works regardless of CWD. Relative
    # paths are resolved against (1) the current working directory, then
    # (2) the script directory (tests/eval/). For backwards compatibility,
    # paths like "tests/eval/foo" launched from inside tests/eval are
    # also stripped to just "foo".
    def _resolve_path(value: str, must_exist: bool) -> str:
        v = Path(value)
        candidates: list[Path] = []
        if v.is_absolute():
            candidates.append(v)
        else:
            candidates.append(Path.cwd() / v)         # relative to CWD
            candidates.append(here / v)               # relative to script dir
            # If the value starts with the script dir's tail (e.g. "tests/eval/..."
            # while we're already inside tests/eval), strip the duplicate prefix.
            tail = list(here.parts)[-2:]              # ('tests', 'eval')
            if list(v.parts)[:len(tail)] == tail:
                candidates.append(here / Path(*v.parts[len(tail):]))
            candidates.append(here / v.name)          # last resort: basename only
        if must_exist:
            for c in candidates:
                if c.exists():
                    return str(c.resolve())
            sys.exit(f"ERROR: file not found: {value} (looked in {[str(c) for c in candidates]})")
        # Output dir: prefer the script-dir candidate so we don't pollute CWD.
        for c in candidates:
            if c.exists():
                return str(c.resolve())
        # Nothing exists yet - default to the script-dir-anchored candidate.
        return str((here / v if not v.is_absolute() else v).resolve())

    cfg.questions_csv = _resolve_path(cfg.questions_csv, must_exist=True)
    cfg.runs_dir = _resolve_path(cfg.runs_dir, must_exist=False)

    if cfg.proxy:
        os.environ["HTTPS_PROXY"] = cfg.proxy
        os.environ["HTTP_PROXY"] = cfg.proxy
        print(f"Using proxy: {cfg.proxy}")
    return cfg


# ---------------------------------------------------------------------------
# Vertex AI Search :answer caller
# ---------------------------------------------------------------------------

def get_access_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def build_answer_url(cfg: argparse.Namespace) -> str:
    return (
        f"https://discoveryengine.googleapis.com/v1/projects/{cfg.search_project_id}"
        f"/locations/{cfg.search_location}/collections/{cfg.search_collection}"
        f"/engines/{cfg.search_engine_id}/servingConfigs/{cfg.search_serving_config}:answer"
    )


def ask(
    url: str,
    token: str,
    project_id: str,
    question: str,
    config_name: str = "baseline",
) -> dict[str, Any]:
    """Call the Vertex AI Search :answer endpoint and return parsed response."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-User-Project": project_id,
    }
    base_body: dict[str, Any] = {
        "query": {"text": question},
        "answerGenerationSpec": {
            "includeCitations": True,
            "ignoreAdversarialQuery": True,
            "ignoreNonAnswerSeekingQuery": False,
        },
    }
    body = apply_overlay(base_body, config_name)
    t0 = time.perf_counter()
    r = requests.post(url, headers=headers, json=body, timeout=120)
    latency_ms = int((time.perf_counter() - t0) * 1000)
    if not r.ok:
        snippet = r.text[:500].replace("\n", " ")
        raise RuntimeError(f"HTTP {r.status_code}: {snippet}")
    return {"resp": r.json(), "latency_ms": latency_ms}


def _chunk_content(ref: dict[str, Any]) -> str:
    ci = ref.get("chunkInfo")
    if isinstance(ci, dict) and ci.get("content"):
        return ci["content"]
    udi = ref.get("unstructuredDocumentInfo") or {}
    for cc in udi.get("chunkContents") or []:
        if isinstance(cc, dict) and cc.get("content"):
            return cc["content"]
    return ""


def _chunk_uri(ref: dict[str, Any]) -> str:
    meta = (ref.get("chunkInfo") or {}).get("documentMetadata") or {}
    return meta.get("uri") or (ref.get("unstructuredDocumentInfo") or {}).get("uri") or ""


def extract_answer_and_context(api_resp: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    """Return (answer_text, context_chunks, citation_uris)."""
    ans = api_resp.get("answer", {})
    chunks: list[str] = []
    uris: list[str] = []
    for ref in ans.get("references", []):
        content = _chunk_content(ref)
        if content:
            chunks.append(content)
        uri = _chunk_uri(ref)
        if uri:
            uris.append(uri)
    return ans.get("answerText", ""), chunks, uris


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

def collect_responses(cfg: argparse.Namespace, questions: pd.DataFrame) -> pd.DataFrame:
    url = build_answer_url(cfg)
    token = get_access_token()

    def _one(row: pd.Series) -> dict[str, Any]:
        try:
            api = ask(url, token, cfg.search_project_id, row["question"], cfg.config)
            answer, chunks, citations = extract_answer_and_context(api["resp"])
            return {
                "question_id": row["question_id"],
                "question": row["question"],
                "reference_answer": row["reference_answer"],
                "response": answer,
                "context": "\n\n---\n\n".join(chunks),
                "context_chunks": chunks,
                "citations": "; ".join(citations),
                "latency_ms": api["latency_ms"],
                "error": "",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "question_id": row["question_id"],
                "question": row["question"],
                "reference_answer": row["reference_answer"],
                "response": "",
                "context": "",
                "context_chunks": [],
                "citations": "",
                "latency_ms": -1,
                "error": str(exc)[:500],
            }

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=cfg.concurrency) as ex:
        futures = [ex.submit(_one, row) for _, row in questions.iterrows()]
        for f in tqdm(as_completed(futures), total=len(futures), desc="Querying app"):
            rows.append(f.result())

    return pd.DataFrame(rows).sort_values("question_id").reset_index(drop=True)


def score_with_vertex_eval(cfg: argparse.Namespace, responses: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run Vertex AI Eval Service on the responses DataFrame."""
    vertexai.init(project=cfg.gcp_project_id, location=cfg.gcp_region)

    eval_df = responses[["question_id", "question", "reference_answer", "response", "context"]].copy()
    eval_df = eval_df.rename(columns={"question": "prompt", "reference_answer": "reference"})

    metrics = [
        faithfulness_metric(),
        build_answer_relevancy(),
        build_answer_correctness(),
        build_context_precision(),
        build_context_recall(),
    ]

    task = EvalTask(dataset=eval_df, metrics=metrics)
    result = task.evaluate()
    metrics_df: pd.DataFrame = result.metrics_table

    rename = {
        "faithfulness/score": "faithfulness",
        "faithfulness/explanation": "faithfulness_explanation",
        "answer_relevancy/score": "answer_relevancy",
        "answer_relevancy/explanation": "answer_relevancy_explanation",
        "answer_correctness/score": "answer_correctness",
        "answer_correctness/explanation": "answer_correctness_explanation",
        "context_precision/score": "context_precision",
        "context_precision/explanation": "context_precision_explanation",
        "context_recall/score": "context_recall",
        "context_recall/explanation": "context_recall_explanation",
    }
    metrics_df = metrics_df.rename(columns={k: v for k, v in rename.items() if k in metrics_df.columns})

    # Drop columns from metrics_df that are already in responses to avoid duplicates after concat.
    metrics_df = metrics_df.drop(
        columns=[c for c in metrics_df.columns if c in responses.columns],
        errors="ignore",
    )

    return pd.concat(
        [responses.reset_index(drop=True), metrics_df.reset_index(drop=True)],
        axis=1,
    ), result.summary_metrics


def main() -> None:
    cfg = load_config()

    questions = pd.read_csv(cfg.questions_csv)
    required = {"question_id", "question", "reference_answer"}
    if not required.issubset(questions.columns):
        sys.exit(f"ERROR: input CSV must contain columns {required}")

    print(f"Loaded {len(questions)} questions from {cfg.questions_csv}")

    responses = collect_responses(cfg, questions)
    print(f"Got {(responses['error'] == '').sum()} successful responses, "
          f"{(responses['error'] != '').sum()} errors.")

    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    run_id = f"{run_ts}_{cfg.config}"
    run_dir = Path(cfg.runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    responses.drop(columns=["context_chunks"]).to_csv(run_dir / "responses.csv", index=False)
    config_meta = get_config(cfg.config)
    (run_dir / "run_config.json").write_text(
        json.dumps(
            {
                **{k: v for k, v in vars(cfg).items() if not k.startswith("_")},
                "config_name": cfg.config,
                "config_description": config_meta.get("description", ""),
                "config_model_label": config_meta.get("model_label", ""),
                "request_overlay": config_meta.get("request_overlay", {}),
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    if cfg.dry_run:
        print(f"[dry-run] Skipping metric scoring. See {run_dir}/responses.csv")
        return

    print(f"Scoring {len(responses)} responses with Vertex AI Eval Service "
          f"(region: {cfg.gcp_region}, autorater: server-side default)...")
    scored, summary = score_with_vertex_eval(cfg, responses)
    scored.drop(columns=["context_chunks"], errors="ignore").to_csv(run_dir / "results.csv", index=False)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    print(f"\nRun complete: {run_dir}")
    print("\nMetric means:")
    for k, v in summary.items():
        if isinstance(v, (int, float)):
            print(f"  {k:50s} {v:.3f}")


if __name__ == "__main__":
    main()
