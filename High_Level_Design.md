# High-Level Design — GAP GenAI Knowledge Discovery (locked)

> **Variant**: Vertex AI Search (Discovery Engine). All other approaches (custom Vertex pipeline, managed RAG Engine, vectorless RAG) have been retired.
> **Detailed docs**: see [Vertex_AI_Search_Variant/](Vertex_AI_Search_Variant/) — `README.md`, `Architecture.md`, `Multi_Session_Flow.md`.
> **Diagrams**: [GAP_HLD_v2 (2).drawio](GAP_HLD_v2%20(2).drawio) is the **canonical HLD** post the 2026-06-12 GAP Infra Security review (Composer ingest · Agent Engine · AlloyDB · GitHub Actions · OBO). [High_Level_Design.drawio](High_Level_Design.drawio) is the prior published copy, kept until ARB sign-off. [GCP_RAG_Architecture.drawio](GCP_RAG_Architecture.drawio) holds the solution-architecture / data-flow view.
> **Action items from the 2026-06-12 client infra review**: tracked in [Client_Infra_Action_Items.csv](Client_Infra_Action_Items.csv) and mirrored in §6 below (`AI-1`…`AI-10`).

---

## 1. Architecture at a glance

```mermaid
flowchart LR
    classDef user fill:#E3F2FD,stroke:#1565C0,color:#0D47A1
    classDef web  fill:#FFF3E0,stroke:#E65100,color:#BF360C,stroke-width:2px
    classDef back fill:#F3E8FD,stroke:#8430CE,color:#3C1361,stroke-width:3px
    classDef vais fill:#F3E8FD,stroke:#8430CE,color:#3C1361,stroke-width:3px
    classDef job  fill:#E6F4EA,stroke:#137333,color:#0D652D
    classDef data fill:#E8F0FE,stroke:#1A73E8,color:#174EA6
    classDef ext  fill:#E8EAED,stroke:#5F6368,color:#202124

    IDP["Workspace IdP<br/>SSO / OIDC"]:::ext
    U([End User<br/>PDM · Analyst · Exec]):::user

    subgraph WEB["Web App  (Cloud Run)"]
        WS["/sessions sidebar"]:::web
        WC["/chat surface"]:::web
    end

    subgraph BACK["ADK Discovery Agent  (Vertex AI Agent Engine)"]
        BS["/sessions thin pass-through<br/>owner-gate on userPseudoId"]:::back
        BC["/chat single :answer call<br/>format citations · log · feedback"]:::back
    end

    subgraph SE["Vertex AI Search engine"]
        VS["Vector Search Hybrid<br/>parse · chunk · embed (gemini-embedding-2) · index<br/>BM25 + semantic + reranker<br/>:answer (grounded)"]:::vais
        CS["Chat Sessions<br/>engine-scoped · userPseudoId<br/>90-day TTL"]:::vais
        DS[("Datastore<br/>gap-genai-discovery-corpus")]:::data
    end

    subgraph ING["Ingest (weekly delta)"]
        SRC["Confluence<br/>Test & Learn COE"]:::ext
        EXP["Cloud Composer DAG<br/>confluence_weekly_ingest"]:::job
        GCS[("GCS corpus-html<br/>+ images/ prefix")]:::data
    end

    ADB[("AlloyDB Postgres<br/>gap-genai-app-alloydb<br/>experiments · feedback · eval_runs")]:::data
    IAM["IAM + Secret Manager"]:::ext
    LOG["OTel → Cloud Logging / Monitoring / Trace<br/>(GAP standard)"]:::ext
    EVAL["Vertex AI Gen AI Evaluation Service"]:::vais

    U -->|sign-in| IDP
    IDP -->|ID token| WC
    WS <--> BS
    WC -->|POST /chat + OBO token| BC
    BC -->|:answer| VS
    VS -->|auto-append turn| CS
    BS <-->|sessions.list/get/delete| CS

    EXP -.weekly @cron.-> SRC
    SRC -->|GET pages PAT| EXP
    EXP --> GCS
    EXP -->|extract images| GCS
    EXP -->|importDocuments| DS
    EXP -->|write experiments| ADB

    BC -->|Postgres + IAM DB auth (OBO)| ADB
    BC -.OTel logs+traces+metrics.-> LOG
    EVAL -.weekly golden set.-> ADB
    IAM -.-> BACK
    LOG -.-> BACK
```

## 2. Service table

| Service | Role |
|---------|------|
| **Cloud Run — Web App** | `/sessions` sidebar + `/chat` surface. Calls the Agent Engine only. Sign-in via Workspace IdP (OIDC); user identity flows through OBO. |
| **Vertex AI Agent Engine** | Hosts the **ADK Discovery Agent** (registered in Agent Registry per the 2026-06-12 review). `/sessions` (thin pass-through to VAIS, owner-gated on `userPseudoId`) and `/chat` (single VAIS `:answer` call, then format citations + emit OTel telemetry). No app-side LLM. Skills: `generate_answer`, `format_citations`, `record_feedback`, `query_experiment_kpis`, `list_sessions`, `delete_session`. **Replaces Cloud Run for the agent** — Cloud Run agents are not approved by GAP Infra. |
| **Vertex AI Search engine** `gap-genai-discovery-search` | Hybrid retrieval (BM25 + semantic + reranker), grounded synthesis (`:answer` API), filter extraction (`naturalLanguageQueryUnderstandingSpec`), chat-session memory (engine-scoped, `userPseudoId`-keyed, 90-day TTL). Enterprise + LLM add-on tier. |
| **VAIS Datastore** `gap-genai-discovery-corpus` | GCS-unstructured, HTML + image metadata; points at `gs://gap-genai-discovery-corpus-html/pages/` and `gs://gap-genai-discovery-corpus-html/images/`. |
| **Cloud Composer (Airflow)** — `confluence_weekly_ingest` DAG | Weekly delta from Confluence Test & Learn COE. Tasks: `fetch_changed_pages` (read-only SA-PAT) → `extract_text` → `extract_images` → `upload_gcs` → `trigger_vais_reindex` → `write_experiment_rows` (AlloyDB). **Replaces the previous Cloud Run Job + Cloud Scheduler combo** per the 2026-06-12 review. Image extraction is Phase 1 (was P2 — AR-2/3/4). |
| **AlloyDB Postgres** `gap-genai-app-alloydb` | Application/product data: `experiments`, `experiment_clusters`, `feedback`, `golden_evals`, `eval_runs`, `app_config.skill_registry`, `app_config.ingest_state`. Accessed via AlloyDB AuthProxy with **IAM database authentication**, so the OBO user identity flows through to row-level access. **Replaces BigQuery `gap_genai_app`** — BigQuery MCP is not approved (2026-06-12). Telemetry remains in Cloud Observability, **not** in this database. |
| **Vertex AI Evaluation Service** | Weekly golden-set run (~100 Q&A pairs) producing `faithfulness`, `answer_relevance`, `context_precision`, `citation_coverage`, plus pairwise comparisons against the previous week. Refs: <https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview>, <https://cloud.google.com/vertex-ai/generative-ai/docs/models/online-pairwise-evaluation>. Used for regression detection only — never gates production traffic. |
| **Cloud Observability Suite** | Primary telemetry store: Cloud Logging (structured JSON), Cloud Monitoring (SLOs, alerting, dashboards), Cloud Trace (OTel + ADK trace exporter), Cloud Profiler, Error Reporting. **GAP standard OTel pipeline** (confirmed by Joe Brand on 2026-06-12). Log-based metrics for `request_count`, `latency_p95`, `model_id`, **`llm_tokens_in/out` per model** (finance / cost reporting). 30-day default retention; long-tail to Cloud Storage cold bucket if required. |
| **GitHub Actions — DevSecOps Golden Path** | All four CI/CD streams (Web App image, Agent Engine bundle, Composer DAG, AlloyDB schema migrations) run from a single mono-repo. **Workload Identity Federation** between GitHub and GCP (no long-lived SA keys). **Replaces Cloud Build** — Cloud Build is not approved (2026-06-12). |
| **Models** — Vertex AI Model Garden | Stable picks (verified against `ai.google.dev/gemini-api/docs/models`, 2026-06-09): `gemini-3.5-flash` (primary inference), `gemini-2.5-pro` (complex synthesis fallback), `gemini-embedding-2` (multimodal embeddings for Phase-1 image grounding). Submitted for Model Garden policy verification (AI-4). |
| **Cloud IAM + Secret Manager** | Per-service SA (least privilege); **Confluence read-only service-account PAT** in Secret Manager (no employee tokens). New SA: `sa-composer-ingest@<prj>.iam.gserviceaccount.com`. |

## 3. Key design decisions

| Decision | Rationale |
|---|---|
| VAIS owns retrieval + synthesis + sessions | Three managed surfaces vs three custom services. Same single network hop. |
| No app-side LLM call | Removes Model Router, Opus/Gemini fallback service, and prompt-template maintenance. |
| GCS-staged corpus (not Google's Confluence connector) | Decouples query traffic from Confluence outages; full control of ACL tags per page. |
| Backend = ADK skills | Each step is versioned + has a golden-eval slice; swap or A/B without redeploy. |
| `:answer` on v1beta | `naturalLanguageQueryUnderstandingSpec` is only on v1beta. Rewriting is automatic when `session` is set — don't pass `queryRewritingSpec`. |
| Sessions are engine-scoped | Datastore-scoped sessions return 400 on `:answer`. |
| `sessions.list` filtered client-side on `userPseudoId` | Server-side `filter=` is currently ignored by the API. |

## 4. Validation

End-to-end smoke test against the live engine in [tests/multi_session_smoke.ps1](tests/multi_session_smoke.ps1) — verifies multi-user, multi-session, multi-turn anaphora, resume-with-follow-up, cross-user isolation, and ACL gate. Last run: 11/12 turns successful (1 cosmetic em-dash encoding failure), all five architectural validations PASS.


---

## 5. Action items � AI Architect Review (2026-05-25)

> Source: Biswajeet Mishra (AI Architect) review session. Decisions already reflected in this document and in `High_Level_Design.drawio` v2 are marked **DONE**. Open items are tracked here until the next ARB review.

| ID | Action | Owner | Type | Status |
|----|--------|-------|------|--------|
| AR-1 | Replace employee Confluence PAT with a dedicated **read-only service-account PAT**; rotate via Secret Manager. Diagram + docs already updated; provisioning to be completed before pilot. | Ashiq | Decision | OPEN (impl pending) |
| AR-2 | ~~Phase-1 assumption: **images / diagrams are NOT processed**.~~ **Promoted to Phase 1** on 2026-06-12: Composer DAG now includes `extract_images` task; images stored under `gs://…/images/` and indexed via `gemini-embedding-2` (multimodal). | Ashiq, Mradal | Scope change | **DONE-in-P1** |
| AR-3 | ~~Phase-2 plan~~ **Phase-1 (now)**: save images to GCS + retrieve based on user queries via multimodal embeddings. | Ashiq, Mradal | Scope change | **DONE-in-P1** |
| AR-4 | Spike — run a Confluence page with embedded images through VAIS `:answer` and report whether it handles them out-of-the-box. **Result**: handled via `gemini-embedding-2` configured on the datastore; image alt-text + OCR captions surfaced in citations. | Ashiq | Spike | **DONE-in-P1** |
| AR-5 | **Cloud Observability Suite** replaces BigQuery as the logging / tracing / metrics store. BigQuery keeps only product data (`experiments`, `clusters`, `feedback`, `golden_evals`, `eval_runs`, `app_config.*`). | Ashiq / Architect | Decision | **DONE** (HLD v2) |
| AR-6 | Track LLM **token consumption + per-model usage** for finance cost reporting. Implement as log-based metrics + monthly billing export. Backend extracts `usageMetadata.{prompt,candidates}TokenCount` from every Vertex AI / VAIS call and emits OTel attributes `llm_tokens_in`, `llm_tokens_out`, `model_id`, `skill_name`; Cloud Monitoring log-based metrics `gap_genai/llm_tokens_in`, `gap_genai/llm_tokens_out`, `gap_genai/llm_calls`, `gap_genai/llm_cost_usd` feed a finance dashboard + Cloud Billing line-item budget alert on Discovery Engine + Vertex AI, plus a Monitoring alert on output-token rate-of-change. | Ashiq | Decision | **DONE** (HLD v2) |
| AR-7 | Use **VAIS native session APIs** (`sessions.create/list/delete`) directly; no custom backend session store. | Ashiq | Decision | **DONE** (variant locked) |
| AR-8 | Investigate **ADK agent API endpoint customisation** � confirm whether any backend modifications are needed for the integration. | Backend lead | Spike | OPEN |
| AR-9 | Dashboard frontend = **React** (Streamlit dropped from scope). | Frontend lead | Decision | **DONE** (Frontend_Developer_Guide) |
| AR-10 | Reflect **IAM roles / CSRF tokens / service accounts** on the diagrams so ARB reviewers can answer security questions without follow-up. | Ashiq, Nilim | Documentation | **DONE** (HLD v2 + D2 / D5) |
| AR-11 | Upload HLD + LLDs (`Vertex_AI_Search_Variant/` + `arch-meeting/D2`�`D5`) to the **Confluence ARB review page**. | Ashiq, Nilim | Documentation | OPEN |
| AR-12 | Clarify **ARB-reviewer document-set requirements** (which doc, which audience, which depth) before LLD authoring begins. | Kaushik / Architect | Open question | OPEN |

### Diagram changes captured in `High_Level_Design.drawio` v2
- **Observability Suite** tile replaces the old "Cloud Logging + Monitoring" tile; OTel arrows fan in from every Cloud Run service and Job (AR-5, AR-6).
- BigQuery cylinder no longer lists `request_logs` / `skill_invocations`; now shows product data only (AR-5).
- New **Google Workspace IdP** ellipse inserted between Users and the Web App for **SSO sign-in** (OIDC). Users authenticate with SSO, then access the Web App over HTTPS (AR-10). IAP-on-Cloud-Run / CSRF details intentionally kept out of the conceptual diagram — they live in the physical / security views (D2, D5).
- Confluence tile labelled **`Read-only service-account PAT (no employee tokens)`**; exporter tile now shows `auth: SA PAT from Secret Manager` (AR-1).
- **Secret Manager**, **Cloud IAM**, and **Vertex AI Evaluation** tiles (previously orphans in the Shared Platform lane) are now wired to their consumers with labelled edges.
- **LLM token-tracking chain surfaced on the diagram** (AR-6): the `Backend → Vertex AI Model Garden` edge is labelled `Gemini inference / ← usageMetadata / {prompt,candidates}TokenCount` and the `Backend → VAIS` edge is labelled `top-10 retrieval / ← :answer.metadata / (token counters)`. The Observability tile now lists the four log-based metric names (`gap_genai/llm_tokens_in`, `…_out`, `…_calls`, `…_cost_usd`), the backend OTel edge label calls out `llm_tokens_in / llm_tokens_out / model_id / skill_name`, and a new **Cloud Billing — budget alerts** tile is wired from Observability via a `log-based metric → budget + alert policy` dashed edge.

> The previous `High_Level_Design.drawio` is preserved as `High_Level_Design.legacy.drawio` until ARB sign-off, then it will be deleted.

---

## 6. Action items — GAP Infra Security review (2026-06-12)

> Source: client infra review with Joe Brand & Abhi Baheti. Master tracker is [Client_Infra_Action_Items.csv](Client_Infra_Action_Items.csv) — the table below is the same data. Diagram changes already reflected in [GAP_HLD_v2 (2).drawio](GAP_HLD_v2%20(2).drawio).

| ID | Lane | Item | Decision / Action | Owner | Status |
|----|------|------|-------------------|-------|--------|
| AI-1 | Intake | Composer / Dataproc vs Cloud Run | **Cloud Run Job + Cloud Scheduler replaced by Cloud Composer (Airflow DAG)**. No Dataproc — corpus is ~1.3k pages and the workload is HTTP fetch + render, not Spark. The same DAG handles new Phase-1 image extraction. | Mradal Tiwari | IN PROGRESS |
| AI-2 | Intake | Confluence service account | SA: **`sa-composer-ingest@<prj>.iam.gserviceaccount.com`** with read-only PAT in Secret Manager (`projects/<prj>/secrets/confluence-readonly-pat`); GCP roles: `secretmanager.secretAccessor`, `storage.objectAdmin` (corpus-html), `composer.worker`. GCP-native SA only — no AD SA. | Nilim Borah | OPEN (IAM team to provision) |
| AI-3 | Query | Agent Engine for ADK | **Cloud Run dropped for the agent**. ADK Discovery Agent moves to **Vertex AI Agent Engine** + Agent Registry. Web App stays on Cloud Run. Substory required for Agent Engine API enablement. | Ashiq KS | IN PROGRESS |
| AI-4 | Query | Model Garden — model list | Submitted: `gemini-3.5-flash` (primary), `gemini-2.5-pro` (complex synthesis), `gemini-embedding-2` (multimodal embeddings for P1 image grounding). Verified stable per `ai.google.dev/gemini-api/docs/models` (2026-06-09). | Ashiq KS | OPEN (awaiting Model Garden policy check) |
| AI-5 | Query | BigQuery MCP / data access | **BigQuery MCP dropped**. Replacing the entire `gap_genai_app` warehouse with **AlloyDB Postgres** (`gap-genai-app-alloydb`, already PSEC-approved). Agent connects via AlloyDB AuthProxy with **IAM database authentication** — OBO identity flows through to row-level access. Impact: ~1 week schema/connector migration; ADK Postgres toolset replaces planned BQ toolset. | Ashiq KS | IN PROGRESS |
| AI-6 | Query | User group / roles | Single role for P1 ("Knowledge Discovery User"). Workspace group **`gap-genai-knowledge-discovery-users@gap.com`** (final DN to be confirmed by IAM team). Future analyst role parked for P2. | Nilim Borah | OPEN (IAM team to provision group) |
| AI-7 | Query | On-Behalf-Of auth | End-to-end OBO chain: Workspace IdP → Web App (validates ID token) → token exchange → Agent Engine (inherits user identity) → AlloyDB (IAM DB auth) + VAIS (`userPseudoId`). No SA impersonation for user requests. | Ashiq KS | IN PROGRESS |
| AI-8 | CI/CD | Cloud Build replacement | **Cloud Build dropped**. CI/CD via **GitHub Actions / DevSecOps Golden Path** — single mono-repo, Workload Identity Federation, no long-lived SA keys. Repo: TBD (`github.com/gap-inc/genai-knowledge-discovery` placeholder). | Athul Babu | OPEN (awaiting DevSecOps doc reference from Joe) |
| AI-9 | Observe | GAP standard OTel | **Confirmed** by Joe on the call. OTel SDK → Cloud Logging + Cloud Monitoring + Cloud Trace from every Cloud Run service and the Composer DAG. | Ashiq KS | DONE |
| AI-10 | Observe | Vertex AI Eval detail | Vertex AI Gen AI Evaluation Service runs offline weekly against a curated golden set (~100 Q&A); metrics: faithfulness, answer-relevance, context-precision, citation-coverage, plus pairwise comparisons. Results land in AlloyDB `eval_runs`. **Never gates production traffic.** Refs: <https://cloud.google.com/vertex-ai/generative-ai/docs/models/evaluation-overview>, <https://cloud.google.com/vertex-ai/generative-ai/docs/models/online-pairwise-evaluation>. | Ashiq KS | IN PROGRESS |

### Diagram changes captured in `GAP_HLD_v2 (2).drawio`
- **Ingest lane** — `Cloud Run Job (Confluence Exporter) + Cloud Scheduler` consolidated into a single **Cloud Composer DAG** tile (`confluence_weekly_ingest`); Composer's own Airflow scheduler replaces Cloud Scheduler. Edge from Confluence → Composer flipped to Composer → Confluence (Composer is the caller; AR review feedback). Edge label: `GET pages (SA-PAT) via Secret Manager`. Image extraction added to the DAG description (AR-2/3/4 → P1).
- **Query lane** — Backend tile re-coloured to Vertex-AI purple, retitled **"ADK Discovery Agent (Vertex AI Agent Engine)"**, icon swapped from `cloud_run` to `cloud_machine_learning`. Model Garden tile updated with the AI-4 model list. **MCP Toolbox tile annotated as REMOVED** (kept as a small dashed marker for traceability). **BigQuery cylinder replaced by AlloyDB cylinder** (`gap-genai-app-alloydb`) — colour swapped to GCP-blue, schema list updated, edge label `Postgres + IAM DB auth (OBO)`.
- **Auth chain** — `qa1` edge label upgraded to `(1) HTTPS + SSO/OIDC — Workspace IdP`. New dashed `qa7` edge Web App → Agent Engine labelled `OBO ID token (user identity)`.
- **CI/CD lane** — `Cloud Build` tile replaced by **`GitHub Actions — DevSecOps Golden Path`** with annotation `Cloud Build NOT approved (2026-06-12)`. Deployment targets: Web App (Cloud Run), ADK Agent (Agent Engine), Ingest DAG (Composer), DB Schema Migrate (AlloyDB Liquibase). MCP Toolbox deployment target removed; ci5 edge dashed (representative DB-migrate).
- **Shared Platform** — `Cloud Logging + Monitoring` retitled `OTel → Cloud Logging + Monitoring + Trace — GAP standard observability pipeline`. Vertex Eval tile expanded with reference URL.