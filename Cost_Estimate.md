# Cost Estimate — Vertex AI Search + Vertex AI Model Garden

**Date:** 2026-06-01
**Scope:** POC of the GenAI Knowledge Discovery + Dashboard Data Agent variant.
**Coverage:** Vertex AI Search (Discovery Engine, Enterprise edition) + Vertex AI Model Garden (Gemini 2.5 Pro + Gemini 2.5 Flash). Platform overhead (Cloud Run, GCS, BQ, Observability, networking, VPC-SC, KMS) is summarised separately at the end.
**Pricing basis:** GCP public list prices, 2026-Q2 (us-central1).

> All numbers are list-price estimates for budgeting. Treat as ±25 % until the first month of live telemetry from the Cloud Billing line-item budget (AR-6) confirms the actuals.

---

## 1. Assumptions

| Driver | POC value | Source |
|---|---|---|
| Users | 20 | [Model_Selection.md](Model_Selection.md) §workload profile; [Meeting 3/Meeting_Overview.md](Meeting%203/Meeting_Overview.md) row 8 |
| Turns / user / day | 30 | [Model_Selection.md](Model_Selection.md) line 98 |
| Working days / month | 22 | — |
| **Turns / month** | **~13,200** | derived |
| Corpus size | ~1,500 pages ≈ 30 MB HTML | [Meeting 1/Project_Reference.md](Meeting%201/Project_Reference.md), [DE_Handover_Corpus_Ingest.md](DE_Handover_Corpus_Ingest.md) |
| Retrieval | top-10 chunks × ~500 tokens each | [Project_Documentation.md](Project_Documentation.md) §chunking |
| Per-turn input to Pro | ~7,500 tokens (system + history + chunks + query) | derived |
| Per-turn output | ~500 tokens | derived |
| Flash usage (intent / param extract) | ~300 in / 50 out per turn | model orchestration spec |
| Eval runs | weekly golden set, ~200 prompts × 4 weeks = 800 / mo | [Project_Documentation.md](Project_Documentation.md) |

---

## 2. Vertex AI Search (Discovery Engine, Enterprise edition)

| Line item | Unit price | Volume / mo | Monthly cost |
|---|---|---|---|
| Search query (Enterprise) | $4 / 1,000 queries | 13,200 | **$53** |
| LLM add-on / Answer API | $4 / 1,000 queries | 13,200 | **$53** |
| Indexed-data storage | $5 / GiB·mo (first 10 GiB free) | 0.03 GiB | **$0** |
| Ingestion / re-indexing | included | weekly | $0 |
| Eval queries (golden-set replay) | $8 / 1,000 (search + add-on) | 800 | **$6** |
| **VAIS subtotal** | | | **~$112 / mo** |

---

## 3. Vertex AI Model Garden — Gemini 2.5

Public list prices (us-central1, ≤200K context window):

| Model | Input | Output |
|---|---|---|
| Gemini 2.5 Pro | $1.25 / M tokens | $10 / M tokens |
| Gemini 2.5 Flash | $0.30 / M tokens | $2.50 / M tokens |

| Use case | Input tokens / mo | Output tokens / mo | Monthly cost |
|---|---|---|---|
| Pro — answer / narrative (13,200 turns × 7,500 in / 500 out) | 99 M | 6.6 M | $124 + $66 = **$190** |
| Flash — intent / param extract (13,200 turns × 300 in / 50 out) | 3.96 M | 0.66 M | $1 + $2 = **$3** |
| Pro — weekly eval (800 prompts × 7,500 in / 500 out) | 6 M | 0.4 M | $8 + $4 = **$12** |
| **Model Garden subtotal** | | | **~$205 / mo** |

---

## 4. Combined POC estimate

| Bucket | Monthly |
|---|---|
| Vertex AI Search | ~$112 |
| Vertex AI Model Garden (Gemini 2.5 Pro + Flash) | ~$205 |
| **Total managed AI services** | **~$315 – $360 / mo** |

Recommended budget envelope including ±25 % buffer for prompt drift, retries and admin usage: **$400 / mo** for the two managed-AI line items.

---

## 5. Sensitivity to scale

| Scenario | Turns / mo | VAIS | Gemini (Pro + Flash) | Combined |
|---|---|---|---|---|
| POC base — 20 users × 30 turns | 13.2 K | $112 | $205 | **~$320** |
| 50 users × 30 turns | 33 K | $270 | $510 | **~$780** |
| 100 users × 30 turns | 66 K | $530 | $1,020 | **~$1,550** |
| Corpus 5K pages (worst-case ingest) | unchanged | +$0 (still < 10 GiB free tier) | +$0 | — |

Dominant cost driver at every scale: **Gemini Pro input tokens × retrieved-chunk size**. Every additional 1,000 retrieved tokens per turn adds ~$0.013 / turn ≈ **$170 / mo** at the POC volume.

Two practical levers to keep Pro spend bounded:

1. **Reduce top-K** from 10 → 6 chunks (or compress chunks before grounding) → ~30 % off Pro input bill.
2. **Move the orchestrator's "synthesise draft" hop to Flash** and reserve Pro for the final user-visible answer only → ~40 % off Pro input bill.

Both are configuration changes against the existing pipeline; no architectural rework.

---

## 6. Cost-control mechanisms already in the architecture (AR-6)

- **Cloud Billing budget alerts** on the Discovery Engine and Vertex AI SKUs.
- **Log-based metrics** `gap_genai/llm_tokens_in`, `gap_genai/llm_tokens_out`, `gap_genai/llm_calls`, `gap_genai/llm_cost_usd` published to a Cloud Monitoring dashboard.
- **Monitoring alert policy** on `llm_tokens_out` rate-of-change (catches runaway agent loops before they show up on the bill).
- **Cloud Run max-instances cap** on web/gateway/agent services bounds concurrent fan-out (also mitigates STRIDE T13).
- **Agent caps:** `max_steps = 8`, output `max_tokens` cap, 30 s deadline (D5 STRIDE row).

---

## 7. Out-of-scope of this estimate

Items below are real but small at POC scale; covered under the platform line on the budget rather than the AI line. Order-of-magnitude reference for completeness:

| Item | Order-of-magnitude / mo (POC) |
|---|---|
| Cloud Run (5 services + 2 Jobs, scale-to-zero) | $20 – $60 |
| GCS (corpus bucket, versioned + CMEK) | $1 – $5 |
| BigQuery (product data only: `feedback`, `golden_evals`, `eval_runs`, `app_config.*`, view `v_experiment_kpis`) | $5 – $20 |
| Cloud Observability Suite (Logging / Monitoring / Trace) | $20 – $50 |
| Secret Manager (a few secrets + access calls) | < $1 |
| KMS (CMEK key operations) | $1 – $3 |
| VPC + Cloud NAT + PSC endpoints (~$10 / endpoint·mo) | $30 – $60 |
| **Platform subtotal** | **~$80 – $200 / mo** |

**Grand total POC ceiling (managed AI + platform):** ~$400 – $560 / mo.

---

## 8. Caveats

- The `~$1,200 – $1,500 / mo` figure quoted in [Model_Selection.md](Model_Selection.md) line 98 reflects an earlier model assumption ("Opus dominant" — Claude Opus). The current two-Gemini setup lands at ~$315 – $400 / mo for managed AI services.
- Vertex AI Evaluation Service itself does not carry an additional SKU charge beyond the underlying VAIS query + Gemini token spend it triggers (already counted above).
- All Confluence ingest and HTML rendering occurs in Gap-owned Cloud Run; no SKU charge against VAIS for ingestion.
- VAIS Enterprise edition pricing assumed (chosen for generative grounding + advanced features). Switching to Standard edition (no LLM add-on) would cut VAIS to ~$20 / mo but disable the Answer API.
- Pricing assumes us-central1 and the standard Vertex AI commercial terms (Google Cloud DPA, no training on customer data, regional residency).
