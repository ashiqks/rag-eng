# First eval run vs latest winner (preview+prompt)

- **First** = `C:\Users\vn5a4j1\Downloads\results.csv` (original eval delivered to client; baseline serving config + default model).
- **Latest** = `runs/2026-06-11T11-35-58Z_preview+prompt/results.csv` (sweep-winner config: `preview` model + strict preamble).
- Same 15 questions (Q-001 … Q-015), same 5 PointwiseMetrics scored by Vertex AI Eval Service.
- All scores on a 1–5 scale; positive `Δ` = improvement.

## Aggregate

| metric | first_mean | latest_mean | delta_mean |
| --- | --- | --- | --- |
| faithfulness | 4.20 | 4.07 | -0.13 |
| answer_relevancy | 4.73 | 4.87 | +0.13 |
| answer_correctness | 2.00 | 2.40 | +0.40 |
| context_precision | 4.47 | 4.40 | -0.07 |
| context_recall | 3.33 | 3.53 | +0.20 |

### Latency

| metric | first_mean | latest_mean | delta_mean |
| --- | --- | --- | --- |
| latency_ms (mean) | 8594.47 | 4670.27 | -3924.20 |

## Per-question scores

Compact: `first → latest (Δ)` per metric. F=faithfulness, R=relevancy, C=correctness, P=context_precision, Re=context_recall.

| Q | F | R | C | P | Re |
| --- | --- | --- | --- | --- | --- |
| Q-001 | 3→3 (0) | 5→5 (0) | 2→2 (0) | 5→4 (-1) | 2→2 (0) |
| Q-002 | 4→4 (0) | 5→5 (0) | 2→2 (0) | 5→4 (-1) | 5→4 (-1) |
| Q-003 | 5→5 (0) | 5→5 (0) | 2→2 (0) | 5→5 (0) | 3→5 (+2) |
| Q-004 | 4→3 (-1) | 5→5 (0) | 2→2 (0) | 5→5 (0) | 3→3 (0) |
| Q-005 | 5→4 (-1) | 5→5 (0) | 2→3 (+1) | 5→5 (0) | 5→4 (-1) |
| Q-006 | 5→5 (0) | 5→5 (0) | 3→3 (0) | 5→5 (0) | 5→5 (0) |
| Q-007 | 5→4 (-1) | 5→5 (0) | 3→3 (0) | 5→5 (0) | 5→4 (-1) |
| Q-008 | 5→3 (-2) | 4→3 (-1) | 1→1 (0) | 4→3 (-1) | 2→3 (+1) |
| Q-009 | 5→5 (0) | 5→5 (0) | 3→3 (0) | 5→5 (0) | 5→5 (0) |
| Q-010 | 4→5 (+1) | 5→5 (0) | 1→2 (+1) | 5→5 (0) | 1→3 (+2) |
| Q-011 | 3→5 (+2) | 4→5 (+1) | 2→5 (+3) | 4→5 (+1) | 2→5 (+3) |
| Q-012 | 5→4 (-1) | 5→5 (0) | 2→2 (0) | 5→5 (0) | 5→4 (-1) |
| Q-013 | 4→5 (+1) | 5→5 (0) | 2→2 (0) | 2→2 (0) | 3→3 (0) |
| Q-014 | 3→4 (+1) | 5→5 (0) | 1→2 (+1) | 5→5 (0) | 1→1 (0) |
| Q-015 | 3→2 (-1) | 3→5 (+2) | 2→2 (0) | 2→3 (+1) | 3→2 (-1) |

## Per-question correctness (focused)

| question_id | answer_correctness_first | answer_correctness_latest | delta_answer_correctness | context_recall_first | context_recall_latest | delta_context_recall |
| --- | --- | --- | --- | --- | --- | --- |
| Q-001 | 2.00 | 2.00 | +0.00 | 2.00 | 2.00 | +0.00 |
| Q-002 | 2.00 | 2.00 | +0.00 | 5.00 | 4.00 | -1.00 |
| Q-003 | 2.00 | 2.00 | +0.00 | 3.00 | 5.00 | +2.00 |
| Q-004 | 2.00 | 2.00 | +0.00 | 3.00 | 3.00 | +0.00 |
| Q-005 | 2.00 | 3.00 | +1.00 | 5.00 | 4.00 | -1.00 |
| Q-006 | 3.00 | 3.00 | +0.00 | 5.00 | 5.00 | +0.00 |
| Q-007 | 3.00 | 3.00 | +0.00 | 5.00 | 4.00 | -1.00 |
| Q-008 | 1.00 | 1.00 | +0.00 | 2.00 | 3.00 | +1.00 |
| Q-009 | 3.00 | 3.00 | +0.00 | 5.00 | 5.00 | +0.00 |
| Q-010 | 1.00 | 2.00 | +1.00 | 1.00 | 3.00 | +2.00 |
| Q-011 | 2.00 | 5.00 | +3.00 | 2.00 | 5.00 | +3.00 |
| Q-012 | 2.00 | 2.00 | +0.00 | 5.00 | 4.00 | -1.00 |
| Q-013 | 2.00 | 2.00 | +0.00 | 3.00 | 3.00 | +0.00 |
| Q-014 | 1.00 | 2.00 | +1.00 | 1.00 | 1.00 | +0.00 |
| Q-015 | 2.00 | 2.00 | +0.00 | 3.00 | 2.00 | -1.00 |

## Win/loss/tie

- `answer_correctness`: latest wins on **4/15**, loses on 0/15, ties on 11/15.
- `context_recall`: latest wins on **4/15**, loses on 5/15.

**Top correctness gains:** Q-011 (+3), Q-010 (+1), Q-005 (+1)

**Largest correctness regressions:** Q-012 (+0), Q-013 (+0), Q-015 (+0)

**Top recall gains:** Q-011 (+3), Q-010 (+2), Q-003 (+2)
