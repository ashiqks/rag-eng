# Vertex AI Search Evaluation Harness

Automated evaluation framework for a Vertex AI Search (Agent Search /
Discovery Engine) application, using **Vertex AI Gen AI Evaluation Service**
as the metric engine.

## What it does

1. Reads `eval_questions.csv` (curated `question_id`, `question`, `reference_answer`).
2. For each question, calls your Vertex AI Search engine's `:answer` endpoint
   (with `includeCitations=true`) in parallel.
3. Sends the (question, answer, retrieved-context, reference) tuples to
   Vertex AI Eval Service, scored by a Gemini autorater.
4. Writes a CSV with one row per question and one column per metric
   (plus the autorater's explanation per metric).

## Current configuration

These are the values shipped in [.env.example](.env.example) and used by
this POC. Override any of them via env var or CLI flag.

| Setting | Value |
|---|---|
| GCP project (runs Vertex AI Eval Service) | `prj-0n-dta-pt-ai-sandbox` |
| GCP region | `us-central1` |
| Search engine project | `prj-0n-dta-pt-ai-sandbox` |
| Search engine location | `global` |
| Search engine collection | `default_collection` |
| Search engine ID | `gap-erd-discovery_1779708094567` |
| Search serving config | `default_search` |
| Judge model | `gemini-3.1-pro-preview` |
| Concurrency (parallel `:answer` calls) | `8` |
| Active config preset | `preview+prompt` (set `EVAL_CONFIG` to switch — see [Configurations](#configurations)) |
| Questions input | [eval_questions.csv](eval_questions.csv) (8 questions) |
| Runs output | [runs/](runs/) (UTC-timestamped subfolders) |

## Metrics

| Output column | How it is scored |
|---|---|
| `faithfulness` | Custom `PointwiseMetric` — is the response grounded in the retrieved context? |
| `answer_relevancy` | Custom `PointwiseMetric` — does the response address the question? |
| `answer_correctness` | Custom `PointwiseMetric` — does the response match the reference answer? |
| `context_precision` | Custom `PointwiseMetric` — are the retrieved chunks relevant to the question? |
| `context_recall` | Custom `PointwiseMetric` — do the retrieved chunks cover the reference answer? |

All five metrics use hand-written rubric prompts defined in [metrics.py](metrics.py)
and are evaluated by Vertex AI Gen AI Evaluation Service's server-side
autorater. The autorater model is selected by the service in this SDK version
(`google-cloud-aiplatform >= 1.156`); the `JUDGE_MODEL` env var is reserved
for future SDKs that expose `autorater_config`.

> Note: this SDK version does not expose the built-in `groundedness` metric
> in a way that reads the `context` column — it only sees `prompt` and
> `response`, which scores every RAG answer as ungrounded. The custom
> `faithfulness` metric above explicitly takes `response` + `context` and
> produces the correct signal.

## Quick start

The recommended entry point is the cross-platform Python launcher
[eval.py](eval.py). It auto-detects your OS, creates the virtual environment
on first run, installs requirements, then runs the eval. One command, same
syntax on Windows / Linux / macOS:

```bash
# 1. Authenticate with Google Cloud (one-time, interactive browser flow)
gcloud auth login <your-email>
gcloud auth application-default login
gcloud auth application-default set-quota-project prj-0n-dta-pt-ai-sandbox
gcloud config set project prj-0n-dta-pt-ai-sandbox

# 2. Run the launcher. First run: ~1-2 min for setup + ~30 sec for the eval.
#    Subsequent runs: just the eval.
python tests/eval/eval.py                         # full eval (queries + scoring)
python tests/eval/eval.py --dry-run               # query the app, skip scoring
python tests/eval/eval.py --concurrency 4         # tweak any run_eval.py flag
python tests/eval/eval.py --reinstall             # force re-install of deps
```

> On Windows the command may be `py tests\eval\eval.py` or
> `python3 tests/eval/eval.py` depending on how Python was installed.

The launcher writes a marker file (`.venv/.eval_harness_setup_ok`) after a
successful setup, so subsequent invocations skip straight to the eval.

### Platform-specific wrappers (alternative)

If you prefer a native shell wrapper instead of `python eval.py`:

| OS | Setup (one-time) | Run |
|---|---|---|
| Windows (PowerShell) | `.\tests\eval\setup.ps1` | `.\tests\eval\run.ps1 [args]` |
| Linux / macOS (bash) | `chmod +x tests/eval/*.sh && tests/eval/setup.sh` | `tests/eval/run.sh [args]` |

Both wrappers internally do exactly what `eval.py` does and forward all
arguments to `run_eval.py`. If PowerShell blocks `setup.ps1` with "running
scripts is disabled on this system", unblock it for the current user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Manual setup (no helper)

```bash
cd tests/eval
python -m venv .venv
# Windows:  .venv\Scripts\Activate.ps1
# Linux/macOS:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Copy-Item on Windows
python run_eval.py --dry-run
```

## Required IAM roles on the calling identity

| Role | Why |
|---|---|
| `roles/discoveryengine.user` | Call the `:answer` API on the search engine |
| `roles/aiplatform.user` | Run Vertex AI Gen AI Evaluation Service |
| `roles/serviceusage.serviceUsageConsumer` | Use the quota project |

## Configurations

The Discovery Engine `:answer` API exposes several knobs that change
retrieval behaviour and answer quality (model selection, system prompt,
grounding strictness, retrieval breadth, query rephrasing). To compare
them empirically, [configs.py](configs.py) defines named presets that are
deep-merged into the request body at run time.

| Preset | Model | Preamble | maxResults | Rephrase | Grounding | Use for |
|---|---|---|---|---|---|---|
| `baseline` | default | — | default | 0 | default | Reproduces today's request body. Reference for deltas. |
| `prompt-only` | default | strict | default | 0 | default | Isolate prompt impact on the cheap default model. |
| `flash-2.5+prompt` | `gemini-2.5-flash` | strict | default | 0 | default | Cheap upgrade. |
| `preview+prompt` | `preview` (server-rolled best) | strict | default | 0 | default | Strongest instruction-following the `:answer` API exposes. |
| `preview+recall` | `preview` | strict | 25 | 3 | default | Targets `context_recall` failures on broad questions. |
| `preview+grounding` | `preview` | strict | 25 | 3 | `HIGH` | Server-side abstention on unsupported claims. |
| `kitchen-sink` | `preview` | strict + brand glossary | 25 | 5 | `HIGH` | Upper-bound config (no re-indexing). |

Notes on what is and isn't tunable on `:answer`:

- `gemini-2.5-pro/answer_gen/v1` is **not** accepted by the `:answer` API
  (returns `Unsupported model version`). The only model versions accepted
  are `stable`, `preview`, `gemini-2.0-flash-001/answer_gen/v1`, and
  `gemini-2.5-flash/answer_gen/v1`. Use `preview` to ride whatever
  Discovery Engine has currently rolled as its strongest answer model.
- `searchSpec.searchParams.maxReturnResults` is capped at **25**.
- `queryExpansionSpec` and `spellCorrectionSpec` are `:search`-only fields
  and are rejected by `:answer`. The serving config's AUTO defaults
  already apply.

Run a single config:

```bash
python run_eval.py --config preview+prompt
python run_eval.py --config baseline --dry-run    # inspect request body without scoring
```

Run a sweep over all configs (or a subset) and produce a side-by-side
comparison report:

```bash
python sweep.py                                          # all configs
python sweep.py --configs baseline,preview+prompt,kitchen-sink
python sweep.py --questions-csv my_user_set.csv          # any CSV with the standard schema
```

Sweep output lands in `runs/sweep_<UTC-timestamp>/`:

```
comparison.csv          one row per (question_id, config), all metrics
comparison_summary.csv  one row per config: metric means + delta vs baseline
comparison.md           human-readable report with a recommendation
sweep_manifest.json     record of which per-config run dirs feed this sweep
```

Winner pick rule (in `comparison.md`): the config with the highest
`answer_correctness + 0.5 * faithfulness` mean.

### Sweep results on the user 15-question set (2026-06-11)

Latest sweep over the 15-question user set
([eval_questions_user_set.csv](eval_questions_user_set.csv), drawn from
`results.csv`):

| Config | faith | rel | correct | prec | recall | Δ correct vs baseline |
|---|---|---|---|---|---|---|
| `baseline` | 4.20 | 4.80 | 1.93 | 4.67 | 2.80 | — |
| `prompt-only` | 4.00 | 4.87 | 2.33 | 4.67 | 2.40 | +0.40 |
| `flash-2.5+prompt` | 4.13 | 4.93 | 2.47 | 4.40 | 2.93 | +0.53 |
| **`preview+prompt`** | **3.93** | **4.93** | **2.67** | **4.27** | **3.60** | **+0.73** |
| `preview+recall` | 3.67 | 5.00 | 2.33 | 4.60 | 2.73 | +0.40 |
| `preview+grounding` | 3.53 | 5.00 | 2.40 | 4.47 | 3.13 | +0.47 |
| `kitchen-sink` | 3.67 | 4.87 | 2.40 | 4.53 | 2.80 | +0.47 |

**Winner: `preview+prompt`** — highest `answer_correctness` (+0.73 over
baseline) and highest `context_recall` (+0.80). `EVAL_CONFIG` defaults to
this preset.

Key observations:

- The strict preamble alone (no model swap) lifts correctness +0.40
  (baseline → `prompt-only`).
- Upgrading the model to `preview` on top of the strict preamble adds
  another +0.33 correctness and +1.20 recall.
- Bumping `maxReturnResults` to 25 or forcing `groundingSpec=HIGH`
  *hurts* correctness vs `preview+prompt` — added context introduces
  noise the answerer doesn't need.
- `kitchen-sink` (everything on, including a brand glossary) does not
  beat `preview+prompt`, confirming the simplest tuned config wins.
- Faithfulness drops slightly (-0.27) under the winner because the
  model now abstains/hedges honestly instead of fabricating; correctness
  rises in lockstep.
- Absolute correctness still tops out at 2.67/5 on this question set —
  the remaining gap is dominated by index-side issues (chunk metadata,
  layout chunking, missing Confluence pages) tracked in
  [Index_Side_Improvements_Backlog.md](Index_Side_Improvements_Backlog.md).

Full data: `runs/sweep_2026-06-11T11-02-36Z/comparison.md` and
`comparison.csv`.

### What `:answer`-config tuning **cannot** fix

Some failure modes (date hallucination from chunk-metadata gaps,
cross-chunk brand confusion, missing Confluence pages) live in the
data-store layer, not the request. They're tracked separately in
[Index_Side_Improvements_Backlog.md](Index_Side_Improvements_Backlog.md).
The sweep results help decide whether that deferred work is needed.

## Output

Each invocation creates a UTC-timestamped folder under `runs/`:

```
tests/eval/runs/2026-06-08T14-30-00Z/
  responses.csv      <- raw app outputs (question, answer, context, citations, latency_ms, error)
  results.csv        <- responses.csv + per-metric score and explanation columns
  summary.json       <- mean / count per metric for the whole run
  run_config.json    <- resolved config values used for this run (engine, judge, etc.)
```

`results.csv` columns:

```
question_id, question, reference_answer, response, context, citations, latency_ms, error,
faithfulness, faithfulness_explanation,
answer_relevancy, answer_relevancy_explanation,
answer_correctness, answer_correctness_explanation,
context_precision, context_precision_explanation,
context_recall, context_recall_explanation
```

Scores are 1-5 (Vertex Eval scale). The `*_explanation` columns contain the
autorater's reasoning — gold for debugging "why did this question fail".

## Adding questions

Edit [eval_questions.csv](eval_questions.csv). Schema:

| Column | Type | Notes |
|---|---|---|
| `question_id` | string | Stable ID, e.g. `Q-009` |
| `question` | string | Natural-language query |
| `reference_answer` | string | Curated gold answer (used by `answer_correctness` and `context_recall`) |

## Configuration reference

All settings are environment variables loaded from [.env](.env). CLI flags
override env vars. See [.env.example](.env.example) for the full template.

| Env var | Default | Meaning |
|---|---|---|
| `GCP_PROJECT_ID` | `prj-0n-dta-pt-ai-sandbox` | Project that runs Vertex AI Eval Service |
| `GCP_REGION` | `us-central1` | Region for Vertex AI Eval Service |
| `SEARCH_PROJECT_ID` | = `GCP_PROJECT_ID` | Project hosting the search engine |
| `SEARCH_LOCATION` | `global` | Engine location |
| `SEARCH_COLLECTION` | `default_collection` | Engine collection |
| `SEARCH_ENGINE_ID` | `gap-erd-discovery_1779708094567` | Engine ID under test |
| `SEARCH_SERVING_CONFIG` | `default_search` | Serving config to call |
| `JUDGE_MODEL` | `gemini-3.1-pro-preview` | Reserved; this SDK uses a server-side autorater |
| `EVAL_CONCURRENCY` | `8` | Concurrent in-flight `:answer` calls |
| `EVAL_CONFIG` | `preview+prompt` | Named preset from [configs.py](configs.py) — alters the `:answer` request body (model, preamble, grounding, retrieval breadth). |
| `EVAL_QUESTIONS_CSV` | `eval_questions.csv` | Input file path. Relative paths resolved against `tests/eval/`, then CWD. |
| `EVAL_RUNS_DIR` | `runs` | Output base directory. Relative paths resolved against `tests/eval/`. |
| `HTTPS_PROXY` / `HTTP_PROXY` | (optional) | Set if your network requires an outbound proxy for `*.googleapis.com`. |

## Porting this harness to another machine

The `tests/eval/` folder is self-contained — copy the repo (or just this
folder) to the new machine and run `python tests/eval/eval.py`. Only one
file is machine-specific:

* `.env` — holds project ID, search engine ID, judge model, and (if needed)
  proxy. It is **not** version-controlled (`.gitignore` excludes it).
  Either copy your old `.env` alongside the code, or let the launcher copy
  `.env.example` and edit the values for the new environment.

Do **not** copy the `.venv/` or `runs/` folders — they're regenerated /
append-only on the target machine.

Minimum requirements on the target machine:

* Python **3.10+** on PATH
* `gcloud` CLI authenticated as a principal with the IAM roles listed above
* Network egress to `*.googleapis.com` (direct, or via an outbound proxy
  declared in `.env`)
