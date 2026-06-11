# Backend Developer Guide - GAP GenAI Knowledge Discovery (ADK Discovery Agent)

## 1. Project context

The Backend is a Google Agent Development Kit (ADK) root agent named `DiscoveryAgent` running on Cloud Run. It exposes a small REST surface to the Web App and delegates all retrieval + grounded synthesis to **Vertex AI Search (Discovery Engine)** via the `:answer` API. The Backend never calls an LLM itself - Vertex AI Search is the single managed plane that owns retrieval, ranking, generation, and chat-session memory.

```
Web App (Cloud Run, public)
  -> Backend "DiscoveryAgent" (Cloud Run, private, run.invoker)
       -> Vertex AI Search engine "gap-genai-discovery-search" (:answer, sessions API)
       -> BigQuery dataset "gap_genai_app" (logs, feedback, evals)
       -> Secret Manager (Confluence SA-PAT - jobs only)
```

Two Cloud Run **Jobs** sit alongside the service:
- `gap-genai-discovery-exporter` - weekly Confluence delta -> GCS HTML.
- `gap-genai-discovery-reindex` - weekly `documents.import` into the VAIS datastore.

---

## 2. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | Required by the ADK Python SDK |
| Web framework | FastAPI | ASGI; async-friendly for VAIS calls |
| Server | Uvicorn (workers via Gunicorn in prod) | Cloud Run will scale instances; keep workers per instance low |
| Agent runtime | **Google ADK** (`google-adk`) | Root agent class `DiscoveryAgent`; skills are typed ADK tools |
| VAIS client | `google-cloud-discoveryengine` (>= v0.13, **v1beta** surface) | v1beta is required for `naturalLanguageQueryUnderstandingSpec` |
| Data | `google-cloud-bigquery`, `google-cloud-storage` | Service-account ADC |
| Secrets | `google-cloud-secret-manager` | Confluence SA-PAT only (read-only, no employee tokens) |
| Auth verification | `google-auth` | Verify ID tokens forwarded from the Web App / IAP header |
| Observability | `opentelemetry-sdk` + `opentelemetry-exporter-gcp-trace` + `google-cloud-logging` | Structured JSON logs + Cloud Trace |
| Testing | `pytest`, `pytest-asyncio`, `httpx`, `respx` | Mock VAIS at the HTTP layer |
| Lint / format | `ruff`, `black`, `mypy --strict` | Pre-commit |

> Stack is **RECOMMENDED**, not locked. Architecture.md only mandates "ADK agent on Cloud Run" and "Vertex AI Search v1beta `:answer`". Anything else above is a recommendation.

---

## 3. REST endpoints exposed

All six endpoints are mounted under `/api/genai`. All accept JSON, return JSON, and require an authenticated caller (Web App service account via `run.invoker`, propagating the end-user identity in headers).

### Common request headers

| Header | Source | Purpose |
|---|---|---|
| `Authorization: Bearer <id_token>` | Cloud Run automatic | Identifies the **calling service** (Web App SA) - enforced by `run.invoker` IAM |
| `X-User-Id` | Web App (OAuth `sub`) | The end-user. Used as VAIS `userPseudoId` and as the **OTel log/trace attribute `user_id`** in the Cloud Observability Suite (AR-5). |
| `X-Session-Id` | Web App | Current chat session (last segment of `engines/{e}/sessions/{id}`). Optional on `POST /sessions` |
| `X-Request-Id` | Web App (uuid v4) | Echoed back as an **OTel log entry / Cloud Trace span attribute** (`request_id`). |

### 3.1 `POST /api/genai/chat`

Submit one turn. The Backend calls `generate_answer` -> VAIS `:answer` -> `format_citations` -> returns the formatted response. Always non-streaming today (streaming is the Phase 2 R2 mitigation in README.md).

Request body:
```json
{
  "text": "What checkout-related tests have we run?",
  "session_id": "18411582449178203485"
}
```

Response body:
```json
{
  "answer": "The strongest evidence comes from ... [1] [2]",
  "citations": [
    { "sources": [ { "referenceId": "chunk_id" } ] }
  ],
  "references": [
    {
      "chunkInfo": {
        "documentMetadata": {
          "structData": {
            "confluence_url": "https://confluence.gap.com/...",
            "page_id": "TLCOE-2010225",
            "title": "Old Navy Sticky Add-to-Bag"
          }
        }
      }
    }
  ],
  "dashboard_payload": null
}
```

**Optional `dashboard_payload`** (present when the agent fires `query_experiment_kpis`; see [`Architecture.md`](Architecture.md) §7):

```json
"dashboard_payload": {
  "tiles": {
    "total_run": 142, "completed": 136, "successful": 78, "active": 6,
    "avg_conversion_lift": 3.8, "total_revenue_impact": 9400000,
    "avg_aov_lift": 4.2, "upt_lift": 5.1, "total_category_sales_impact": 4600000
  },
  "card_clusters": [
    { "cluster_id": "DEP-001", "name": "Denim Entrance Placement",
      "category": "Product Placement", "stores": 45, "region": "North America",
      "duration": "2025-08-01..2025-11-15",
      "conversion_lift": 3.6, "revenue_lift": 2100000,
      "aov_lift": 4.0, "confidence": 96, "success": true }
  ]
}
```

The field is `null` (or omitted) on pure narrative turns. The frontend renders tiles + cards only when it is present.

Owner-gate: before calling VAIS, the Backend fetches the session resource and asserts `session.userPseudoId == X-User-Id`. Mismatch -> `403 Forbidden`.

### 3.2 `GET /api/genai/sessions`

Lists the caller's chats.

Implementation: VAIS `sessions.list` with `filter=userPseudoId="<user_id>"` AND a **client-side re-filter** (the server-side `filter=` is currently ignored by VAIS - see README.md). `preview_snippet` is derived from the VAIS session resource (`turns[-1].query.text` after `sessions.get?includeAnswerDetails=true`) — no BigQuery join required.

Response:
```json
{
  "sessions": [
    {
      "session_id": "18411582449178203485",
      "title": "Old Navy sticky add-to-bag wins",
      "last_active": "2026-05-14T09:18:41Z",
      "turn_count": 6,
      "preview_snippet": "The strongest evidence comes from..."
    }
  ]
}
```

### 3.3 `POST /api/genai/sessions`

Creates a new chat session.

```
POST engines/{engine}/sessions
body { "userPseudoId": "<X-User-Id>" }
-> returns { "name": "engines/.../sessions/{id}" }
```

Response: `{ "session_id": "...", "title": null }`.

### 3.4 `GET /api/genai/sessions/{id}/turns`

Fetch the full ordered transcript for a session. Backend calls `sessions.get?includeAnswerDetails=true` after the owner-gate.

Response:
```json
{
  "turns": [
    { "role": "user", "text": "..." },
    { "role": "assistant", "text": "... [1] [2]", "citations": [...], "references": [...] }
  ]
}
```

### 3.5 `DELETE /api/genai/sessions/{id}`

Owner-gate, then VAIS `sessions.delete`. Returns `204 No Content`. Also emits an **OTel log entry** tagged `skill_name = "delete_session"` to the Cloud Observability Suite.

### 3.6 `POST /api/genai/feedback`

Records a thumbs / freetext comment for a specific assistant turn.

Request:
```json
{
  "session_id": "184...",
  "turn_id": "q1",
  "rating": 1,
  "comment": "useful, but missing the FY24 test"
}
```

Backend writes a row into `gap_genai_app.feedback` and returns `204 No Content`.

### Error response convention

| Status | When | Body |
|---|---|---|
| `400 Bad Request` | Prompt-filter trip (length cap, injection pattern, off-topic) | `{"error": "prompt_filter", "reason": "..."}` |
| `401 Unauthorized` | Missing / invalid `X-User-Id` after gateway | `{"error": "unauthorized"}` |
| `403 Forbidden` | Owner-gate mismatch on a session | `{"error": "owner_mismatch"}` |
| `404 Not Found` | Session does not exist or was deleted | `{"error": "session_not_found"}` |
| `429 Too Many Requests` | VAIS rate-limit (`http_429`) | `{"error": "rate_limited", "retry_after_s": 5}` |
| `5xx` | VAIS error or internal | `{"error": "upstream", "request_id": "<X-Request-Id>"}` |

All errors are emitted as an **OTel log entry** with `status="error"` and the VAIS error body in `jsonPayload.error_payload` — routed to Error Reporting in the Cloud Observability Suite.

---

## 4. ADK skills catalog

Each skill is a typed Python function decorated as an ADK tool. Skills can be enabled / disabled / repointed without redeploy by editing the row in `gap_genai_app.app_config` (hot-reloaded every 60s).

| Skill | Input | Output | Writes | Golden-eval slice |
|---|---|---|---|---|
| `generate_answer` | `query, session_name, user_pseudo_id` | VAIS `:answer` response object | - | `e2e` (answer quality vs golden set) |
| `query_experiment_kpis` | `{brand?, value_stream?, region?, outcome?, time_range?='6M'}` | `{ tiles, card_clusters }` (see [`Architecture.md`](Architecture.md) §7.3) | - | `e2e_dashboard` (tile + card-cluster accuracy vs golden filter sets) |
| `format_citations` | VAIS `:answer` response | `{answer, citations[], references[]}` where each `reference` carries `documentMetadata.structData.learning_snippet` (1-2 line per-result summary, see Meeting 4 §7) lifted from the `<meta name="learning_snippet">` tag during ingest | - | `skill` (deterministic post-process) |
| `record_feedback` | `session_id, turn_id, rating, comment?` | `204` | `gap_genai_app.feedback` | - |
| `emit_turn_telemetry` | full turn context | `204` | **OTel log + Trace span \u2192 Cloud Observability Suite** (skill_name, latency_ms, llm_tokens_in/out, model_id, VAIS-extracted filter; includes `skill_name='query_experiment_kpis'` when the dashboard skill fired) | - |
| `list_sessions` | `user_pseudo_id` | `[{session_id, title, last_active, turn_count, preview_snippet}]` | - | `trajectory` |
| `delete_session` | `session_id, user_pseudo_id` | `204` | OTel log entry tagged `skill_name="delete_session"` | - |

**Skill wiring inside the ADK `DiscoveryAgent`**:
- `generate_answer` -> ADK **Built-in tool** (direct call to Discovery Engine `:answer`).
- `query_experiment_kpis` -> **MCP client** pointing at the Google-managed **BigQuery MCP server** (`https://bigquery.googleapis.com/mcp`). The agent issues the `execute_sql_readonly` MCP tool against the authorized view `gap_genai_app.v_experiment_kpis` (which joins `experiments` + `experiment_clusters`). No self-hosted Cloud Run service and no custom `tools.yaml` to maintain; auth is OAuth2 via `sa-agent` (`roles/mcp.toolUser`). The Agent picks this skill when `gemini-2.5-flash` classifies the turn intent as list/show/how-many/which.
- For mixed intent turns (list + explain), both skills run; the merged narrative is summarised by `gemini-2.5-pro`. Model bindings are configured per-skill on the `LlmAgent`, not via a custom router class.

File layout convention:
```
backend/
  app/
    main.py                    # FastAPI app, route handlers, health checks
    agent.py                   # DiscoveryAgent root agent + skill registry
    skills/
      generate_answer.py
      format_citations.py
      record_feedback.py
      log_turn.py
      list_sessions.py
      delete_session.py
    clients/
      vais.py                  # discoveryengine v1beta wrapper
      bq.py                    # BigQuery writer
      secrets.py               # Secret Manager accessor
    config/
      loader.py                # 60s app_config hot-reload from BQ
    auth/
      ownership.py             # owner-gate helper
    obs/
      tracing.py               # OTel init
      logging.py               # structured JSON logger
  jobs/
    exporter/                  # gap-genai-discovery-exporter
    reindex/                   # gap-genai-discovery-reindex
  tests/
  pyproject.toml
```

---

## 5. Vertex AI Search integration

### 5.1 `:answer` - the main per-turn call

```http
POST https://discoveryengine.googleapis.com/v1beta/projects/<project>/locations/global/
     collections/default_collection/engines/gap-genai-discovery-search/
     servingConfigs/default_search:answer
Content-Type: application/json
Authorization: Bearer <SA token>

{
  "query":         { "text": "<user query>" },
  "session":       "projects/<p>/locations/global/collections/default_collection/engines/gap-genai-discovery-search/sessions/<session_id>",
  "userPseudoId":  "<user_id>",
  "answerGenerationSpec": {
    "modelSpec":       { "modelVersion": "stable" },
    "includeCitations": true
  },
  "queryUnderstandingSpec": {
    "queryClassificationSpec": {
      "types": ["ADVERSARIAL_QUERY", "NON_ANSWER_SEEKING_QUERY"]
    }
  },
  "searchSpec": {
    "searchParams": {
      "naturalLanguageQueryUnderstandingSpec": {
        "filterExtractionCondition": "ENABLED"
      }
    }
  }
}
```

Response shape:
```json
{
  "answer": {
    "answerText": "...",
    "citations": [ { "sources": [ { "referenceId": "..." } ] } ],
    "references": [ { "chunkInfo": { "documentMetadata": { "structData": { "confluence_url": "..." } } } } ],
    "queryId": "q1"
  },
  "sessionInfo": { "...": "..." },
  "queryUnderstandingInfo": { "structuredExtractedFilter": { "...": "..." } }
}
```

### 5.2 Sessions API

| Op | HTTP |
|---|---|
| Create | `POST engines/{e}/sessions  body { "userPseudoId": "<user_id>" }` |
| List | `GET engines/{e}/sessions?filter=userPseudoId%3D%22<user_id>%22&orderBy=updateTime%20desc&pageSize=50` (v1 OK) |
| Get | `GET engines/{e}/sessions/{id}?includeAnswerDetails=true` |
| Delete | `DELETE engines/{e}/sessions/{id}` |

### 5.3 Four known VAIS quirks (from README.md)

1. **Server-side `filter=` on `sessions.list` is ignored.** Always re-filter client-side by `userPseudoId`. Tests in `multi_session_smoke.ps1` Phase 3 catch regressions.
2. **`queryRewritingSpec` is not a field.** Rewriting is automatic when `session` is set on `:answer`. Do not include the key - the API returns 400.
3. **`naturalLanguageQueryUnderstandingSpec` is only available on `v1beta`.** Stay on the v1beta endpoint for `:answer` even if v1 looks tempting.
4. **Sessions must be engine-scoped, not datastore-scoped.** Datastore-scoped session resources return 400 on `:answer`.

---

## 6. Client-side userPseudoId filter

Server-side filter is unreliable. Always re-filter:

```python
def list_sessions(client, engine: str, user_pseudo_id: str, page_size: int = 50):
    raw = client.list_sessions(
        parent=engine,
        filter=f'userPseudoId="{user_pseudo_id}"',  # belt
        order_by="updateTime desc",
        page_size=page_size,
    )
    # ...and braces: re-filter client-side because server-side filter is ignored
    return [s for s in raw if s.user_pseudo_id == user_pseudo_id]
```

The same pattern applies to `sessions.get` results in `/turns` - reject if the returned `userPseudoId` does not match the caller (403).

---

## 7. BigQuery schema

Dataset: `gap_genai_app` (region `us-central1`, partition expiration 90 days on write-heavy tables).

| Table | Partition | Cluster | Purpose |
|---|---|---|---|
| `experiments` | `DATE(start_date)` | `category, region` | Test-and-Learn experiment metadata + KPI rollups (powers the dashboard) |
| `experiment_clusters` | none | `category` | Grouping / theme overlay for experiments |
| `feedback` | `DATE(ts)` (no exp) | `session_id` | Thumbs + freetext, joined to `session_id, turn_id` |
| `golden_evals` | none | `eval_set_id` | Golden queries + expected answers + expected citations, `version + is_current` |
| `eval_runs` | `DATE(run_ts)` | `eval_set_id, status` | One row per offline eval run; metrics rolled up |
| `app_config` | none | `config_key` | JSON config rows hot-reloaded every 60s by the agent; `is_current` flag |

> **Operational telemetry** (`request_logs`-equivalent: latency, tokens, route, request_id, status, error_payload) lives in the **Cloud Observability Suite** as structured OTel log entries + Trace span attributes, **not** in BigQuery (AR-5, 2026-05-25 architect review).

Minimal OTel structured-log shape emitted by every turn (Cloud Logging `jsonPayload`):
```jsonc
{
  "ts": "2026-05-25T18:11:02Z",
  "request_id": "...",
  "user_id": "...",
  "session_id": "...",
  "route": "/api/genai/chat",
  "model_id": "vais://answer",
  "skill_name": "generate_answer",
  "latency_ms": 842,
  "llm_tokens_in": 1240,
  "llm_tokens_out": 318,
  "citation_count": 4,
  "status": "ok",
  "error_payload": null
}
```
Log-based metrics on these fields drive Cloud Monitoring dashboards + alerts (AR-5/AR-6). The token fields map to the Gemini Python SDK as `response.usage_metadata.prompt_token_count` → `llm_tokens_in` and `response.usage_metadata.candidates_token_count` → `llm_tokens_out`; for VAIS the equivalent counters arrive in `:answer` response under `metadata`. The four published metric names are `gap_genai/llm_tokens_in`, `gap_genai/llm_tokens_out`, `gap_genai/llm_calls`, `gap_genai/llm_cost_usd`; a Cloud Billing line-item budget (Discovery Engine + Vertex AI) plus a Monitoring alert policy on output-token rate-of-change close the cost-guard loop.

> **Streaming note (Phase 2)**: when Gemini is invoked with `stream=True`, `usage_metadata` is only populated on the **final** chunk. The backend must aggregate the stream and emit the OTel log entry on stream-close (in the same span) to avoid double-counting or zero-token rows. Per-chunk emission is explicitly **not** supported.

See [`GCP_Services_Required.md`](GCP_Services_Required.md) and [`Architecture.md`](Architecture.md) §6 for the full BigQuery dataset list and the network / ports layout.

---

## 8. Secret Manager

| Secret | Accessor (SA) | Used by |
|---|---|---|
| `confluence-pat` | `sa-ingest@<project>.iam.gserviceaccount.com` | Exporter job only |

The Backend service does **not** need any third-party LLM keys - all generation goes through Vertex AI Search.

---

## 9. Service accounts and IAM

### `sa-orch@<project>.iam.gserviceaccount.com` (Backend service)

| Role | Resource | Why |
|---|---|---|
| `roles/aiplatform.user` | project | Optional - only if calling Vertex AI Evaluation directly |
| `roles/discoveryengine.viewer` | project | Read engine + datastore metadata |
| `roles/discoveryengine.editor` | engine | Required for `:answer` and `sessions.*` write ops |
| `roles/bigquery.dataEditor` | `gap_genai_app` | Insert into feedback / eval_runs |
| `roles/bigquery.dataViewer` | `gap_genai_corpus` | Read-only - optional, only if backend reads corpus metadata |
| `roles/bigquery.jobUser` | project | Run insert / query jobs |
| `roles/secretmanager.secretAccessor` | (none) | Backend does not need secrets - jobs SA does |
| `roles/logging.logWriter` | project | Structured logs |
| `roles/cloudtrace.agent` | project | OTel spans |

### Caller bindings

| Caller | Binding |
|---|---|
| Web App SA `sa-web@` | `roles/run.invoker` on the Backend Cloud Run service |
| `sa-orch@` | `roles/run.invoker` on the Reindex job (manual re-trigger) |

### Jobs SAs

| Job | SA | Extra roles |
|---|---|---|
| Exporter | `sa-ingest@` | `roles/storage.objectAdmin` on `gap-genai-discovery-corpus-html`, `roles/secretmanager.secretAccessor` on `confluence-pat`, `roles/bigquery.dataEditor` on `gap_genai_app.ingest_state` |
| Reindex | `sa-reindex@` | `roles/discoveryengine.editor` on the engine, `roles/storage.objectViewer` on the corpus bucket |

---

## 10. Configuration

### Environment variables (Cloud Run service)

| Name | Example | Notes |
|---|---|---|
| `PROJECT_ID` | `gap-genai-discovery` | GCP project |
| `LOCATION` | `global` | Discovery Engine location |
| `ENGINE_ID` | `gap-genai-discovery-search` | VAIS engine resource id |
| `DATASTORE_ID` | `gap-genai-discovery-corpus` | Unstructured GCS datastore |
| `BUCKET_NAME` | `gap-genai-discovery-corpus-html` | HTML corpus bucket |
| `BQ_DATASET` | `gap_genai_app` | Operational data |
| `BQ_CORPUS_DATASET` | `gap_genai_corpus` | Optional corpus metadata |
| `LOG_LEVEL` | `INFO` | `DEBUG` only for local dev |
| `OTEL_EXPORTER` | `cloudtrace` | Set to `none` locally |
| `APP_CONFIG_POLL_S` | `60` | Hot-reload cadence |
| `REQUEST_TIMEOUT_S` | `60` | Upper bound per VAIS call |

### Hot-reloaded `app_config` row

```json
{
  "config_key": "agent_config",
  "version": 7,
  "is_current": true,
  "payload": {
    "skills_enabled": ["generate_answer", "format_citations", "record_feedback", "log_turn", "list_sessions", "delete_session"],
    "answer_generation_model": "stable",
    "include_citations": true,
    "filter_extraction": "ENABLED",
    "max_prompt_chars": 4000,
    "prompt_filter": {
      "block_patterns": ["ignore previous", "system prompt"],
      "topic_allow_list": ["test-and-learn", "experiment", "ab-test"]
    }
  }
}
```

The loader polls every `APP_CONFIG_POLL_S` seconds with `WHERE config_key='agent_config' AND is_current=TRUE` and atomically swaps the in-process config.

---

## 11. Cloud Run sizing

| Setting | Value |
|---|---|
| CPU | 2 vCPU |
| Memory | 2 GiB |
| Concurrency | 80 |
| Min instances | 0 |
| Max instances | 10 |
| Request timeout | 300 s (VAIS `:answer` is upper-bounded at 60 s, but allow headroom) |
| CPU always allocated | **Yes** (so the 60s `app_config` poll keeps running) |
| Region | `us-central1` |
| Ingress | Internal (only Web App SA via `run.invoker`) |

---

## 12. Background jobs

### 12.1 `gap-genai-discovery-exporter` (Mon 02:00 PT)

Cloud Run Job. Pulls weekly delta from Confluence.

```
- read gap_genai_app.ingest_state -> last_sync_at
- Confluence REST: GET pages where version.when > last_sync_at
- for each page:
    - render storage-format -> sanitised HTML5
    - inject per-field <meta> tags + JSON-LD
    - sha256(html) -> skip if unchanged
    - write gs://gap-genai-discovery-corpus-html/pages/<space>/<page_id>.html
    - append row to metadata.jsonl
    - upsert ingest_state(page_id, last_updated, last_sync_at=now, html_uri, sha256)
- reconcile deletes: pages in ingest_state not in Confluence -> tombstone html file
- emit ingest_run row
```

Sizing: 4 vCPU / 8 GiB, 30 min timeout, max retries 1.

### 12.2 `gap-genai-discovery-reindex` (Mon 03:00 PT)

Cloud Run Job. Triggers VAIS `documents.import`.

```
- Discovery Engine documents.import (incremental on GCS prefix + metadata.jsonl)
- poll import operation -> success / partial / failed
- emit reindex_run row (operation_id, docs_imported, docs_failed, duration)
```

Sizing: 2 vCPU / 4 GiB, 60 min timeout (the import operation can take 20-40 min).

Both jobs are triggered by **Cloud Scheduler** (`gap-genai-cron-weekly`) hitting the Cloud Run Job execute endpoint with an OIDC token.

---

## 13. Observability

### Structured logs (Cloud Logging)

Every request emits a single JSON log line at INFO:
```json
{
  "feature":      "genai",
  "request_id":   "f0c7...",
  "user_id":      "u_8f23...",
  "session_id":   "1841...",
  "route":        "POST /api/genai/chat",
  "skill":        "generate_answer",
  "status":       "ok",
  "latency_ms":   2841,
  "vais_query_id":"q1",
  "citation_count": 4
}
```

These OTel log entries land directly in the **Cloud Observability Suite** (Cloud Logging structured JSON). Log-based metrics + Cloud Monitoring dashboards consume them in-place — no Pub/Sub fan-out, no BigQuery sink (AR-5).

### OpenTelemetry

- Initialise OTel at process start (`obs/tracing.py`).
- Each FastAPI route is a parent span.
- Each skill call is a child span with attributes: `skill.name`, `vais.endpoint`, `vais.session_id`, `vais.query_id`.
- Exporter: Cloud Trace.

### Key metrics / SLOs

| Metric | Target |
|---|---|
| VAIS `:answer` p95 | < 8 s (R2: streaming added if breached - see README.md) |
| Backend p95 end-to-end | < 9 s |
| Citation rate | >= 95 % of answers carry at least one citation |
| Ingest freshness | `max(now - last_sync_at)` < 8 days |
| Owner-gate denials | alert if > 0 / hour (potential leakage attempt) |

---

## 14. Error and fallback conventions

- **Input prompt filter** runs before `generate_answer`: length cap (`max_prompt_chars`), injection patterns (block list), topic allow-list. Trip -> `400 prompt_filter`.
- **Output prompt filter** runs on the VAIS response: citation requirement (>= 1), hallucination heuristic (citation references must resolve to a known `page_id`), length cap. Trip -> rewrite to a safe-fail message + emit OTel log entry with `status='output_filter'`.
- **VAIS retries:**
  - `http_429` -> exponential backoff, 3 attempts, then 429 to caller with `retry_after_s`.
  - `http_5xx` -> 1 retry, then 502 to caller.
  - `timeout > 60s` -> abort, 504 to caller.
- **Session TTL:** VAIS auto-expires sessions at 90 days. After that, the next turn on a stale `session_id` creates a fresh session with the same id discarded - the Backend transparently treats this as a new chat.

---

## 15. Testing

### Local unit tests

```
pytest                                # all
pytest tests/skills/                  # ADK skill unit tests
pytest -k vais and not integration    # VAIS wrapper, mocked with respx
```

### Multi-session smoke (production-like)

[tests/multi_session_smoke.ps1](../tests/multi_session_smoke.ps1) hits the live VAIS engine directly (no app code) and is the contract test the Backend must match.

Phases:
| Phase | What it asserts |
|---|---|
| 1 - Create 4 sessions (2 users x 2 sessions) | Engine accepts engine-scoped session create with `userPseudoId` |
| 2 - 3 turns x 4 sessions = 12 `:answer` calls | Conversation history is preserved, citations returned, latencies recorded |
| 3 - `sessions.list` for each user | Client-side filter is required (server-side ignored), no cross-user leakage |
| 4 - Resume one session with a 4th anaphoric turn | Multi-turn memory works after a fresh session.get |
| 5 - Delete sessions | Owner-gate enforced; cross-user delete is rejected |

When adding new tests, mirror the Phase pattern (`Phase X - <assertion>`) and reuse the `Invoke-Vais` helper.

---

## 16. Local dev / build / deploy

### Local dev

```powershell
# one-time
uv venv
uv pip install -e ".[dev]"
gcloud auth application-default login

# run
$env:PROJECT_ID = "gap-genai-discovery"
$env:ENGINE_ID = "gap-genai-discovery-search"
$env:OTEL_EXPORTER = "none"
uvicorn app.main:app --reload --port 8080
```

### Container build

Cloud Build trigger on push to `main`:
```
gcr.io build steps:
  1. uv pip install -r requirements.lock
  2. pytest -q
  3. docker build -t us-central1-docker.pkg.dev/<project>/gap-backend/api:$SHORT_SHA .
  4. docker push
  5. gcloud run deploy gap-genai-discovery-backend
        --image=us-central1-docker.pkg.dev/<project>/gap-backend/api:$SHORT_SHA
        --region=us-central1
        --no-allow-unauthenticated
        --service-account=sa-orch@<project>.iam.gserviceaccount.com
```

### CD

Cloud Build updates the Cloud Run revision; traffic is shifted 100% on green. The two jobs (`gap-genai-discovery-exporter`, `gap-genai-discovery-reindex`) are built and deployed by separate Cloud Build files in `jobs/exporter/` and `jobs/reindex/`.

### Smoke checklist before merging to `main`
1. `pytest -q` is green locally.
2. `ruff check . && mypy --strict app/` are clean.
3. `tests/multi_session_smoke.ps1` passes against a dev project.
4. Cloud Build pipeline goes green end-to-end on a feature branch.
