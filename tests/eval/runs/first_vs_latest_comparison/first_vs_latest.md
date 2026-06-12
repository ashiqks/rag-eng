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

## Configuration settings

### Common runtime settings (used by every run)

| setting | value |
| --- | --- |
| GCP project | `prj-0n-dta-pt-ai-sandbox` |
| GCP region | `us-central1` |
| Discovery Engine project | `prj-0n-dta-pt-ai-sandbox` |
| Discovery Engine location | `global` |
| Engine ID | `gap-erd-discovery_1779708094567` |
| Serving config | `default_search` |
| Collection | `default_collection` |
| Eval questions | `tests/eval/eval_questions_user_set.csv` (15 questions, Q-001 … Q-015) |
| Judge model (Vertex Eval Service) | `gemini-3.1-pro-preview` |
| Concurrency | 8 |
| Proxy | `http://proxy.wal-mart.com:8080` |
| Eval metrics | `faithfulness`, `answer_relevancy`, `answer_correctness`, `context_precision`, `context_recall` (PointwiseMetrics, 1–5) |

### "First" run configuration (= `baseline`)

Reproduces the historical request shape sent to the Discovery Engine `:answer` API. No model override, no preamble, no retrieval overrides.

| key | value |
| --- | --- |
| config name | `baseline` |
| `model_label` | `default` (Discovery Engine default `:answer` model) |
| `request_overlay` | `{}` (empty — server defaults for everything) |
| Retrieval | default (no `searchSpec.searchParams.maxReturnResults`, no query rephrasing override) |
| Grounding | none (`groundingSpec` not set) |
| Prompt | none (`promptSpec.preamble` not set) |
| `ignoreLowRelevantContent` | not set (server default) |

### "Latest" run configuration (= `preview+prompt`, sweep winner)

Strict anti-hallucination preamble + the server-rolled `preview` answer-generation model. Default retrieval, no grounding override.

| key | value |
| --- | --- |
| config name | `preview+prompt` |
| `model_label` | `preview` |
| `answerGenerationSpec.modelSpec.modelVersion` | `preview` |
| `answerGenerationSpec.ignoreLowRelevantContent` | `true` |
| `answerGenerationSpec.promptSpec.preamble` | `PREAMBLE_STRICT` (see below) |
| `searchSpec` | not set (default retrieval) |
| `queryUnderstandingSpec` | not set (default rephrasing) |
| `groundingSpec` | not set |

#### `PREAMBLE_STRICT` text used in the latest run

```
You are an analyst answering questions strictly from the provided documents. Hard rules:
1. Never invent dates, numbers, percentages, test names, brand codes, or document titles. If a fact is not stated verbatim in the retrieved chunks, omit it.
2. When referring to a test, use the exact name as it appears in the chunk. If no name appears, refer to it descriptively (e.g., 'a 2025 Old Navy PDP test') without inventing a title.
3. When the chunk filename encodes the year (e.g., '2018_...'), you MAY cite that year, but only if the chunk's textual content also discusses dates consistent with it.
4. Quantitative claims (RPV, OPV, return-rate %, engagement %) must be quoted from the chunk verbatim or omitted.
5. If the retrieved chunks do not answer the question, say so explicitly rather than guessing.
```

### All configurations tested in the sweeps that led to picking `preview+prompt`

Eleven configs were evaluated across three sweeps (run definitions in `tests/eval/configs.py`). Every config layers a `request_overlay` on the same baseline request body via deep-merge.

| config | model | preamble | maxReturnResults | maxRephraseSteps | groundingSpec.filteringLevel | `ignoreLowRelevantContent` |
| --- | --- | --- | --- | --- | --- | --- |
| `baseline` | default | — | default | default | — | unset |
| `prompt-only` | default | STRICT | default | default | — | true |
| `flash-2.5+prompt` | `gemini-2.5-flash/answer_gen/v1` | STRICT | default | default | — | true |
| **`preview+prompt`** (winner) | `preview` | STRICT | default | default | — | true |
| `preview+recall` | `preview` | STRICT | 25 | 3 | — | true |
| `preview+grounding` | `preview` | STRICT | 25 | 3 | `FILTERING_LEVEL_HIGH` | true |
| `kitchen-sink` | `preview` | STRICT + glossary | 25 | 5 | `FILTERING_LEVEL_HIGH` | true |
| `gemini-3.1-pro+prompt` | `gemini-3.1-pro-preview/answer_gen/v1` | STRICT | default | default | — | true |
| `gemini-3.1-pro+recall` | `gemini-3.1-pro-preview/answer_gen/v1` | STRICT | 25 | 3 | — | true |
| `gemini-3.1-pro+grounding` | `gemini-3.1-pro-preview/answer_gen/v1` | STRICT | 25 | 3 | `FILTERING_LEVEL_HIGH` | true |
| `gemini-3.1-pro+glossary` | `gemini-3.1-pro-preview/answer_gen/v1` | STRICT + glossary | default | default | — | true |

### Sweeps run

| sweep folder | configs included |
| --- | --- |
| `runs/sweep_2026-06-11T11-02-36Z/` | `baseline`, `prompt-only`, `flash-2.5+prompt`, `preview+prompt`, `preview+recall`, `preview+grounding`, `kitchen-sink` |
| `runs/sweep_2026-06-11T11-33-03Z/` | `baseline`, `preview+prompt`, `gemini-3.1-pro+prompt`, `gemini-3.1-pro+recall`, `gemini-3.1-pro+grounding` |
| `runs/sweep_pro31_2026-06-12T05-33-07Z/` | `baseline`, `preview+prompt`, `gemini-3.1-pro+prompt`, `gemini-3.1-pro+recall`, `gemini-3.1-pro+grounding`, `gemini-3.1-pro+glossary` |

`preview+prompt` was selected as the latest winner because it produced the largest gain on `answer_correctness` (+0.40) and `context_recall` (+0.20) while halving mean latency vs. the first run (8594 ms → 4670 ms), with no statistically meaningful regression on `faithfulness` or `context_precision`.
