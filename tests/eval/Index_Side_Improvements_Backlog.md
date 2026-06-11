# Index-Side Improvements Backlog (DEFERRED)

The eval-config sweep (`sweep.py`) tunes only the request-time knobs of the
Discovery Engine `:answer` API. Three classes of failure surfaced in the
results CSV originate at the **data store / index layer** and cannot be
fixed by API tuning alone. They are captured here so they aren't lost.

> **Status:** Deferred 2026-06-11 by user. Revisit after the API-tuning
> sweep results land — the sweep numbers will indicate how much headroom
> remains for the index-side fixes to recover.

## Issues

### 1. Chunk metadata gaps (page titles / dates not in chunk body)

| | |
|---|---|
| **Symptom** | Hallucinated dates (2018, 2024, 2026) in answers for Q-001, Q-010, Q-014, Q-015. |
| **Root cause** | Test names and dates live in Confluence page titles or page properties but the chunked text in the index contains only the body. The model has no source for the date and invents one. |
| **Fix options** | (a) Configure the data store's chunk config to **prepend** the page title and key properties to every chunk's body. (b) Fix at the Confluence source so each test page repeats name and date in the body text. |
| **Owner** | DE / Confluence admin |
| **Verify** | Re-run the sweep on the `baseline` config; expect `faithfulness` ≥ 4.5 and disappearance of fabricated years in spot-checks. |

### 2. Layout-unaware chunking (cross-chunk brand confusion)

| | |
|---|---|
| **Symptom** | Q-011 / Q-013: numbers from BR Mobile and BRFS Mobile got mixed up in a single answer. |
| **Root cause** | Pages that document multiple tests are split with default chunking, so a single chunk ends up containing fragments of two tests; the model attributes a metric to the wrong brand/challenger. |
| **Fix options** | Switch the data store to **layout-based chunking** so each test result section becomes its own chunk. Requires consistent heading conventions on the source pages. |
| **Owner** | DE |
| **Verify** | Spot-check Q-011 / Q-013 answers after re-index; numbers should match the brand the question asked about. |

### 3. Missing Confluence pages

| | |
|---|---|
| **Symptom** | Q-008 reference cites 31 tests; retrieval covered 4–5. Q-010 (MegaNav) missed most. |
| **Root cause** | One or more Confluence spaces / pages are not in the data store. Either the connector hasn't crawled them, or specific space keys were excluded. |
| **Fix options** | Audit indexed docs in `Discovery Engine → Data Stores → <store> → Documents` (search for "ISM", "Promo Drawer", "MegaNav"). Re-run the Confluence connector with the missing space keys, or manually add them. |
| **Owner** | DE / Confluence admin |
| **Verify** | After re-index, `context_recall` on the affected questions should rise to ≥ 4.0 in the sweep. |

## How to revisit

1. After the sweep completes, open `runs/sweep_<ts>/comparison_summary.csv`.
2. If the best API-only config still has `context_recall` < 4.0 or shows
   date-fabrication in spot-checks, the issues above are gating quality
   and the deferred work should be picked up.
3. If the best API-only config clears those bars, the deferred items
   become a "polish" backlog rather than a blocker.

## Cross-references

- API-side configurations: [configs.py](configs.py)
- Sweep driver: [sweep.py](sweep.py)
- Eval harness entry point: [run_eval.py](run_eval.py)
