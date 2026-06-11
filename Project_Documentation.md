# GAP Experimentation Discoverability — Project Documentation

> **Type**: Master project reference (consolidates Meeting 1 + Meeting 2 + design + architecture)
> **Project**: GAP Experimentation Discoverability — RAG-based GenAI POC
> **Owner (Mathco)**: Kaushik B (offshore lead) · Aditya Govind Ravikrishnan (onsite point) · Syed Muzaffar J (engagement lead)
> **Owner (GAP)**: David Rose (primary), Prateek Oberoi (digital experimentation SME), Aravindhan (executive sponsor)
> **Status**: POC design locked · Implementation not yet started
> **Cloud**: Google Cloud Platform · Vertex AI

---

## Table of Contents

1. [Project Vision & Problem Statement](#1-project-vision--problem-statement)
2. [Current A/B Testing Workflow at GAP (As-Is)](#2-current-ab-testing-workflow-at-gap-as-is)
3. [Source Systems & Knowledge Assets](#3-source-systems--knowledge-assets)
4. [Personas & User Journeys](#4-personas--user-journeys)
5. [Project Scope](#5-project-scope)
6. [Functional Requirements](#6-functional-requirements)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [RAG Solution — Detailed Requirements & Instructions](#8-rag-solution--detailed-requirements--instructions)
9. [Architecture Reference](#9-architecture-reference)
10. [Data Contracts](#10-data-contracts)
11. [Design Constraints & Decisions](#11-design-constraints--decisions)
12. [Phase 1 vs Phase 2 Boundary](#12-phase-1-vs-phase-2-boundary)
13. [Delivery Plan](#13-delivery-plan)
14. [Risks & Open Questions](#14-risks--open-questions)
15. [Glossary](#15-glossary)

---

## 1. Project Vision & Problem Statement

### 1.1 Vision (one-liner)

Make GAP's 1,500+ historical A/B test reports instantly discoverable and synthesisable in natural language, so that any PDM, brand owner, analyst, or executive can answer "what have we already learned about X?" without reading the underlying Confluence pages.

### 1.2 The Problem

GAP runs ~450–500 digital experiments per year via the Test and Learn COE. Every closed test is documented as a Confluence "Test Plan" page and a "Test Results" page. The body of historical learning (~1,500 reports going back to 2017) is rich, structured, and high-quality, but in practice:

- **Only Prateek and David carry the institutional memory.** When questions land on tests from 2023, no one else can answer them.
- **PDMs and brand owners cannot self-serve** — there is no good way to search across years of reports, so they ask the experimentation team or open Confluence pages one by one.
- **Cross-test recall is manual.** When a new test is being designed, finding all relevant prior tests requires the analyst who ran them — newer team members, especially as the org moves to value-stream-aligned analysts, can't find them.
- **Executives have no level-1/level-2 insight.** Aravindhan asks "what's working?" and David has to manually pivot Excel.

### 1.3 The Goal (Phase 1)

A web application — chatbot-first for PDMs/analysts, dashboard-first for executives — that:

1. Lets a user ask natural-language questions over the full Confluence corpus.
2. Returns answers grounded in the source pages, with citations.
3. Surfaces metrics tiles (closed tests, wins, losses, $ incremental, $ averted loss) and a result breakdown.
4. Enables the experimentation team to find every prior relevant test in seconds when designing a new one.

### 1.4 Two Primary User Journeys (validated in Meeting 2)

| # | Journey | Persona | Today's pain | Tool's value |
|---|---------|---------|--------------|--------------|
| 1 | **Self-service search before escalation** | PDM, Brand owner | Must open many Confluence pages or escalate to Prateek's team | Ask in natural language, get cited answers |
| 2 | **Cross-test recall during test design** | **Senior Analyst** (Experimentation team) | Manual Confluence trawl, dependency on the analyst who ran prior tests | Query surfaces all relevant prior tests with summary, any analyst can synthesise |
| 3 | **Executive scan of program outcomes** | Leadership | No fast way to see what shipped vs. what was averted across a quarter | Same chat UI; answers tend to be aggregated WBR-style summaries grounded in the same corpus |

> **Personas (validated in Meeting 4):** PDM, Brand Partner, **Senior Analyst**, Leadership. Analyst level (junior vs. senior) does **not** change the flow - the scope and volume of work differs but the search / synthesis interaction is identical. The four personas above are confirmed; PM and Brand Manager interviews are still pending and may surface persona-specific prompt-chip variants but **no persona-conditional rendering** of the result page.

---

## 2. Current A/B Testing Workflow at GAP (As-Is)

This section consolidates Meeting 1 and Meeting 2 findings so the implementation team has a single canonical view of how GAP runs A/B tests today.

### 2.1 Process Diagram (per Prateek, Meeting 2)

The process is **circular, not linear**. Findings from completed tests feed straight back into the next brainstorming session.

```
        Brainstorming ──▶ Generate Ideas ──▶ Determine Feasibility ──▶ Coding
              ▲                                                            │
              │                                                            ▼
        Recommendations ◀── Data Analysis ◀── A/B Test (Optimizely + Adobe)
```

### 2.2 Stage-by-Stage

| # | Stage | Owner | Tools | Notes |
|---|-------|-------|-------|-------|
| 1 | **Brainstorming** | PDMs + Brand teams + Experimentation team | Meetings, Confluence | Three idea sources: PDM roadmap, brand-driven asks, experimentation team's own learnings. Cadence is mixed — scheduled (PDM roadmap) + ad-hoc (brand). |
| 2 | **Idea generation** | Same group | — | Often loops back from prior test learnings. |
| 3 | **Feasibility** | Experimentation team | — | Two sub-decisions: **can it be built?** and **is it worth testing?** Trivial changes get rolled out without an A/B. |
| 4 | **Test build** | Engineering | Optimizely | Two paths: **client-side** (Optimizely overrides on page load — fast, possible visible flicker) or **server-side** (coded in app — slower build, smoother UX). |
| 5 | **Execution** | Optimizely | Optimizely | Power calculation drives sample size + duration (typical run: 1–6 months; most 3–4 months). All tests are A/B (no DiD or quasi-experiments). |
| 6 | **Measurement** | Adobe Analytics | Adobe Experience Cloud, Databricks | Some flows into internal stores. |
| 7 | **Significance testing** | Analyst | Excel | Pulls metrics, runs significance tests, classifies Win / Loss / Flat. |
| 8 | **Documentation (Test Plan + Test Results)** | Experimentation team | Confluence | Standardised templates (largely stable since 2017). Covers ~80% of tests. |
| 9 | **SharePoint catalog row** | Analyst | SharePoint Experimentation Catalog | Manual metadata entry per test. |
| 10 | **Periodic pivoting** | David | Excel pivots | Every 3–4 weeks, classified by tactic / brand / channel / device. |
| 11 | **Recommendation loop** | Experimentation team → Brands/PDMs | Meeting + Confluence link share | Feeds findings + optimisation opportunities into the next brainstorm. |

### 2.3 Org / Team Context

- **Recent restructure**: GAP has moved to **value streams** — PLP, PDP, Shopping Bag, Checkout. Each value stream has a dedicated PDM.
- **Future intake**: PDMs are intended to be the single channel for new test requests. Brand-driven ad-hoc requests still exist today.
- **Resourcing TBD**: Experimentation team is planning to align analysts to value streams.
- **Digital vs Store**: Dave's org owns both. A separate dedicated resource handles retail/store experimentation. **The tool is digital-only for Phase 1.**

### 2.4 Test Outcome Classification

| Outcome | Meaning |
|---------|---------|
| **Win** | Change increases revenue / CTR / target KPI; usually rolled out. |
| **Loss** | Change has negative impact; not rolled out — counted as "averted revenue loss". |
| **Flat** | No statistically significant impact. **Most tests fall here.** |

### 2.5 Tactic Categories (used by David's pivot)

Quality · Time Savings · Urgency · Value

### 2.6 Cross-Brand Test Behaviour

- **Same test, different brand** is the norm — Athleta + Banana Republic (premium customers) vs. Old Navy + Gap (discount customers).
- Trivial changes (font) tested once, rolled across brands.
- Funnel-critical changes (Bag, Checkout) tested per brand.
- **Same test, same brand, repeated over time** is also common for **promo-driven tests** where each promo window is too short for sample size.

### 2.7 Volume Statistics

| Metric | Value |
|--------|-------|
| Lifetime experiments | ~1,500 (last 6–7 years) |
| FY 2025 | 450–490 tests |
| FY 2026 (so far) | 20–30 tests |
| Phase 1 RAG corpus (proposed) | FY25/26 → ~500–600 reports for tuning, then expand to full 1,500 |
| Confluence coverage of all tests | ~80% (rest live in email / PDF / PPT — out of Phase 1 scope) |

---

## 3. Source Systems & Knowledge Assets

### 3.1 Primary Source — Confluence (Test and Learn COE Space)

**This is the canonical source for Phase 1 RAG ingestion.** Everyone with a `gap.com` email can read it; it spans 2017 → 2026.

Two standardized pages per test:

#### 3.1.1 Test Plan page — fields

- Brand
- Page / Funnel / Channel
- Audience Limitation
- Problem Statement
- Hypothesis
- Experimental Changes (Control vs Challenger description)
- Additional Documents (e.g., comparison snapshots)
- **Significance Calculations & Experimental Design**
  - Brand · Scenarios (e.g., 1 Control + 1 Challenger) · Primary KPI (e.g., OPV) · Minimum Detectable Lift (e.g., ~0.4%) · Confidence Threshold (~80%) · Power Threshold (80%) · Sample Size (e.g., ~7.2MM visits/variation) · Estimated Duration (e.g., 2–3 weeks) · Sample Size Calc Assumptions · Test Exposure (e.g., 100% / 50–50 split) · Secondary Metrics
- Adobe Dashboard Link (Adobe Experience Cloud)
- **Measurement** (4 buckets):
  - Metrics (All Experiments) — Conversion Rate (OPV), Net RPV, AOS, UPT, AUR, Total Visits, Visits Split by Visit/Visitor, Variation Overlap
  - Metrics (Test Specific) — e.g., PDP Views/Visit, Add-to-Bag Rate, PDP→Bag Conversion, PDP Certona Engagement Rate, PDP Exit Rate
  - Segments (All Experiments) — New vs Returning
  - Segments (Test Specific) — Desktop vs Mobile
- Custom Metrics — Description/Location, Custom Variable, Notes (track once / always)

#### 3.1.2 Test Results page — fields

- Overview (restated hypothesis)
- Variation Description with Control + Challenger screenshots
- DETAILS — directional commentary, statistical significance disclaimer, breakdowns by Device Type and Visit Type
- Impacts table — Net RPV · OPV · AOS · UPT · AUR · Product Views/Visit · PDP→SB · Add-to-Bag Rate · Exit Rate · Engagement Rate · Incremental delta row
- Product Mix
- Gross Margin (GMS/Visit)
- Findings summary
- Recommendation
- Optimization Opportunities

### 3.2 Secondary Source — SharePoint Experimentation Catalog

A flat list with one row per test. Phase 1 ingests these as enriched metadata that supports filtering on the dashboard view.

Fields: Test Name · Test Description · Brand · Market · Source · Start/End Date · Platform · Device · Channel · Channel Section · Audience · Vendor · Primary KPI · Other KPI · Winning/Losing Delta % · Estimated Annualized Value ($) · Recommendation · Confluence Result Link · Recommendation Adopted · Test Insights · Return Rate · Attachments
Statuses: All Items / Closed Tests / Inflight / Live

### 3.3 Out-of-Scope Sources (Phase 1)

| System | Why out |
|--------|---------|
| Adobe Customer Journey | Test data source, not a knowledge artefact |
| Databricks | Same |
| Optimizely | Test runner, not a knowledge artefact |
| Excel pivot workbooks | Derivative of Confluence — not separately ingested |
| Power BI dashboard | Being replaced |
| Email / PDF / PPT findings (~20% of tests) | Not standardised — defer to Phase 2 |
| Confluence images | Image content extraction not in Phase 1 (stretch only) |
| Store / customer-related tests | Digital only for Phase 1 |

---

## 4. Personas & User Journeys

### 4.1 Personas

| Persona | Role | Primary need | Default landing |
|---------|------|--------------|-----------------|
| **Executive** (Aravindhan, VPs, SVPs) | Senior leadership | "What's working in our experiments?" | Dashboard view (metrics tiles + breakdown) with chatbot below |
| **Experimentation team** (David, Prateek, analysts) | Test designers, knowledge holders | Cross-test recall during design; freeing institutional memory | Chatbot first |
| **PDM / Brand / App owner / UX lead** | Test requestors | "Has this been done? What did we learn?" before requesting | Chatbot first |

### 4.2 Representative Questions (designed-for)

- "What checkout-related tests have we run on Old Navy in the last 12 months?"
- "Summarize learnings from PDP recommendation tests across all brands."
- "Have we tested removing the free-shipping thermometer? What happened?"
- "Show me all Athleta tests where the challenger lost on conversion."
- "What's our average lift for Quality-tactic tests vs. Time Savings?"
- "Did the Internal Product Recommendation Model V3 win or lose vs V2?"
- "What metric is 'Gross Margin Dollar per Visit' and where did we use it?"

### 4.3 Confluence Access Today

- Anyone with `gap.com` email can read the Test and Learn COE space.
- In practice PDMs/brands rarely traverse it themselves — they wait for Prateek's team to bring findings or share specific page links. **The tool removes this dependency.**

---

## 5. Project Scope

### 5.1 In Scope (Phase 1)

| # | Capability |
|---|------------|
| 1 | Ingest ~1,500 Confluence Test Plan + Test Results pages from Test and Learn COE space |
| 2 | Ingest SharePoint Experimentation Catalog rows as metadata |
| 3 | Daily delta sync from both sources |
| 4 | Vector embeddings + metadata indexing in Vertex AI Vector Search + BigQuery |
| 5 | RAG-powered chatbot with citations to Confluence pages |
| 6 | Search-only mode (return matching tests without an LLM answer) |
| 7 | Multi-turn conversations with history |
| 8 | Persona-aware landing pages (Executive vs Analyst/PDM) |
| 9 | Dashboard view replacing the current Power BI stopgap (metrics tiles, result breakdown, filter pane) |
| 10 | User feedback (thumbs up/down + free-text correction) |
| 11 | Admin surface to update prompts, model config, and policies via Firestore |
| 12 | A/B testing of LLMs and prompt variants |
| 13 | Cost & token tracking dashboard |
| 14 | Configurable Model Layer — switch between **Claude Opus 4.6 GA** (primary, `us-east5`) and **Gemini 2.5 Pro** (fallback / cheap-task / judge, `us-central1`) without redeploy |

### 5.2 Out of Scope (Phase 1)

- Forward-looking recommendations ("what should I test next?" cold)
- Post-rollout monitoring (did the win hold up at scale?)
- Adobe / Databricks / Optimizely automation
- Automating the human-written Test Results write-up (David is firm on this)
- Image content extraction from Confluence pages (stretch only)
- Store / customer experimentation tests
- Email / PDF / PPT findings ingestion
- Multi-tenant isolation, full PII pipeline, GDPR DSR pipeline

### 5.3 Phase 2 Candidates

1. Forward-looking test recommendations (given a new idea → suggest design + KPIs based on prior tests)
2. Scaled-test tracking (predicted lift vs. actual lift after rollout)
3. Image content from Confluence
4. Store / customer test parsing
5. Recommendation augmentation (suggest analysis type, metrics, success criteria, client- vs server-side, duration, sample size)
6. Email / PDF / PPT ingestion for the ~20% of tests not in Confluence

---

## 6. Functional Requirements

### 6.1 Ingestion (Batch)

| ID | Requirement |
|----|-------------|
| FR-I-1 | Pull all current pages from the Test and Learn COE Confluence space via REST API (one-time bulk run). |
| FR-I-2 | Pull the SharePoint Experimentation Catalog list via Microsoft Graph API. |
| FR-I-3 | Run a daily delta job triggered by Cloud Scheduler that pulls only items modified since the last successful watermark. |
| FR-I-4 | Store raw HTML and attachments in Cloud Storage (`gs://<bucket>/raw/<source>/<doc_id>/...`). |
| FR-I-5 | Extract structured metadata fields per Section 10 into BigQuery `document_metadata`. |
| FR-I-6 | Chunk text into 512–1024 token chunks with 50–100 token overlap, preserving section boundaries. |
| FR-I-7 | Enrich each chunk with section header + parent page summary + 2–3 hypothetical questions (HyDE-lite). |
| FR-I-8 | Generate 768-dim embeddings via Vertex AI `text-embedding-004` and upsert to Vector Search with metadata. |
| FR-I-9 | Track every job in `pipeline_jobs`; failed pages do not abort the job — they are recorded for retry. |
| FR-I-10 | Re-ingestion must be idempotent (re-running over the same page overwrites cleanly). |

### 6.2 Discoverability (Query Time)

| ID | Requirement |
|----|-------------|
| FR-Q-1 | Accept a natural-language question via `POST /api/genai/chat`. |
| FR-Q-2 | Apply input prompt-filter (length cap, injection patterns, topic allow-list). |
| FR-Q-3 | Detect obvious metadata filters in the question (brand, page_funnel) and pre-filter the vector search. |
| FR-Q-4 | Retrieve top-50 candidates from Vertex AI Vector Search. |
| FR-Q-5 | Rerank to top-10 using Vertex AI Ranking API (`semantic-ranker-default-001`). |
| FR-Q-6 | Assemble context within token budget (system prompt + history + RAG context + question). |
| FR-Q-7 | Send to Model Router; route by task per Firestore `model_config`. |
| FR-Q-8 | Apply Vertex AI Grounding for citations. |
| FR-Q-9 | Apply output prompt-filter (citation requirement, hallucination heuristic, length cap). |
| FR-Q-10 | Return response with inline `[n]` citations mapped to Confluence URLs and chunk ids. |
| FR-Q-11 | Persist conversation turn in Firestore (`conversations/{id}/messages`). |
| FR-Q-12 | Support search-only mode (`POST /api/genai/search`) returning ranked chunks without a generated answer. |

### 6.3 Dashboard

| ID | Requirement |
|----|-------------|
| FR-D-1 | Top-row metric tiles: Total Tests · Closed Tests · Wins · Losses · Flat · Incremental Revenue · Averted Revenue Loss · Tests Needing Attention. |
| FR-D-2 | Filter pane: Start/End Date · Brand · Market · Source · Platform · Device · Channel · Channel Section · Audience · Vendor · Primary KPI · Other KPI · Tactic · Recommendation Adopted. |
| FR-D-3 | Result Breakdown donut (Win / Loss / Flat). |
| FR-D-4 | Program Insights and Test Insights panes (LLM-generated summaries, refreshed daily). |
| FR-D-5 | Drill-down to the underlying tests with links to Confluence. |
| FR-D-6 | Persona-aware default view (Executive → dashboard first; Analyst/PDM → chatbot first). |

### 6.4 Feedback & Admin

| ID | Requirement |
|----|-------------|
| FR-F-1 | Thumbs-up/down + 1–5 rating + optional free-text correction per response. |
| FR-F-2 | Admin can edit `prompts/<feature>_v<n>` and toggle which version is active in Firestore. |
| FR-F-3 | Admin can edit Model Router config and policy doc in Firestore; service hot-reloads within 60s. |
| FR-F-4 | Admin can trigger ad-hoc bulk re-ingest or delta run. |

### 6.5 Authentication & Authorisation

| ID | Requirement |
|----|-------------|
| FR-A-1 | Sign-in via Google Workspace OAuth; restrict to `gap.com` domain. Edge enforcement is via Identity-Aware Proxy (IAP) enabled directly on the Cloud Run `web` service (Cloud Run native IAP). |
| FR-A-2 | Admin role determined by membership in the `gap-genai-admins@gap.com` Google Group; pilot-user access by membership in `gap-genai-users@gap.com`. No application-level user or role table. |
| FR-A-3 | All API calls require an OAuth ID token (IAP-validated for the Web App; IAM `run.invoker` for service-to-service). |
| FR-A-4 | **Flat read access at the app layer (no app-level RBAC)** - any authenticated `gap.com` user with `gap-genai-users` membership can search any indexed experiment page. Validated with Prateek in Meeting 4 §9: Confluence is already open to all GAP IDs and one PDM owns a site section across all four brands. |
| FR-A-5 | Audit captured via Cloud Audit Logs (Admin Activity + Data Access) + IAP request logs + application telemetry, all sunk to BigQuery `gap_genai_app.audit_logs` / `iap_logs` / `request_logs` with 1-year retention. See [`PSEC/User_Provisioning_And_Audit.md`](PSEC/User_Provisioning_And_Audit.md). |

---

## 7. Non-Functional Requirements

| Category | Target |
|----------|--------|
| **Concurrent users (POC)** | 5–20 |
| **Peak RPS** | ~5 |
| **End-to-end chat latency P95** | < 5s |
| **Retrieval latency** | < 350ms (top-10 reranked) |
| **Bulk ingest of 1,500 reports** | < 2 hours |
| **Daily delta** | < 15 minutes |
| **Citation-present rate (output filter pass rate)** | > 95% |
| **Initial thumbs-up target** | > 70% |
| **Model swap time (Firestore edit → live)** | < 60s (no redeploy) |
| **Data freshness (Confluence change → searchable)** | < 24h |
| **Logging overhead per request** | < 5ms |
| **Encryption** | TLS 1.2+ in transit; GCP defaults at rest |
| **Audit** | Every request logged with `request_id`, `user`, `model_id`, `tokens_in/out`, `latency_ms` |

---

## 8. RAG Solution — Detailed Requirements & Instructions

This is the core implementation guidance for the RAG team.

### 8.1 RAG Stack Decisions (locked)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| RAG engine | **Vertex AI Agent Builder** | Managed, integrates natively with Vector Search + Grounding |
| Embeddings | **Vertex AI `text-embedding-004`** (768-dim) | GCP-native, batch-friendly |
| Vector store | **Vertex AI Vector Search** (TreeAH index, cosine) | POC-scale, no operational overhead |
| Reranker | **Vertex AI Ranking API** `semantic-ranker-default-001` | Cuts noise after top-50 vector recall |
| Citations | **Vertex AI Grounding** | Inline `[n]` references with source chunk ids |
| LLMs | **Claude Opus 4.6 GA** (primary, Vertex Model Garden, `us-east5`) · **Gemini 2.5 Pro GA** (fallback / cheap-task / judge, `us-central1`) | Premium synthesis from Anthropic with vendor-diverse fallback + cheap-task routing on Google native |
| Model selection | **Firestore-driven Model Router** | Swap models without redeploy; supports A/B split |
| Operational store | **Firestore** | Prompts, conversations, model_config, policies, feedback |
| Analytics store | **BigQuery** | Document metadata, logs sink, cost rollups, feedback aggregates |

### 8.2 Ingestion Instructions

#### 8.2.1 Connector design

- One container image with two entry points: `bulk_load.py` and `delta_extract.py`.
- Watermark stored in BigQuery `ingestion_state(source, last_run_watermark, updated_at)`.
- Confluence: `atlassian-python-api`. Paginate via `cql` with `lastModified > <watermark>`.
- SharePoint: `msgraph-sdk` against the Experimentation Catalog list.
- Tokens in Secret Manager; service account scoped to `secretmanager.secretAccessor` + `storage.objectAdmin` on the raw bucket only.

#### 8.2.2 Parsing rules

- Confluence body is HTML — parse with BeautifulSoup. The Test Plan and Test Results templates have stable section anchors (`Hypothesis`, `Variation Description`, `Significance Calculations & Experimental Design`, `Measurement`, `DETAILS`, `Impacts`, `Recommendation`).
- For each section: extract heading, body text, tables (preserve as Markdown tables in chunk text), and any embedded screenshots' alt-text/captions.
- Extract metadata fields per Section 10 deterministically from the templated tables. If a field is missing or the page predates the current template (some 2017–2018 pages), fall back to a Gemini 2.5 Pro call to extract the field and tag `metadata_quality = "llm_inferred"`.
- Always retain the original Confluence page URL, page id, version id, last-modified timestamp, and author.

#### 8.2.3 Chunking rules

| Rule | Detail |
|------|--------|
| Default strategy | Recursive section-aware splitting; never split a chunk across `Hypothesis`, `Variation Description`, `Impacts`, `Recommendation` boundaries. |
| Default size | 512–1024 tokens, 50–100 token overlap. |
| Tables | Whole table as one chunk if ≤ 1024 tokens; otherwise split by row groups, repeating the header. |
| Metric definitions | Each `(metric_name, definition)` pair gets its own chunk so "what is Gross Margin Dollar per Visit?" can return a clean answer. |

#### 8.2.4 Enrichment rules

Each chunk's stored text = `[brand] · [page_funnel] · [section_header]\n[parent_page_one_liner]\n\n[chunk_body]\n\nHypothetical questions: [q1] [q2] [q3]`.

- One-liner generated **once per page** (cached) via Gemini 2.5 Pro.
- 2–3 hypothetical questions generated per chunk via Gemini 2.5 Pro (HyDE-lite).
- Toggle in Firestore: `model_config.routes.enrichment.enabled`.

#### 8.2.5 Embedding & upsert

- Batch up to 250 inputs per Vertex AI Embeddings call.
- Store `embedding_model_version` alongside each vector for traceable re-indexing.
- Upsert via Vertex AI Vector Search streaming API.

#### 8.2.6 Retry / failure handling

- Per-page failure recorded in `pipeline_jobs.errors[]`; job continues.
- Retry job (`retry_failed.py`) replays failed pages from the latest run.
- DO NOT retry indefinitely — after 3 failed attempts a page is quarantined and surfaced in admin UI.

### 8.3 Query-Time Instructions

#### 8.3.1 Pipeline (numbered)

1. User submits query → Web App → Orchestration (Cloud Run, FastAPI).
2. Input prompt-filter: length ≤ 4000 chars; reject known injection patterns; soft topic allow-list.
3. Filter extraction: detect brand / value_stream mentions → metadata pre-filter for vector search.
4. Vertex AI Agent Builder embeds query + executes vector search → top-50.
5. Vertex AI Ranking API → top-10.
6. Agent Builder assembles context (top-10 chunks + system prompt from Firestore + conversation history).
7. Model Router resolves task → model from `model_config.routes`.
8. LLM call (Gemini or Claude). On failure → fallback model. On both fail → error to user.
9. Vertex AI Grounding attaches `[n]` citations.
10. Output prompt-filter: citation present (if factual question), hallucination heuristic, length cap.
11. Response returned with `citations[]` — each item is `{n, page_url, page_title, chunk_id, brand, page_funnel, last_modified}`.
12. Conversation turn persisted in Firestore.
13. Structured log entry written to Cloud Logging (sinks to BigQuery `genai_logs.requests`).

#### 8.3.2 Prompt template — base chat (`chat_v1`)

```
You answer questions about GAP A/B testing results using ONLY the provided context.
If the answer is not in the context, say so plainly — do not speculate.

Cite every factual claim with [n] referencing the numbered chunk. When the user asks
about a specific brand, page, or KPI, surface those values explicitly. When summarising
multiple tests, group by brand and outcome (Win / Loss / Flat).

Context:
{{context}}

Conversation history:
{{conversation_history}}

User question: {{question}}
```

Stored in Firestore `prompts/chat_v1`. Future versions: `chat_v2`, `chat_v3`. Active version controlled by `prompts/active_pointer`.

#### 8.3.3 Model routing strategy

| Route | Default primary | Fallback | Notes |
|-------|----------------|----------|-------|
| `complex_reasoning` (default chat) | `claude-opus-4-6@latest` (us-east5) | `gemini-2.5-pro` (us-central1) | Vendor-diverse fallback on `http_429` / `http_5xx` / `timeout_30s` / `cross_region_unreachable` |
| `query_rewrite` | `gemini-2.5-pro` | — | Cheap-task tier on the fallback model |
| `enrichment` (ingest) | `gemini-2.5-pro` | — | Per-chunk; runs at ingest in the Cloud Run Job |
| `convo_summary` | `gemini-2.5-pro` | — | Sliding-window compaction for sessions older than 6 turns |
| `memory_curation` | `gemini-2.5-pro` | — | Vertex Agent Engine Memory Bank curation on session close |
| `judge` (eval) | `gemini-2.5-pro` | — | LLM-as-judge for `citation_accuracy` metric — kept on a different vendor than the primary to avoid scoring bias |

### 8.4 Citation & Grounding Rules

- Every factual claim in the response MUST have at least one `[n]` citation.
- Each `[n]` MUST resolve to a chunk that exists in the corpus (validated against BigQuery `chunk_metadata`); unknown chunk ids are dropped.
- Citation payload always includes the Confluence URL so the UI can render a clickable link.
- If output filter detects zero citations on a factual question, append a "couldn't find a sourced answer" disclaimer and surface low-confidence chip in UI.

### 8.5 Prompt Filter (POC scope, simple)

**Input checks:**
- Length cap: 4000 chars.
- Injection regex: `ignore (all|previous) (instructions|rules)`, `system prompt`, role-redefinition patterns. Configurable in Firestore.
- Soft topic allow-list: A/B testing, experiments, brands, KPIs, results. Out-of-scope queries get a polite redirect, not a hard block.

**Output checks:**
- Citation requirement (factual questions).
- Hallucination heuristic: any brand or metric in the response that isn't present in retrieved chunks → flag.
- Length cap: 2000 tokens.

**Out of POC** (deferred): full PII pipeline (Presidio), ML-based content categorisation, per-user rate limiting. Justification: corpus is internal experimentation data with no customer PII; users are gap.com authenticated.

### 8.6 Conversation Management Rules

- Sliding window: last 6 turns verbatim.
- Older turns: replaced by a one-shot Gemini 2.5 Pro summary message.
- TTL: 90 days in Firestore.
- Per-user isolation by `user@gap.com` claim.

### 8.7 Quality Gates Before Pilot Goes Live

| Gate | Threshold |
|------|-----------|
| Citation-present rate on test set | > 95% |
| Hallucination flag rate on test set | < 10% |
| End-to-end P95 latency | < 5s |
| Retrieval recall@10 on labelled question set | > 80% |
| At least 2 prompt versions A/B-tested | required |
| At least 1 model A/B running (Claude Opus 4.6 vs Gemini 2.5 Pro on `complex_reasoning`) | required |

### 8.8 RAG-Specific Engineering Conventions

- Single Cloud Run Orchestration service (FastAPI). No API gateway in front.
- All LLM calls go through the Model Router — **no direct SDK calls from feature code**.
- All prompts live in Firestore — **no hard-coded prompts in code**.
- Every LLM call writes a structured log entry with `model_id`, `route`, `tokens_in`, `tokens_out`, `latency_ms`, `ab_variant`.
- Cost rollups computed nightly in BigQuery from the log sink — no second cost-tracking system.

---

## 9. Architecture Reference

The canonical architecture diagram (Mermaid) lives in [GCP_RAG_Architecture.md](GCP_RAG_Architecture.md). The detailed component-level design lives in [Vertex_AI_Search_Variant/Architecture.md](Vertex_AI_Search_Variant/Architecture.md) (with the developer guides and `GCP_Services_Required.md` alongside). High-level recap:

```
Confluence + SharePoint
        │
        ▼
Cloud Run Jobs (Bulk + Daily Delta + Parse/Chunk/Embed)
        │
        ├─▶ Cloud Storage (raw)
        ├─▶ BigQuery (metadata)
        └─▶ Vertex AI Vector Search (vectors)

Web App (Cloud Run) ─▶ Orchestration (Cloud Run) ─▶ Vertex AI Agent Builder
                                                       │
                                                       ├─▶ Vector Search → Ranking API
                                                       ├─▶ Model Router → Gemini / Claude
                                                       └─▶ Grounding → Citations
                                                       
Firestore: prompts · conversations · feedback · model_config · policies
Cloud Logging ─sink─▶ BigQuery (analytics + cost)
```

---

## 10. Data Contracts

### 10.1 BigQuery `document_metadata`

| Field | Type | Source |
|-------|------|--------|
| `doc_id` | STRING | Confluence page id (or SharePoint item id) |
| `source` | STRING | `confluence` / `sharepoint` |
| `url` | STRING | Page URL |
| `title` | STRING | |
| `brand` | STRING | Old Navy / Gap / Athleta / BR |
| `page_funnel` | STRING | PDP / PLP / Bag / Checkout / Other |
| `value_stream` | STRING | Mapped from `page_funnel` |
| `audience` | STRING | All Customers / segment |
| `primary_kpi` | STRING | e.g., OPV |
| `tactic` | STRING | Quality / Time Savings / Urgency / Value |
| `hypothesis` | STRING | |
| `experiment_changes` | STRING | Control vs Challenger summary |
| `outcome` | STRING | Win / Loss / Flat / Inconclusive |
| `winning_losing_delta_pct` | FLOAT64 | |
| `est_annualized_value_usd` | FLOAT64 | |
| `recommendation_adopted` | BOOL | |
| `metrics_specific` | ARRAY<STRING> | |
| `created_date` | DATE | |
| `start_date` | DATE | |
| `end_date` | DATE | |
| `author` | STRING | |
| `last_modified` | TIMESTAMP | Watermark for delta |
| `metadata_quality` | STRING | `parsed` / `llm_inferred` |

### 10.2 BigQuery `chunk_metadata`

| Field | Type |
|-------|------|
| `chunk_id` | STRING |
| `doc_id` | STRING |
| `position` | INT64 |
| `chunk_size_tokens` | INT64 |
| `overlap_tokens` | INT64 |
| `strategy` | STRING |
| `section` | STRING |
| `context_header` | STRING |
| `hypothetical_questions` | ARRAY<STRING> |
| `embedding_model_version` | STRING |

### 10.3 BigQuery `genai_logs.requests`

| Field | Type |
|-------|------|
| `request_id` | STRING |
| `user` | STRING |
| `feature` | STRING (`chat` / `search` / `summarization`) |
| `route` | STRING |
| `model_id` | STRING |
| `ab_variant` | STRING |
| `tokens_in` / `tokens_out` | INT64 |
| `latency_ms` / `retrieval_ms` / `llm_ms` | INT64 |
| `citations_count` | INT64 |
| `filter_flags` | ARRAY<STRING> |
| `status` | STRING |
| `timestamp` | TIMESTAMP |

### 10.4 Firestore collections

| Collection | Doc id | Contents |
|------------|--------|----------|
| `model_config` | `active` | Model Router config |
| `policies` | `active` | Filter & feature-flag policy |
| `prompts` | `<feature>_v<n>` | Versioned templates |
| `prompts` | `active_pointer` | Map of feature → active version |
| `conversations` | `<conversation_id>` | Header (user, created_at) |
| `conversations/{id}/messages` | `<message_id>` | Per turn |
| `feedback` | `<feedback_id>` | Per response |

---

## 11. Design Constraints & Decisions

### 11.1 Mandates from GAP

| # | Mandate | Source |
|---|---------|--------|
| 1 | GCP for the data backbone | David Rose (Aravindhan-driven strategic shift) |
| 2 | Confluence is the canonical source for Phase 1 | Meeting 2 |
| 3 | The human writes the Test Results — do **not** automate the write-up | David Rose |
| 4 | IDs raised via David, not Holly | Aditya / Meeting 2 |
| 5 | Insights ≠ Recommendations — Phase 1 is summarisation + simple historical patterns only | Syed |
| 6 | Digital tests only for Phase 1 (no store) | Meeting 2 |

### 11.2 Mathco Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Model Router with Firestore config | Swap LLMs without redeploy; supports A/B |
| 2 | Vertex AI Agent Builder over hand-rolled RAG | Managed, integrated grounding + ranking |
| 3 | No API gateway / load balancer for POC | 5–20 users; Cloud Run is sufficient |
| 4 | No separate semantic cache tier for POC | LLM cost at this scale doesn't justify it |
| 5 | Looker Studio over Grafana / Synapse | GCP-native, free, fast to wire |
| 6 | Tune on FY25/26 corpus (~500–600 reports) before scaling to 1,500 | Faster iteration on prompt + chunking quality |
| 7 | Image extraction is a stretch goal, not a commitment | Confluence images are mostly screenshots — limited NL value |

---

## 12. Phase 1 vs Phase 2 Boundary

| Capability | Phase 1 | Phase 2 |
|------------|---------|---------|
| Discovery search (NL Q&A over Confluence) | ✅ | |
| Summarisation across multiple tests | ✅ | |
| Level-1/2 historical insights ("5 ran, 4 won, common factor X") | ✅ | |
| Citations to Confluence | ✅ | |
| Dashboard view replacing Power BI | ✅ | |
| Filters on dashboard + chat | ✅ | |
| User feedback collection + quality dashboard | ✅ | |
| Cold "what should I test next?" | | ✅ |
| Augmented test design (suggest analysis type, KPIs, success criteria, sample size, server vs client) | | ✅ |
| Scaled-test tracking (predicted vs actual lift after rollout) | | ✅ |
| Image content extraction | stretch | ✅ |
| Store / customer tests | | ✅ |
| Email / PDF / PPT ingestion | | ✅ |

---

## 13. Delivery Plan

### 13.1 Indicative Phasing (POC, ~10 weeks)

| Phase | Weeks | Deliverable |
|-------|-------|-------------|
| 1. Foundation | 1–2 | GCP project, IAM, Terraform skeleton, Vector Search index, Firestore seed |
| 2. Batch Ingestion | 2–4 | Confluence + SharePoint connectors, chunking, embeddings, bulk run on FY25/26 corpus, daily delta |
| 3. Discoverability MVP | 4–6 | Orchestration service, Agent Builder integration, Model Router (Gemini default), prompt management, basic prompt filters, conversation management, Web App + Chatbot UI |
| 4. Quality & Operations | 6–8 | Feedback collection, log sink to BigQuery, cost tracking, Looker Studio dashboards, A/B model run (Claude Opus 4.6 vs Gemini 2.5 Pro on `complex_reasoning`) |
| 5. Pilot & Hardening | 8–10 | Onboard 5–20 pilot users, weekly prompt tuning, runbooks, expand to full 1,500 corpus |

Phase 1 V1 target per SOW: ~September 4, 2026.

### 13.2 Communication

- Weekly status to GAP with proactive delay attribution.
- Customer kickoff was scheduled for May 4–5, 2026.
- In-person sync with David / Holly post-Atlanta (Syed).

### 13.3 Access & Onboarding (per Meeting 2 update)

- IDs raised via Prateek-walkthrough route so they go to Dave for approval (~7 IDs needed).
- After IDs: GAP Sourcing → Dave → external MFA setup. Total ~15 minutes to raise + 1 day to approve.
- Aditya following up with Greg Christensen on the GCP project provisioning process (Databricks-equivalent path).

---

## 14. Risks & Open Questions

### 14.1 Risks

| # | Risk | Likelihood | Mitigation |
|---|------|-----------|------------|
| 1 | GCP project provisioning gated by an architecture review | Medium | Aditya → Greg Christensen; in parallel, prove pieces in personal GCP project |
| 2 | Confluence access not provisioned in time | Medium | Use exported HTML samples during early dev; switch when IDs land |
| 3 | Old (2017–2018) Confluence pages don't fit current template | Medium | LLM-based field-extraction fallback; tag `metadata_quality = "llm_inferred"` |
| 4 | Hallucinated answers undermine trust | Medium | Mandatory citations + hallucination heuristic + grounding confidence chip in UI |
| 5 | Claude Opus 4.6 quota / regional outage in `us-east5` | Medium | Model Router fails over to Gemini 2.5 Pro on `http_429` / `http_5xx` / `timeout_30s` / `cross_region_unreachable`; Cloud Monitoring alert on Opus error-rate; admin can promote Gemini 2.5 Pro to primary via `app_config` SQL update |
| 6 | Cost spike on Claude Opus 4.6 (primary) | High | Cloud Billing budget alert on Vertex AI line ($1.5K/month); per-turn cost telemetry in `request_log`; admin can flip `complex_reasoning` primary to Gemini 2.5 Pro via single `app_config` SQL update (no redeploy); cheap tasks already on Gemini 2.5 Pro keep ~80% of token volume off Opus |
| 7 | Confluence images contain key signal we lose by ignoring | Low–Medium | Document as known limitation; stretch experiment with GCS → Gemini multi-modal scan |
| 8 | "Recommendations" expectation mismatch with Aravindhan | Medium | Level-set in kickoff; tight Phase 1/2 boundary above |
| 9 | 80% Confluence coverage means ~20% of tests are invisible | Low | Documented as Phase 2; flag in UI when corpus is incomplete for a brand |
| 10 | Athul out for ~2 weeks late May (visa stamping) | Low | Plan coverage |

### 14.2 Open Questions (carry to next customer touchpoint)

- What happens when an idea is **rejected** at the experimentation-team validation stage? (Meeting 1 + Meeting 2 still ambiguous.)
- Confirmation of value-stream resourcing model for analysts (still TBD inside GAP).
- GCP project provisioning lead time + any architecture-review gate.
- Whether a metric definitions glossary exists, or whether the tool needs to construct one from the corpus.
- Whether we can ingest the ~20% of non-Confluence findings (PDF / PPT / email) at any stage.
- Confirmation that "duplicate test detection" is or isn't a real customer ask (Aditya unsure).

The full open-questions list lives in [Meeting 1/Open_Questions.md](Meeting%201/Open_Questions.md).

---

## 15. Glossary

| Term | Meaning |
|------|---------|
| A/B test | Experiment with a control and one or more challenger variants |
| Agent Builder | Vertex AI managed RAG service |
| Averted loss | $ value of NOT rolling out a losing variant |
| Challenger | The variant being tested against the Control |
| Client-side test | Optimizely overrides the rendered page after load |
| Confluence | Atlassian wiki — canonical source for test write-ups |
| Control | The current production experience |
| Discoverability | Primary project goal — making 1,500 prior tests findable |
| Estimated Annualized Value | Projected $ if a winning variant rolls out at scale |
| Flat | Outcome with no statistically significant impact (most common) |
| Grounding | Vertex AI service that attaches source citations to LLM output |
| HyDE-lite | Per-chunk hypothetical questions to widen semantic match surface |
| Loss | Negative outcome — the variant is not rolled out |
| MDE | Minimum Detectable Effect |
| Model Router | Firestore-driven layer that picks the LLM per task |
| OPV | Order Placement / Conversion Rate KPI |
| Optimizely | Licensed 3rd-party A/B testing platform |
| PDM | Product Decision Maker — internal product / brand stakeholder |
| Prompt filter | Lightweight input/output safety checks |
| RAG | Retrieval-Augmented Generation |
| Server-side test | Variant rendered before page load (engineered into the app) |
| Tactic | Test category — Quality / Time Savings / Urgency / Value |
| Test Plan | Confluence page authored before a test runs |
| Test Results | Confluence page authored after a test ends |
| Value stream | New GAP grouping by site section (PLP / PDP / Bag / Checkout) |
| Vector Search | Vertex AI managed vector index |
| Win | Positive outcome — variant rolled out |

---

*This document supersedes earlier project-overview drafts. The architecture diagram is in [GCP_RAG_Architecture.md](GCP_RAG_Architecture.md). The component-level design is in [Vertex_AI_Search_Variant/Architecture.md](Vertex_AI_Search_Variant/Architecture.md). Meeting-specific notes are in [Meeting 1/](Meeting%201), [Meeting 2/](Meeting%202), [Meeting 3/](Meeting%203), and [Meeting 4/](Meeting%204).*
