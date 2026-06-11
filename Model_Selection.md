# LLM Model Selection — GAP Experimentation Discoverability POC

> **Goal:** narrow the current 6-model roster (Gemini 3.1 Pro preview, Gemini 2.5 Pro, Gemini 2.5 Flash, Claude Opus 4.7 preview, Claude Opus 4.6 GA, Claude Haiku 3.5) down to **one primary + one fallback** so the client only has to approve two models, not six.
>
> **Scope:** applies to both tracks — the main RAG (Vertex AI Agent Builder) and the Vectorless RAG Spike (Claude Agent SDK + PageIndex).
>
> **VAIS variant note (May 2026)**: the **locked variant in [`Vertex_AI_Search_Variant/`](Vertex_AI_Search_Variant/) is Gemini-only** - `gemini-2.5-flash` for intent classification + parameter extraction on the Dashboard Data Agent, `gemini-2.5-pro` for chained narrative summarisation. **VAIS `:answer` owns its own internal generation model** (managed by Google) - the Agent does not call Claude. No fallback to Claude is configured. The Claude Opus 4.6 + Gemini 2.5 Pro pair described below applies to the **alternate non-VAIS track** (Claude Agent SDK + PageIndex) only. See [`Vertex_AI_Search_Variant/Architecture.md`](Vertex_AI_Search_Variant/Architecture.md) §7.
>
> **Workload profile:** internal-only, 5–20 users, ~500–1500 Confluence pages, RAG-style Q&A with citations, no public exposure, no multimodal needs, no agentic long-horizon tool-use beyond the orchestrator.

---

## 1. Comparison parameters (why these were chosen)

For a RAG application the parameters that actually move the needle are:

| Category | Parameter | Why it matters for RAG |
|---|---|---|
| **Quality** | General reasoning (MMLU-Pro, GPQA-Diamond) | Determines synthesis quality from retrieved chunks |
| | RAG-specific faithfulness (RAGTruth / FActScore) | Hallucination rate when grounded on context |
| | Long-context recall (RULER 128K, Needle-in-Haystack) | Whether the model actually uses the context you give it |
| | Instruction following (IFEval) | Citation format, answer length, refusal discipline |
| **Cost** | Input $/M tokens | Dominant cost in RAG (context >> output) |
| | Output $/M tokens | Matters for long synthesised answers |
| | Cached-input $/M tokens | Big win when prompt + system instructions repeat |
| **Speed** | Time-to-first-token (TTFT) p50 | UX perception in chat |
| | Output tokens/sec (steady state) | End-to-end latency for long answers |
| **Capacity** | Context window | Sets the upper bound on retrieved-chunk count |
| | Max output tokens | Caps answer length |
| | Default RPM / TPM quota on Vertex | Real-world throughput before quota requests |
| **Operability** | Vertex AI Model Garden availability | Single billing, single IAM, in-VPC |
| | Vendor (concentration risk) | One vs two suppliers across primary + fallback |
| | Maturity (GA vs preview) | Production readiness; preview models can change |
| | Grounding / structured-output / function-calling | Native citation + JSON-mode support |

---

## 2. Side-by-side comparison

> **Pricing and benchmarks are point-in-time (May 2026) public figures from Google Vertex AI, Anthropic, and the Artificial Analysis / LMSYS / HELM leaderboards.** Preview models (Gemini 3.1 Pro preview, Claude Opus 4.7) are subject to change; figures marked *(preview)* are best-effort approximations and should be re-validated before sign-off.

| Parameter | Gemini 3.1 Pro preview | Gemini 2.5 Pro | Gemini 2.5 Flash | Claude Opus 4.7 preview | Claude Opus 4.6 GA | Claude Haiku 3.5 |
|---|---|---|---|---|---|---|
| **Status** | Preview (allowlist) | GA | GA | Preview / latest premium | **GA** | GA |
| **Vendor** | Google (native Vertex) | Google (native Vertex) | Google (native Vertex) | Anthropic via Model Garden | Anthropic via Model Garden | Anthropic via Model Garden |
| **Context window** | 1M tokens | 1M tokens (2M roadmap) | 1M tokens | 200K tokens | 200K tokens | 200K tokens |
| **Max output tokens** | 64K | 64K | 64K | 32K | 32K | 8K |
| **Input $/M tokens** | ~$2.50 *(preview)* | $1.25 (≤200K), $2.50 (>200K) | $0.30 | ~$15 *(preview)* | $12 | $0.80 |
| **Output $/M tokens** | ~$15 *(preview)* | $10 (≤200K), $15 (>200K) | $2.50 | ~$75 *(preview)* | $60 | $4.00 |
| **Cached-input $/M** | ~$0.30 *(preview)* | $0.30 | $0.075 | ~$1.50 *(preview)* | $1.20 | $0.08 |
| **Indicative $/RAG turn** ¹ | ~$0.040 | ~$0.020 | ~$0.0035 | ~$0.180 | ~$0.156 | ~$0.012 |
| **MMLU-Pro** | ~85 *(preview)* | ~82 | ~75 | ~84 | ~83 | ~70 |
| **GPQA-Diamond** | ~85 *(preview)* | ~84 | ~75 | ~83 | ~82 | ~65 |
| **RAGTruth (faithfulness, ↑)** | n/a yet | High | Medium-High | **Highest** (Anthropic leads citation discipline) | **Highest** (matches 4.7 within margin) | Medium |
| **Long-context recall (RULER 128K)** | ~95% *(preview)* | ~94% | ~90% | ~93% | ~92% | ~80% |
| **Instruction following (IFEval)** | ~90 *(preview)* | ~88 | ~84 | ~92 | ~91 | ~82 |
| **TTFT p50** | ~1.5 s | ~1.0 s | **~0.4 s** | ~2.0 s | ~1.8 s | ~0.6 s |
| **Output tokens/sec** | ~80 | ~120 | **~250** | ~60 | ~70 | ~150 |
| **Default Vertex RPM** | 30 | 60 | 300 | 30 | 50 | 120 |
| **Native grounding / citations** | Vertex Grounding | Vertex Grounding | Vertex Grounding | Citations API + system-prompt discipline | Citations API + system-prompt discipline | Citations API |
| **Function calling / JSON mode** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Region (us-central1)** | Yes (allowlist) | Yes | Yes | Yes (us-east5) | Yes (us-east5) | Yes (us-east5) |
| **VPC-SC compatible** | Yes | Yes | Yes | Yes (Model Garden) | Yes (Model Garden) | Yes (Model Garden) |
| **Prompt-injection robustness** | High *(preview)* | High | Medium-High | **Highest** | **Highest** | Medium |
| **Maturity for production** | Low (preview) | **High (GA)** | **High (GA)** | Medium (latest premium) | **High (GA, ~6 months in market)** | High (GA) |

¹ Indicative cost per RAG turn assumes ~8K input tokens (system prompt + ~10 reranked chunks + history) and ~500 output tokens. Actual cost will vary; prompt caching reduces input cost by ~75% on repeat-prefix turns.

---

## 3. Per-model verdict

| Model | Keep? | Reasoning |
|---|---|---|
| **Gemini 3.1 Pro preview** | ❌ Drop | Preview status = changeable behaviour, allowlist friction, no faithfulness benchmarks yet, ~2× cost of GA Pro for marginal benchmark gains. Re-evaluate after GA. |
| **Gemini 2.5 Pro** | ✅ **FALLBACK + cheap-task model** | GA, native Vertex (single bill, single IAM, in-VPC), 1M context, strong RAG quality, top-tier reasoning at ~$0.020/turn. Serves as (a) automatic failover for Opus, (b) the cheap-task workhorse (query rewrite, chunk enrichment, conversation summarisation, Memory Bank curation, PageIndex node-scoring), and (c) the LLM-as-judge in the eval pipeline (independent from the premium primary). |
| **Gemini 2.5 Flash** | ❌ Drop | Cheaper and faster than Pro, but the client mandate is **two models only**. Pro already covers every Flash use-case at ~3× the cost which is still negligible at POC scale (5–20 users); collapsing to Pro removes a model from the approval surface. Re-introduce in Phase 2 if ingest-time enrichment cost becomes material. |
| **Claude Opus 4.7 preview** | ❌ Drop | Best citation discipline in the field, but preview status (behaviour can shift), ~25% more expensive than the GA 4.6, and adds preview-allowlist friction on top of the Anthropic vendor track. Pick the GA 4.6 instead. |
| **Claude Opus 4.6 GA** | ✅ **PRIMARY** | Best-in-class faithfulness, citation discipline, and prompt-injection robustness for RAG. Production-stable GA, mature pricing ($12 / $60 per 1M in/out), 200K context (sufficient for the Confluence corpus shape), fully managed via **Vertex AI Model Garden** (IAM-based access, no Anthropic-direct API key, billing rolls into the GCP invoice). Lives in `us-east5` — the cross-region hop from `us-central1` orchestration adds ~30–60 ms p50 and trivial egress cost at POC volume. Premium cost (~$0.156/turn) is acceptable for a 5–20 user internal POC where answer quality / citation fidelity is the primary success criterion. |
| **Claude Haiku 3.5** | ❌ Drop | Cheap and good, but adds Anthropic vendor surface without earning a unique role: Gemini 2.5 Pro already covers cheap-task duties on the same GCP-native stack. Doesn't justify a third approval. |

---

## 4. Recommendation

| Role | Model | Used for |
|---|---|---|
| **Primary** | **Claude Opus 4.6 GA** (Vertex Model Garden, `us-east5`) | All chat answers, cross-brand synthesis, executive summaries, Vectorless-Spike final synthesis after PageIndex tree-walk — every user-facing generation that requires premium faithfulness and citation discipline |
| **Fallback / cheap-task** | **Gemini 2.5 Pro** (GA, `us-central1`) | (a) Automatic failover when Opus is throttled / 5xx / cross-region call fails; (b) intentional routing for cheap tasks: query rewriting, chunk enrichment at ingest, conversation summarisation, PageIndex node-scoring, Memory Bank curation; (c) LLM-as-judge in the eval pipeline (kept independent from the premium primary so eval scoring is not vendor-correlated) |

### Why this pair wins

1. **Premium answer quality where it matters** — Opus 4.6 leads RAG faithfulness and prompt-injection robustness benchmarks. For a discoverability POC where wrong/misattributed answers destroy trust, paying ~$0.156/turn buys the highest defensible answer quality on the market.
2. **Two models, two vendors, but one billing surface** — Anthropic Opus is consumed via **Vertex AI Model Garden** (IAM-based access, GCP-billed, no separate Anthropic API key in Secret Manager, no second DPA at the data-plane level). Approval surface stays at exactly two models.
3. **Real, vendor-diverse fallback** — if Anthropic capacity in `us-east5` degrades, the router transparently fails over to Gemini 2.5 Pro in `us-central1`. Vendor-diverse fallback is genuinely robust, not just a same-family tier-down.
4. **Cheap tasks stay cheap on the fallback** — query rewrite, enrichment, conversation summary and Memory Bank curation route directly to Gemini 2.5 Pro (~$0.020/turn) so we don't pay Opus rates for housekeeping. This puts ~80% of token volume on the cheaper model.
5. **Independent judge** — the eval harness uses Gemini 2.5 Pro as LLM-as-judge against Opus answers. Different vendor + different training data avoids the vendor-correlation bias that hurts judge fidelity when judge and generator come from the same family.
6. **Cost is acceptable at POC scale** — with 20 users × 30 turns/day, blended monthly Vertex AI spend lands around **$1,200–1,500/month** (Opus dominant). Inside the POC budget for the answer-quality gain it buys, and disable-Opus is a single SQL flag flip.
7. **Reversible** — if cost telemetry shows Opus volume crowding out other budget, the router can demote Opus to a `premium` route and promote Gemini 2.5 Pro to default with a single `app_config` row update. No redeploy.

### Trade-offs we are accepting

- **Cost**: ~8× the per-turn cost of a Gemini-only setup. Acceptable at POC volume; needs re-evaluation before any volume scale-up.
- **Cross-region call**: orchestration in `us-central1` calls Opus in `us-east5`. Adds ~30–60 ms p50 latency and trivial inter-region egress. Documented in the latency budget.
- **Two vendor approvals**: legal will need an Anthropic-via-Vertex review. Mitigated by the fact that data does not leave GCP — Anthropic is consumed as a managed Vertex service.
- **Smaller context (200K vs 1M)**: enough headroom for the planned chunk-pack + conversation history; if a future multi-doc synthesis ever exceeds the budget, those queries can be routed to Gemini 2.5 Pro via a `long_context` route.

---

## 5. Routing policy (for `app_config.model_config`)

```jsonc
{
  "default_model": "claude-opus-4-6@latest",
  "fallback_model": "gemini-2.5-pro",
  "routes": {
    "complex_reasoning": {
      "primary":  { "provider": "anthropic", "model": "claude-opus-4-6@latest", "region": "us-east5"    },
      "fallback": { "provider": "google",    "model": "gemini-2.5-pro",        "region": "us-central1" }
    },
    "query_rewrite":   { "primary": { "provider": "google", "model": "gemini-2.5-pro", "region": "us-central1" } },
    "enrichment":      { "primary": { "provider": "google", "model": "gemini-2.5-pro", "region": "us-central1" } },
    "convo_summary":   { "primary": { "provider": "google", "model": "gemini-2.5-pro", "region": "us-central1" } },
    "memory_curation": { "primary": { "provider": "google", "model": "gemini-2.5-pro", "region": "us-central1" } },
    "judge":           { "primary": { "provider": "google", "model": "gemini-2.5-pro", "region": "us-central1" } }
  },
  "fallback_triggers": ["http_429", "http_5xx", "timeout_30s", "safety_block_recoverable", "cross_region_unreachable"]
}
```

This row lives in BigQuery `gap_genai_app.app_config` (`config_key='model_config'`, `version=N`, `is_current=TRUE`) and is hot-reloaded on the 60-second poll. Switching either model is a SQL `INSERT` + flag flip — no redeploy.

---

## 6. Decision log

| Date | Decision | Owner | Notes |
|---|---|---|---|
| 2026-05-12 | Initial recommendation: Gemini 2.5 Pro (primary) + Gemini 2.5 Flash (fallback). Runner-up: Claude Opus 4.6 GA (primary) + Gemini 2.5 Flash (fallback). | AI Architect | Superseded 2026-05-13. |
| 2026-05-13 | **FINAL recommendation per client direction**: **Claude Opus 4.6 GA primary** (`us-east5`, via Vertex Model Garden) + **Gemini 2.5 Pro fallback / cheap-task / judge** (`us-central1`). Drop Gemini 3.1 Pro preview, Gemini 2.5 Flash, Claude Opus 4.7 preview, Claude Haiku 3.5 from Day-1 scope. All cheap-task routes (query rewrite, enrichment, convo summary, Memory Bank curation, PageIndex node-scoring) collapse onto Gemini 2.5 Pro. Re-open bake-off in Phase 2 if cost telemetry justifies adding Flash for ingest-time enrichment. | Client + AI Architect | Approved Day-1 scope. |

---

*References used for benchmark and pricing figures (May 2026): Google Vertex AI pricing page, Anthropic pricing page, Artificial Analysis leaderboard, LMSYS Chatbot Arena, HELM, GPQA-Diamond authors, RULER long-context benchmark, RAGTruth dataset paper. All figures should be re-checked at the time of client sign-off.*
