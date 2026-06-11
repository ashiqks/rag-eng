# D2 - Physical Diagram (companion notes)

**File:** `arch-meeting/D2_Physical/D2_Physical.drawio`  
**Audience:** GCP architects, platform engineers, security reviewers  
**Scope:** GCP project `gap-genai-discovery`, region `us-central1`, env `POC`

> **Update — 2026-05-25 ARB review:** diagram reflects AR-1 (Confluence read-only SA-PAT), AR-5 (Cloud Observability Suite replaces BigQuery as the log sink — BQ holds product data only), AR-6 (LLM token capture + `gap_genai/llm_tokens_*` log-based metrics + Cloud Billing budget alerts), and AR-9 (React SPA web tier). See [`../High_Level_Design.md`](../../High_Level_Design.md) §5 for the full action-item ledger.

The Physical diagram shows the **named, deployable resources** that exist in GCP (and the one external SaaS) for the GenAI Discovery POC, grouped by plane. It is the bill-of-materials view: every box is something you can `gcloud describe`. Logical concerns (multi-region, capacity tiers, abstract "search service") were already covered in `High_Level_Design.drawio`.

## 1. Planes

| Plane | What it contains | Color cue |
|---|---|---|
| Edge / Networking | Cloud DNS, IAP (Cloud Run native), Serverless VPC Access connector, Cloud NAT, VPC, VPC-SC perimeter | Blue |
| Compute (Cloud Run) | `gap-genai-discovery-web`, `-gateway`, `-agent`, `-exporter` (Job), `-reindex` (Job) | Green |
| Managed AI | Vertex AI Search engine + data store + Sessions, Vertex Model Garden (Gemini 2.5 Flash + Pro), Vertex Eval Service, **Managed BigQuery MCP server** (`bigquery.googleapis.com/mcp`) | Purple |
| Data | GCS `gap-genai-discovery-corpus-html`, BigQuery dataset `gap_genai_app` (7 product-data tables, AR-5), Artifact Registry repos | Amber |
| Security | Secret Manager `confluence-pat`, Cloud KMS keyring `gap-genai-kr` (`key-gcs`, `key-bq`), Cloud IAM, 5 service accounts, **Model Armor floor settings** (MCP traffic inspection) | Red |
| Ops / CI-CD | Cloud Logging, Cloud Monitoring, Cloud Trace + Error Reporting, Cloud Scheduler, Cloud Build, GitHub, Pub/Sub log sink | Grey/Blue |
| External | Atlassian Confluence Cloud (Test & Learn COE space), Google Workspace IdP | Grey |

## 2. Service accounts (least privilege)

| SA | Bound to | Key roles |
|---|---|---|
| `sa-web` | `gap-genai-discovery-web` | `roles/run.invoker` on gateway |
| `sa-gateway` | `gap-genai-discovery-gateway` | `roles/run.invoker` on agent |
| `sa-agent` | `gap-genai-discovery-agent` | `roles/discoveryengine.user`, `roles/aiplatform.user`, `roles/mcp.toolUser`, `roles/bigquery.jobUser`, `roles/bigquery.dataViewer` on view `v_experiment_kpis` (only), `roles/bigquery.dataEditor` on `feedback` (writes only). IAM **deny policy** blocks the read-write `execute_sql` MCP tool. |
| `sa-exporter` | `gap-genai-discovery-exporter` Job | `roles/storage.objectAdmin` on corpus bucket, `roles/secretmanager.secretAccessor` on `confluence-pat` |
| `sa-reindex` | `gap-genai-discovery-reindex` Job | `roles/discoveryengine.editor` on engine + data store, `roles/storage.objectViewer` on corpus bucket |

## 3. Key transport/auth on every edge

- **User -> IAP (Cloud Run native):** HTTPS/443 (TLS 1.2+, Cloud Run managed certificate).
- **IAP -> Cloud Run web:** Cloud Run native IAP integration; Workspace OIDC (`hd=gap.com`); managed TLS via Cloud Run.
- **web -> gateway -> agent:** Internal Cloud Run-to-Cloud Run, ID-token via `roles/run.invoker`, ingress = `internal`.
- **agent -> Managed BigQuery MCP (`https://bigquery.googleapis.com/mcp`):** MCP JSON-RPC over HTTPS/443, OAuth2 + IAM (`sa-agent`, `roles/mcp.toolUser`). Tool calls are restricted to `execute_sql_readonly` against the authorized view `v_experiment_kpis`. Every tool call is auto-logged to **Cloud Audit Logs** tagged `goog-mcp-server:true`; no glue code on our side. **Model Armor** floor settings inspect prompts/responses for injection + malicious URIs (AR-9 / STRIDE T2/T4 mitigation). No Cloud Run hop for this skill.
- **agent -> Vertex AI Search `:answer`:** gRPC/443 with `sa-agent` (Sessions auto-managed by VAIS).
- **agent -> Model Garden Gemini Flash + Pro:** TLS/443 with `sa-agent`.
- **Managed BigQuery MCP -> BigQuery:** Google-internal; the agent's identity is propagated, so the BQ job runs as `sa-agent` and is scoped by the `dataViewer` grant on the `v_experiment_kpis` authorized view. The view itself is authorized on the underlying `experiments` + `experiment_clusters` tables, so the agent never receives `dataViewer` on the raw tables.
- **exporter -> Confluence Cloud:** VPC connector -> Cloud NAT (1 static IP, allowlisted on Atlassian) -> HTTPS/443 + PAT.
- **exporter -> GCS:** TLS/443 with `sa-exporter` (write `pages/<space>/<page_id>.html`).
- **reindex -> VAIS:** `documents.import` (gRPC/443) with `sa-reindex`.
- **CMEK:** `key-gcs` encrypts the corpus bucket, `key-bq` encrypts the dataset.
- **Telemetry (AR-5, AR-6):** every Cloud Run service + Job emits OTel (logs, traces, metrics) to the **Cloud Observability Suite** (Logging + Monitoring + Trace + Profiler + Error Reporting). Log-based metrics `gap_genai/llm_tokens_in`, `gap_genai/llm_tokens_out`, `gap_genai/llm_calls`, `gap_genai/llm_cost_usd` are wired to a Cloud Monitoring dashboard and a Cloud Billing line-item budget alert on Discovery Engine + Vertex AI (plus a Monitoring alert policy on output-token rate-of-change). BigQuery is **not** used as a log sink.

## 4. BigQuery tables (in `gap_genai_app`, CMEK `key-bq`)

`feedback`, `golden_evals`, `eval_runs`, `app_config.skill_registry`, `app_config.ingest_state`, `experiments` (raw), `experiment_clusters` (raw).

**Authorized view:** `v_experiment_kpis` = `experiments` JOIN `experiment_clusters USING (cluster_id)`. This is the **only** BigQuery read surface granted to `sa-agent`; the raw tables are reachable only transitively through the view's authorized grant. Switching the agent from the (decommissioned) self-hosted `mcp-toolbox-databases` Cloud Run service to the Google-managed `bigquery.googleapis.com/mcp` endpoint means the agent now uses the generic `execute_sql_readonly` MCP tool against this view instead of a custom parameterised `query_experiment_kpis` tool.

Operational telemetry (request logs, traces, latency, token usage) lives in the Cloud Observability Suite, not BigQuery (AR-5).

## 5. Cloud Scheduler jobs (POC defaults, US/Pacific)

| Job | Cron | Target |
|---|---|---|
| `weekly-export` | Mon 02:00 PT | exporter Job |
| `weekly-reindex` | Mon 03:00 PT | reindex Job |
| `weekly-eval` | Sun 04:00 PT | agent eval endpoint |
| `nightly-session-prune` | Daily 01:00 PT | maintenance task on VAIS Sessions |

## 6. Cross-references

- HLD: [../High_Level_Design.drawio](../../High_Level_Design.drawio)
- Service inventory & IAM: [../Vertex_AI_Search_Variant/GCP_Services_Required.md](../../Vertex_AI_Search_Variant/GCP_Services_Required.md)
- Data flow / ports: [../PSEC/PSEC_Answers.md](../../PSEC/PSEC_Answers.md) section 5
- Network detail: [D3_Network.drawio](../D3_Network/D3_Network.drawio)
- Threat model: [D5_STRIDE.md](../D5_STRIDE/D5_STRIDE.md)
