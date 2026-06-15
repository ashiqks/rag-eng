"""Compare the user's original eval run (`Downloads/results.csv`) against the
winning `preview+prompt` run, produce a markdown + CSV report.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

OLD_CSV = Path(r"C:\Users\vn5a4j1\Downloads\results.csv")
NEW_CSV = Path("runs/2026-06-11T11-35-58Z_preview+prompt/results.csv")
OUT_DIR = Path("runs/first_vs_latest_comparison")
METRICS = ["faithfulness", "answer_relevancy", "answer_correctness", "context_precision", "context_recall"]


def md_table(df: pd.DataFrame, cols: list[str]) -> str:
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, r in df[cols].iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append(f"{v:+.2f}" if c.startswith("delta_") else f"{v:.2f}")
            else:
                cells.append(str(v))
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, sep] + rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    old = pd.read_csv(OLD_CSV)
    new = pd.read_csv(NEW_CSV)

    old_keep = old[["question_id", "question", "latency_ms"] + METRICS].copy()
    new_keep = new[["question_id", "latency_ms"] + METRICS].copy()
    old_keep.columns = ["question_id", "question", "latency_first"] + [f"{m}_first" for m in METRICS]
    new_keep.columns = ["question_id", "latency_latest"] + [f"{m}_latest" for m in METRICS]
    merged = old_keep.merge(new_keep, on="question_id")
    for m in METRICS:
        merged[f"delta_{m}"] = merged[f"{m}_latest"] - merged[f"{m}_first"]
    merged["delta_latency_ms"] = merged["latency_latest"] - merged["latency_first"]

    merged.to_csv(OUT_DIR / "first_vs_latest_per_question.csv", index=False)

    means = pd.DataFrame({
        "metric": METRICS,
        "first_mean": [old[m].mean() for m in METRICS],
        "latest_mean": [new[m].mean() for m in METRICS],
    })
    means["delta_mean"] = means["latest_mean"] - means["first_mean"]
    means.to_csv(OUT_DIR / "first_vs_latest_summary.csv", index=False)

    lines: list[str] = []
    lines.append("# First eval run vs latest winner (preview+prompt)")
    lines.append("")
    lines.append("- **First** = `C:\\Users\\vn5a4j1\\Downloads\\results.csv` (original eval delivered to client; baseline serving config + default model).")
    lines.append("- **Latest** = `runs/2026-06-11T11-35-58Z_preview+prompt/results.csv` (sweep-winner config: `preview` model + strict preamble).")
    lines.append("- Same 15 questions (Q-001 … Q-015), same 5 PointwiseMetrics scored by Vertex AI Eval Service.")
    lines.append("- All scores on a 1–5 scale; positive `Δ` = improvement.")
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    lines.append(md_table(means, ["metric", "first_mean", "latest_mean", "delta_mean"]))
    lines.append("")

    lat = pd.DataFrame({
        "metric": ["latency_ms (mean)"],
        "first_mean": [old["latency_ms"].mean()],
        "latest_mean": [new["latency_ms"].mean()],
    })
    lat["delta_mean"] = lat["latest_mean"] - lat["first_mean"]
    lines.append("### Latency")
    lines.append("")
    lines.append(md_table(lat, ["metric", "first_mean", "latest_mean", "delta_mean"]))
    lines.append("")

    lines.append("## Per-question scores")
    lines.append("")
    lines.append("Compact: `first → latest (Δ)` per metric. F=faithfulness, R=relevancy, "
                 "C=correctness, P=context_precision, Re=context_recall.")
    lines.append("")
    rows: list[str] = []
    rows.append("| Q | F | R | C | P | Re |")
    rows.append("| --- | --- | --- | --- | --- | --- |")
    for _, r in merged.iterrows():
        cells = [r["question_id"]]
        for m in METRICS:
            d = r[f"delta_{m}"]
            sign = "+" if d > 0 else ""
            cells.append(f"{r[f'{m}_first']:.0f}→{r[f'{m}_latest']:.0f} ({sign}{d:.0f})")
        rows.append("| " + " | ".join(cells) + " |")
    lines.append("\n".join(rows))
    lines.append("")

    lines.append("## Per-question correctness (focused)")
    lines.append("")
    focus_cols = ["question_id", "answer_correctness_first", "answer_correctness_latest", "delta_answer_correctness", "context_recall_first", "context_recall_latest", "delta_context_recall"]
    lines.append(md_table(merged, focus_cols))
    lines.append("")

    n = len(merged)
    wins = (merged["delta_answer_correctness"] > 0).sum()
    losses = (merged["delta_answer_correctness"] < 0).sum()
    ties = n - wins - losses
    recall_wins = (merged["delta_context_recall"] > 0).sum()
    recall_losses = (merged["delta_context_recall"] < 0).sum()

    lines.append("## Win/loss/tie")
    lines.append("")
    lines.append(f"- `answer_correctness`: latest wins on **{wins}/{n}**, loses on {losses}/{n}, ties on {ties}/{n}.")
    lines.append(f"- `context_recall`: latest wins on **{recall_wins}/{n}**, loses on {recall_losses}/{n}.")

    biggest_corr = merged.sort_values("delta_answer_correctness", ascending=False)
    biggest_rec = merged.sort_values("delta_context_recall", ascending=False)
    lines.append("")
    lines.append("**Top correctness gains:** " + ", ".join(
        f"{r['question_id']} ({r['delta_answer_correctness']:+.0f})" for _, r in biggest_corr.head(3).iterrows()
    ))
    lines.append("")
    lines.append("**Largest correctness regressions:** " + ", ".join(
        f"{r['question_id']} ({r['delta_answer_correctness']:+.0f})" for _, r in biggest_corr.tail(3).iterrows()
    ))
    lines.append("")
    lines.append("**Top recall gains:** " + ", ".join(
        f"{r['question_id']} ({r['delta_context_recall']:+.0f})" for _, r in biggest_rec.head(3).iterrows()
    ))
    lines.append("")

    (OUT_DIR / "first_vs_latest.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote: {OUT_DIR}/first_vs_latest.md")
    print(f"       {OUT_DIR}/first_vs_latest_summary.csv")
    print(f"       {OUT_DIR}/first_vs_latest_per_question.csv")
    print()
    print("=== Aggregate ===")
    print(means.to_string(index=False))
    print()
    print(f"Wins on correctness: {wins}/{n}, Losses: {losses}/{n}, Ties: {ties}/{n}")
    print(f"Wins on recall:      {recall_wins}/{n}, Losses: {recall_losses}/{n}")


if __name__ == "__main__":
    main()
