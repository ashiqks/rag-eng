"""Multi-config sweep driver for the eval harness.

Runs `run_eval.py` once per named configuration against the same questions
CSV, then aggregates the per-run `results.csv` and `summary.json` files
into a side-by-side comparison.

Outputs (under `runs/sweep_<UTC-timestamp>/`):
  - comparison.csv          one row per (question_id, config), all metrics
  - comparison_summary.csv  one row per config: metric means + delta vs baseline
  - comparison.md           human-readable report

Usage:
  python sweep.py                           # all configs, default questions
  python sweep.py --configs baseline,pro-2.5+prompt
  python sweep.py --questions-csv my_set.csv
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from configs import get_config, list_configs


HERE = Path(__file__).resolve().parent

METRIC_COLS = [
    "faithfulness",
    "answer_relevancy",
    "answer_correctness",
    "context_precision",
    "context_recall",
]

SUMMARY_METRIC_COLS = [f"{c}/mean" for c in METRIC_COLS]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--configs",
        default=",".join(list_configs()),
        help=(
            "Comma-separated config names to run. Default: all. "
            f"Available: {','.join(list_configs())}."
        ),
    )
    p.add_argument(
        "--questions-csv",
        default=None,
        help="Questions CSV. If unset, uses the default from run_eval.py.",
    )
    p.add_argument(
        "--runs-dir",
        default=str(HERE / "runs"),
        help="Where individual config runs are written. Default: ./runs.",
    )
    p.add_argument(
        "--baseline-config",
        default="baseline",
        help="Config name to use as the delta reference. Default: baseline.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Vertex Eval scoring (only collects responses).",
    )
    p.add_argument(
        "--python",
        default=sys.executable,
        help="Python interpreter to invoke run_eval.py with.",
    )
    return p.parse_args()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def run_one(
    py: str,
    config_name: str,
    questions_csv: str | None,
    runs_dir: str,
    dry_run: bool,
) -> Path:
    """Invoke run_eval.py for one config; return the per-run output dir."""
    before = _snapshot_run_dirs(runs_dir, config_name)

    cmd = [py, str(HERE / "run_eval.py"), "--config", config_name, "--runs-dir", runs_dir]
    if questions_csv:
        cmd += ["--questions-csv", questions_csv]
    if dry_run:
        cmd.append("--dry-run")

    print(f"\n=== Running config: {config_name} ===")
    print("  $ " + " ".join(cmd))
    res = subprocess.run(cmd, cwd=HERE, env=os.environ.copy(), check=False)
    if res.returncode != 0:
        print(f"  [warn] config {config_name} exited with code {res.returncode}")

    after = _snapshot_run_dirs(runs_dir, config_name)
    new_dirs = sorted(after - before)
    if not new_dirs:
        raise RuntimeError(f"No new run dir was created for config '{config_name}'")
    return Path(new_dirs[-1])


def _snapshot_run_dirs(runs_dir: str, config_name: str) -> set[str]:
    p = Path(runs_dir)
    if not p.exists():
        return set()
    return {str(d) for d in p.iterdir() if d.is_dir() and d.name.endswith(f"_{config_name}")}


def collect_results(per_config_dirs: dict[str, Path]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the wide-format comparison + per-config summary."""
    rows: list[pd.DataFrame] = []
    summary_rows: list[dict] = []

    for cfg_name, run_dir in per_config_dirs.items():
        results_csv = run_dir / "results.csv"
        summary_json = run_dir / "summary.json"

        if results_csv.exists():
            df = pd.read_csv(results_csv)
            df["config"] = cfg_name
            rows.append(df)
        else:
            print(f"  [warn] {results_csv} missing (dry-run or eval failure)")

        if summary_json.exists():
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
            summary_rows.append(
                {"config": cfg_name, **{k: v for k, v in summary.items() if isinstance(v, (int, float))}}
            )

    comparison = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    summary_df = pd.DataFrame(summary_rows) if summary_rows else pd.DataFrame()
    return comparison, summary_df


def add_baseline_deltas(summary_df: pd.DataFrame, baseline_config: str) -> pd.DataFrame:
    if summary_df.empty or baseline_config not in summary_df["config"].values:
        return summary_df
    base = summary_df.loc[summary_df["config"] == baseline_config].iloc[0]
    out = summary_df.copy()
    for col in summary_df.columns:
        if col == "config" or not pd.api.types.is_numeric_dtype(summary_df[col]):
            continue
        out[f"{col}_delta_vs_baseline"] = summary_df[col] - base[col]
    return out


def write_markdown_report(
    out_dir: Path,
    summary_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
    baseline_config: str,
    questions_csv: str | None,
) -> None:
    lines: list[str] = []
    lines.append("# Eval sweep comparison")
    lines.append("")
    lines.append(f"- Generated: {_utc_now()}")
    lines.append(f"- Questions CSV: `{questions_csv or '(default from run_eval.py)'}`")
    lines.append(f"- Baseline config: `{baseline_config}`")
    lines.append(f"- Configs run: {', '.join(summary_df['config'].tolist()) if not summary_df.empty else '(none — dry-run?)'}")
    lines.append("")

    if not summary_df.empty:
        score_cols = [c for c in SUMMARY_METRIC_COLS if c in summary_df.columns]
        if score_cols:
            lines.append("## Per-config metric means")
            lines.append("")
            lines.append(_md_table(summary_df, ["config"] + score_cols))
            lines.append("")

        delta_cols = [f"{c}_delta_vs_baseline" for c in score_cols if f"{c}_delta_vs_baseline" in summary_df.columns]
        if delta_cols:
            lines.append(f"## Delta vs `{baseline_config}` (positive = improvement)")
            lines.append("")
            lines.append(_md_table(summary_df, ["config"] + delta_cols))
            lines.append("")

        lines.append("## Recommendation")
        lines.append("")
        rec = _pick_winner(summary_df, baseline_config)
        if rec:
            lines.append(rec)
        else:
            lines.append("_Insufficient data to recommend a winner._")
        lines.append("")

    if not comparison_df.empty:
        per_q_cols = ["question_id", "config"] + [c for c in METRIC_COLS if c in comparison_df.columns]
        if per_q_cols:
            lines.append("## Per-question scores (long form sample)")
            lines.append("")
            sample = comparison_df[per_q_cols].sort_values(["question_id", "config"])
            lines.append(_md_table(sample.head(50), per_q_cols))
            if len(sample) > 50:
                lines.append("")
                lines.append(f"_(showing first 50 of {len(sample)} rows; full data in `comparison.csv`)_")
            lines.append("")

    (out_dir / "comparison.md").write_text("\n".join(lines), encoding="utf-8")


def _md_table(df: pd.DataFrame, cols: list[str]) -> str:
    cols = [c for c in cols if c in df.columns]
    if not cols:
        return "_no columns to display_"
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, r in df[cols].iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append(f"{v:+.3f}" if c.endswith("_delta_vs_baseline") else f"{v:.3f}")
            else:
                cells.append(str(v))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep] + rows)


def _pick_winner(summary_df: pd.DataFrame, baseline_config: str) -> str:
    score_cols = [c for c in SUMMARY_METRIC_COLS if c in summary_df.columns]
    primary = "answer_correctness/mean"
    secondary = "faithfulness/mean"
    if not score_cols or primary not in score_cols:
        return ""
    df = summary_df.copy()
    if secondary in df.columns:
        df["__score"] = df[primary].fillna(0) + 0.5 * df[secondary].fillna(0)
    else:
        df["__score"] = df[primary].fillna(0)
    df = df.sort_values("__score", ascending=False)
    winner = df.iloc[0]["config"]
    if winner == baseline_config:
        return f"Baseline (`{baseline_config}`) was not beaten by any challenger on `answer_correctness × faithfulness`."
    base = summary_df.loc[summary_df["config"] == baseline_config].iloc[0] if baseline_config in summary_df["config"].values else None
    win_row = df.iloc[0]
    parts = [f"Recommended config: **`{winner}`**."]
    if base is not None:
        for col in [primary, secondary, "context_recall/mean"]:
            if col in summary_df.columns:
                delta = win_row[col] - base[col]
                parts.append(f"  - {col}: {win_row[col]:.3f} (baseline {base[col]:.3f}, delta {delta:+.3f})")
    return "\n".join(parts)


def main() -> None:
    args = parse_args()
    config_names = [c.strip() for c in args.configs.split(",") if c.strip()]
    for c in config_names:
        get_config(c)  # validates name, raises if unknown

    sweep_id = f"sweep_{_utc_now()}"
    out_dir = Path(args.runs_dir) / sweep_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Sweep output: {out_dir}")
    print(f"Configs: {config_names}")

    per_config_dirs: dict[str, Path] = {}
    for cfg_name in config_names:
        try:
            per_config_dirs[cfg_name] = run_one(
                args.python, cfg_name, args.questions_csv, args.runs_dir, args.dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  [error] config {cfg_name} failed: {exc}")

    comparison, summary_df = collect_results(per_config_dirs)
    summary_df = add_baseline_deltas(summary_df, args.baseline_config)

    if not comparison.empty:
        comparison.to_csv(out_dir / "comparison.csv", index=False)
    if not summary_df.empty:
        summary_df.to_csv(out_dir / "comparison_summary.csv", index=False)

    (out_dir / "sweep_manifest.json").write_text(
        json.dumps(
            {
                "sweep_id": sweep_id,
                "questions_csv": args.questions_csv,
                "configs": config_names,
                "baseline_config": args.baseline_config,
                "per_config_run_dirs": {k: str(v) for k, v in per_config_dirs.items()},
                "dry_run": args.dry_run,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    write_markdown_report(out_dir, summary_df, comparison, args.baseline_config, args.questions_csv)

    print(f"\nSweep complete: {out_dir}")
    if not summary_df.empty:
        print("\nPer-config means:")
        for _, r in summary_df.iterrows():
            cells = [f"{r['config']:25s}"]
            for c in SUMMARY_METRIC_COLS:
                if c in summary_df.columns:
                    cells.append(f"{c.split('/')[0]}={r[c]:.2f}")
            print("  " + " ".join(cells))


if __name__ == "__main__":
    main()
