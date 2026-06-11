# GAP GenAI Knowledge Discovery — Vertex AI Search variant (locked)

> **This is the chosen architecture.** Earlier variants (Variant A custom Vertex pipeline, Variant B managed RAG Engine, Variant D vectorless RAG spike) have been retired. This folder is now the single source of truth.

---

## 1. One-paragraph pitch

A **Google ADK** root agent (`DiscoveryAgent`) calls **Vertex AI Search (Discovery Engine)** once per turn via the `:answer` API. VAIS owns parsing, chunking, embedding, hybrid retrieval (BM25 + semantic + reranker), filter extraction, grounded synthesis, citations, and the **conversational chat-session store**. The agent does **no LLM call of its own**. Confluence pages are exported to HTML on a weekly delta into a GCS bucket and re-indexed by VAIS. The Web App is a thin chatbot with a sidebar (`/sessions`) and a chat surface (`/chat`); the Backend is a thin BFF that mirrors the same two endpoints.

## 2. Why this variant won

| Decision | Why |
|---|---|
| **VAIS owns retrieval + synthesis + sessions** | Removes the three things that go wrong most often in a custom RAG stack: chunking heuristics, rerank tuning, and per-user session state. All three are managed and version-pinned by Google. |
| **No app-side LLM call** | Single network hop per turn (`:answer`). No model-router service, no Opus/Gemini fallback logic, no separate prompt template to maintain. Lower latency, fewer failure modes. |
| **VAIS-native chat sessions** | Sessions are an engine-scoped resource keyed by `userPseudoId`. Multi-session-per-user, multi-turn anaphora, and resume-after-week all work out of the box. Verified end-to-end in [../tests/multi_session_smoke.ps1](../tests/multi_session_smoke.ps1). |
| **GCS-staged HTML corpus** | Decouples Confluence outages from query traffic, gives us full control over ACL tags (`<meta>` per page), and lets us re-index instantly without a connector roundtrip. |
| **ADK skills** | Every backend behaviour is a named, versioned tool with input/output schema and a golden-eval slice — so we can swap or A/B individual steps without redeploying the agent. |

## 3. What lives where

```
Web App (Cloud Run)
   /sessions  — chat-list sidebar (list, open, delete)
   /chat      — turn input + answer pane

Backend (Cloud Run, Google ADK)
   /sessions  — thin pass-through to VAIS sessions.{list,get,delete}; owner-gate on userPseudoId
   /chat      — single VAIS :answer call; format citations; log turn; record feedback
   Skills     — generate_answer · format_citations · record_feedback · log_turn
                list_sessions · delete_session

Vertex AI Search engine: gap-genai-discovery-search
   Vector Search (Hybrid)  — parse + chunk + embed + index + rerank + :answer
   Chat Sessions           — engine-scoped, userPseudoId-keyed, 90-day TTL
   Data Store              — gap-genai-discovery-corpus  (GCS unstructured, HTML)

Ingest (weekly delta)
   Confluence Exporter (Cloud Run Job)  →  GCS corpus-html  →  VAIS Reindex (Cloud Run Job)
   Cloud Scheduler drives both jobs.

Shared platform
   BigQuery (gap_genai_app):  experiments, experiment_clusters, feedback, golden_evals, eval_runs, app_config
   Cloud Observability Suite (Logging · Monitoring · Trace · Profiler · Error Reporting)
   IAM + Secret Manager (per-service SA, Confluence SA-PAT)
   Vertex AI Evaluation Service (weekly golden-set run)
```

See [../GCP_RAG_Architecture.drawio](../GCP_RAG_Architecture.drawio) for the high-level picture, [../High_Level_Design.drawio](../High_Level_Design.drawio) for the GCP-icon HLD with SKUs, [Architecture.md](Architecture.md) for the full mermaid + component table, and [Multi_Session_Flow.md](Multi_Session_Flow.md) for the per-user multi-session walkthrough.

## 4. What's already validated against the live engine

Engine: `gap-genai-discovery-search` (Enterprise + LLM add-on, `global`)
Datastore: `gap-genai-discovery-corpus` (500 synthetic HTML docs under `synthetic_corpus/pages/`)

| Capability | Evidence |
|---|---|
| Multi-user, multi-session-per-user | `tests/multi_session_smoke.ps1` Phase 1 — 4 sessions across 2 users |
| Multi-turn anaphora inside a session | Phase 2 — 12 turns, follow-ups like *"Which of those was the biggest win?"* resolve correctly |
| Cross-user isolation | Phase 3 — `sessions.list` filtered client-side on `userPseudoId`; zero leakage between alpha/beta |
| Resume a stale session with a new follow-up | Phase 4 — replayed history, fired *"Compare the strongest of those Old Navy wins to any Gap mobile-web tests"*, server-side turn count grew from 2 → 3 |
| ACL gate semantics | Phase 5 — `session.userPseudoId` matches owner; gateway rejects mismatched read |

## 5. Known operational findings (from the live test run)

| Finding | Implication |
|---|---|
| `sessions.list?filter=user_pseudo_id="…"` server-side filter is ignored | Backend must always client-side filter on `userPseudoId` after listing. |
| `queryRewritingSpec` is not a field on `QueryUnderstandingSpec` in v1 / v1beta | Rewriting is automatic when `session` is set on `:answer`. Don't pass that key. |
| `naturalLanguageQueryUnderstandingSpec` only available on v1beta endpoint | Backend calls `discoveryengine.googleapis.com/v1beta/...:answer`. |
| Sessions must be **engine-scoped**, not datastore-scoped | Datastore-scoped sessions return 400 on `:answer`. |

## 6. Day-1 scope

**In scope**
- 1 VAIS engine (`gap-genai-discovery-search`, Enterprise + LLM add-on)
- 1 GCS-unstructured datastore (`gap-genai-discovery-corpus`) pointed at `gs://gap-genai-discovery-corpus-html/pages/`
- 1 Cloud Run service `gap-genai-discovery-web` (chatbot)
- 1 Cloud Run service `gap-genai-discovery-agent` (ADK Discovery Agent)
- 1 Cloud Run Job `gap-genai-discovery-exporter` (weekly Confluence delta → HTML)
- 1 Cloud Run Job `gap-genai-discovery-reindex` (weekly `importDocuments`)
- BigQuery dataset `gap_genai_app` (product data: experiments, clusters, feedback, evals, app_config; **no log tables** — AR-5)
- Cloud Scheduler weekly cron for both jobs + weekly eval
- IAM least-privilege SAs, Secret Manager (Confluence **read-only service-account PAT**, AR-1)
- Cloud Observability Suite (Logging + Monitoring + Trace + Profiler + Error Reporting) — BigQuery is **not** used as a log sink (AR-5)
- Weekly golden-set run on Vertex AI Evaluation Service

**Out of scope (Phase 2)**
- Per-user ACL filtering (POC corpus is open to all `gap.com`)
- Custom embedding model (use VAIS default)
- Custom rerankers (use VAIS default)
- Memory Bank / long-term cross-session memory (VAIS sessions cover Phase 1)

## 7. Decision log

| Date | Decision | Owner |
|---|---|---|
| 2026-05-13 | Stand up the variant on **Vertex AI Search** with a **GCS-staged HTML corpus** (not the Google-managed Confluence connector — gives us ACL-tag control and decouples query traffic from Confluence outages). | AI Architect |
| 2026-05-17 | **No app-side LLM call.** All retrieval + synthesis + filter extraction inside VAIS `:answer`. Removes Model Router and Opus/Gemini fallback service. | AI Architect |
| 2026-05-17 | **VAIS-native chat sessions** for conversation history (engine-scoped, `userPseudoId`-keyed). Drop Agent Engine Sessions from this variant. | AI Architect |
| 2026-05-17 | Drop the `plan_query` and `extract_query_filters` skills. VAIS does both inside `:answer` via `naturalLanguageQueryUnderstandingSpec`. | AI Architect |
| 2026-05-18 | **Variant locked.** Retire Variant A, B, D. This folder is the only architecture going forward. | AI Architect |
| 2026-05-25 | **Observability Suite replaces BigQuery as the logging store** (BQ keeps only product data — experiments / clusters / feedback / golden_evals / eval_runs / app_config). **Confluence access via dedicated read-only service-account PAT** (no employee tokens). **React confirmed for dashboard frontend** (Streamlit dropped). See [../High_Level_Design.md](../High_Level_Design.md) §5 *Action items* for the full list. | AI Architect |

## 8. Risks

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | VAIS black-box ranking under-performs human-tuned hybrid on Test-Plan-style queries | Medium | Weekly golden-set eval; if recall@10 < 0.7 on the golden slice, escalate to Phase 2 reranker tuning. |
| R2 | `:answer` latency exceeds the 8s P95 budget | Medium | Smoke test showed p95 = 10.2s on cold sessions; warm sessions are 4–6s. Add a streaming response to the Web App. |
| R3 | Confluence export job lag (page edited but not yet re-indexed) | Low | Cloud Monitoring on `last_sync_at`; alert if > 8 days stale. |
| R4 | VAIS pricing surprise at higher volume | Medium | Cloud Billing budget alert on Discovery Engine line + per-query cost telemetry as OTel attributes (`llm_tokens_in/out`, `model_id`) in the Cloud Observability Suite. |
| R5 | `sessions.list` server-side filter behaviour changes (Google rolls out the documented filter) | Low | Keep client-side filter regardless; treat any server-side filter as an optimisation, not a guarantee. |

---

**Developer guides**

- [Frontend_Developer_Guide.md](Frontend_Developer_Guide.md) - Web App onboarding (stack, routes, REST contract, hooks, auth, env vars, build / deploy)
- [Backend_Developer_Guide.md](Backend_Developer_Guide.md) - ADK Discovery Agent onboarding (endpoints, skills, VAIS integration, BQ schema, IAM, Cloud Run sizing, jobs, smoke test)

**Quick links**

- [../GCP_RAG_Architecture.drawio](../GCP_RAG_Architecture.drawio) - solution architecture (whiteboard mirror)
- [../High_Level_Design.drawio](../High_Level_Design.drawio) - GCP HLD with SKUs
- [Architecture.md](Architecture.md) - full component table + mermaid
- [Multi_Session_Flow.md](Multi_Session_Flow.md) - per-user multi-session walkthrough
- [GCP_Services_Required.md](GCP_Services_Required.md) - onboarding-ready GCP service list
- [../tests/multi_session_smoke.ps1](../tests/multi_session_smoke.ps1) - live-engine validation script
