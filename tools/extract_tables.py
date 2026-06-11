"""Extract tables from images as JSON using Vertex AI Gemini 3.1 Pro Preview.

Uses the google-genai SDK (the same code path as the GCP Console UI),
which supports gemini-3.1-pro-preview in this project.

Usage:
    python tools/extract_tables.py <image_path> [<image_path> ...]
    python tools/extract_tables.py --out out_dir img1.png img2.png

Requires:
    pip install google-genai python-dotenv
    gcloud auth application-default login
    gcloud auth application-default set-quota-project <PROJECT>

Honours HTTPS_PROXY / HTTP_PROXY for corporate-proxy egress.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from google import genai
from google.genai import types


PROMPT = """\
You are a precise data-extraction assistant.

Extract every table you can find in the supplied image as structured JSON.
Return ONLY a single JSON object (no prose, no markdown fences) with this shape:

{
  "tables": [
    {
      "title": "<table title or caption if present, else null>",
      "footnotes": ["<text of any footnote / annotation tied to the table>"],
      "headers": ["<column 1 header>", "<column 2 header>", ...],
      "rows": [
        { "<column 1 header>": "<cell>", "<column 2 header>": "<cell>", ... },
        ...
      ]
    }
  ]
}

Rules:
- Preserve cell text verbatim, including symbols like %, $, ~, **, +, -, .
- If a cell is empty, use an empty string "".
- If a header spans multiple sub-headers, flatten by joining with " - ".
- Do not invent data. If unsure of a character, use the most likely reading.
- Do not include rendered totals that are not visible in the image.
- Output strict JSON parseable by json.loads. No trailing commas. No comments.
"""


def load_config() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    for env in (here.parent / "tests" / "eval" / ".env", here / ".env"):
        if env.exists():
            load_dotenv(env)
            break

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("images", nargs="+", help="One or more image paths.")
    p.add_argument("--project", default=os.getenv("GCP_PROJECT_ID"),
                   help="GCP project ID. Defaults to GCP_PROJECT_ID env.")
    p.add_argument("--location", default=os.getenv("GCP_REGION", "us-central1"),
                   help="Vertex AI location. gemini-2.5-* are regional; "
                        "gemini-3.x previews live at 'global' and require "
                        "VPC-SC-allowed egress to aiplatform.googleapis.com.")
    p.add_argument("--model", default=os.getenv("VISION_MODEL", "gemini-2.5-flash"),
                   help="Vertex AI multimodal model id. Use gemini-2.5-pro for "
                        "higher accuracy, gemini-2.5-flash for speed. "
                        "gemini-3.x previews need --location global.")
    p.add_argument("--out", default=None, help="Optional output directory; "
                   "writes <stem>.json per image. If omitted, prints to stdout.")
    p.add_argument("--proxy", default=os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY"),
                   help="HTTPS proxy required behind VPC-SC corporate perimeter.")
    cfg = p.parse_args()
    if not cfg.project:
        sys.exit("ERROR: --project not provided and GCP_PROJECT_ID not set.")
    if cfg.proxy:
        os.environ["HTTPS_PROXY"] = cfg.proxy
        os.environ["HTTP_PROXY"] = cfg.proxy
    return cfg


def guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/png"


def build_config(model: str) -> types.GenerateContentConfig:
    safety = [
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
    ]
    kwargs: dict = dict(
        temperature=0.0,
        max_output_tokens=65535,
        response_mime_type="application/json",
        safety_settings=safety,
    )
    # thinking_level is a Gemini 3.x-only feature; 2.5 rejects it with 400.
    if model.startswith("gemini-3"):
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level="HIGH")
    return types.GenerateContentConfig(**kwargs)


def extract_from_image(client: genai.Client, model: str, path: Path) -> dict:
    """Send one image to the model and return the parsed JSON tables payload."""
    image_part = types.Part.from_bytes(
        data=path.read_bytes(),
        mime_type=guess_mime(path),
    )
    contents = [
        types.Content(role="user", parts=[image_part, types.Part.from_text(text=PROMPT)]),
    ]

    chunks: list[str] = []
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=build_config(model),
    ):
        if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
            continue
        if chunk.text:
            chunks.append(chunk.text)

    text = "".join(chunks).strip()
    if not text:
        raise RuntimeError("Model returned no text.")

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        cleaned = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"Model did not return valid JSON. First 500 chars:\n{text[:500]}"
            ) from exc


def make_client(cfg: argparse.Namespace) -> genai.Client:
    # ADC-based auth (no API key); same code path as the GCP Console UI export
    # but using application default credentials instead of GOOGLE_CLOUD_API_KEY.
    return genai.Client(vertexai=True, project=cfg.project, location=cfg.location)


def main() -> None:
    cfg = load_config()
    print(f"Project={cfg.project} Location={cfg.location} Model={cfg.model}")
    if cfg.proxy:
        print(f"Proxy={cfg.proxy}")

    client = make_client(cfg)

    out_dir: Path | None = Path(cfg.out) if cfg.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for raw in cfg.images:
        path = Path(raw)
        if not path.exists():
            print(f"[skip] {path} (not found)", file=sys.stderr)
            continue
        print(f"\n--- {path.name} ({path.stat().st_size} bytes) ---")
        try:
            data = extract_from_image(client, cfg.model, path)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {path.name}: {exc}", file=sys.stderr)
            continue

        out_text = json.dumps(data, indent=2, ensure_ascii=False)
        if out_dir:
            out_path = out_dir / f"{path.stem}.json"
            out_path.write_text(out_text, encoding="utf-8")
            n_tables = len(data.get("tables", []))
            n_rows = sum(len(t.get("rows", [])) for t in data.get("tables", []))
            print(f"  -> {out_path}  ({n_tables} tables, {n_rows} rows total)")
        else:
            print(out_text)


if __name__ == "__main__":
    main()
