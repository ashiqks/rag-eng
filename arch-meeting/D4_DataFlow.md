# D4 - Data Flow Diagram (companion notes)

**File:** `arch-meeting/D4_DataFlow.drawio`  
**Style:** OWASP DFD (External entity = rectangle, Process = circle, Data store = open rectangle, Trust boundary = red dashed).  
**Source-of-truth flows:** [../PSEC/PSEC_Answers.md](../PSEC/PSEC_Answers.md) section 5.

> **Update — 2026-05-25 ARB review:** DS4 / DS9 renamed and a new DS10 added — BigQuery now holds product data only (AR-5); operational telemetry (DS9) is the **Cloud Observability Suite**, and a new **DS10 Cloud Billing** receives log-based metric-driven budget alerts (AR-6). Flow F23 carries OTel `llm_tokens_in/out`, `model_id`, `skill_name` attributes; new flow F24 connects DS9 → DS10. P1 web is React (AR-9).

## 1. Trust boundaries

| TB | Boundary | Whose policy controls it |
|---|---|---|
| TB1 | Internet | None (untrusted) |
| TB2 | IAP-authenticated session | GCP IAP + Workspace OIDC (`hd: gap.com`) |
| TB3 | Internal Cloud Run mesh | GCP IAM (`run.invoker`) + ingress=`internal` |
| TB4 | VPC-SC perimeter | GCP VPC-SC + PSC private path |
| TB5 | SaaS (Atlassian) | Atlassian Cloud + PAT scope |

Crossing a boundary requires authentication and is logged.

## 2. Entities, processes, data stores

**External entities:** E1 User (gap.com), E2 Workspace IdP, E3 Confluence Cloud, E4 GitHub.  
**Processes:** P0 IAP (Cloud Run native), P1 web, P2 gateway, P3 agent, **P4 Managed BigQuery MCP server** (`bigquery.googleapis.com/mcp`, Google-hosted, inside TB4), P5 exporter Job, P6 reindex Job, P7 weekly-eval, P8 logging sink, P9 Cloud Build.  
**Data stores:** DS1 VAIS engine + Sessions, DS2 Model Garden endpoints, DS3 GCS corpus-html, DS4 BQ `gap_genai_app` (product data only — feedback, golden_evals, eval_runs, app_config.\*; AR-5), DS5 **`v_experiment_kpis`** (BigQuery authorized view over `experiments` + `experiment_clusters`; the only read surface granted to `sa-agent`), DS6 Secret Manager `confluence-pat`, DS7 KMS keyring, DS8 Artifact Registry, **DS9 Cloud Observability Suite** (Logging + Monitoring + Trace, AR-5), **DS10 Cloud Billing** (budget alerts on Discovery Engine + Vertex AI, AR-6).

## 3. Flow inventory (reconciled with PSEC §5)

| ID | From -> To | Data class | Protocol | Auth | Purpose |
|---|---|---|---|---|---|
| F1 | E1 -> P0 | user query | HTTPS/443 | IAP OIDC | submit question |
| F1a | E2 -> P0 | OIDC ID token | HTTPS | OAuth2 | sign-in |
| F2 | P0 -> P1 | query + JWT | HTTPS internal | IAP | edge -> web |
| F3 | P1 -> P2 | AskRequest | HTTPS internal | run.invoker (sa-web) | BFF -> gateway |
| F4 | P2 -> P3 | validated request | HTTPS internal | run.invoker (sa-gateway) | gateway -> agent |
| F5 | P3 -> DS1 | search/answer call | gRPC/443 | sa-agent (`discoveryengine.user`) | retrieval + Sessions append |
| F6 | P3 -> DS2 | prompt + grounding | TLS/443 | sa-agent (`aiplatform.user`) | LLM call (Flash routing -> Pro) |
| F7 | P3 -> P4 | MCP JSON-RPC tool call | HTTPS/443 (public Google endpoint, PSC-routed) | OAuth2 `sa-agent` + `roles/mcp.toolUser`; Model Armor floor settings inspect payload | invoke `execute_sql_readonly` on `v_experiment_kpis` |
| F8 | P4 -> DS5 | SELECT (read-only) | BQ `jobs.query` | `sa-agent` identity propagated by managed MCP; `dataViewer` scoped to view `v_experiment_kpis` only | experiments lookup; every call auto-logged to Cloud Audit Logs (tag `goog-mcp-server:true`) |
| F9 | P3 -> DS4 | request_log + skill_invocation + feedback | BQ insertAll | sa-agent (table-scoped `dataEditor`) | observability / feedback |
| F10 | DS1 -> DS1 | session turn store | internal | GCP-managed | VAIS Sessions auto-append |
| F11 | P3 -> P1 | AskResponse | HTTPS internal | mTLS | answer + citations |
| F12 | P1 -> E1 | rendered answer | HTTPS/443 | session cookie + IAP | response to browser |
| F13 | P5 -> DS6 | secret access | TLS | sa-exporter (`secretAccessor`) | fetch confluence-pat |
| F14 | P5 -> E3 | Confluence GET | HTTPS via Cloud NAT | PAT bearer | weekly content pull |
| F15 | P5 -> DS3 | HTML upload | TLS | sa-exporter (`objectAdmin`) | corpus refresh |
| F16 | P6 -> DS1 | documents.import | gRPC/443 | sa-reindex (`discoveryengine.editor`) | rebuild VAIS index |
| F16a | DS1 -> DS3 | HTML read by VAIS | TLS internal | Discoveryengine SA | indexer pulls HTML |
| F17 | P7 -> DS4 | golden_evals + eval_runs | BQ | sa-agent | weekly eval cycle |
| F18 | P7 -> DS2 | eval prompts | TLS | sa-agent | scoring with Vertex Eval |
| F19 | P3 -> P8 | app + access logs | Logging API | all SAs | observability |
| F20 | P8 -> DS9 | log sink to BQ | internal | logging SA | audit trail |
| F21 | E4 -> P9 | webhook + OIDC | HTTPS | GitHub OIDC -> WIF | trigger build |
| F22 | P9 -> DS8 | image push + deploy | TLS | Cloud Build SA | CI/CD |

## 4. Data classifications (POC defaults)

| Class | Examples | Storage | Retention |
|---|---|---|---|
| Public | Confluence COE pages | GCS, VAIS index | indefinite |
| Internal | feedback, eval_runs, golden_evals, app_config.* | BQ | 90 days (POC) |
| Telemetry (AR-5, AR-6) | request_logs / traces / metrics incl. `llm_tokens_in`, `llm_tokens_out`, `model_id`, `skill_name` | Cloud Observability Suite | 30 days default (cold-tier to GCS optional) |
| Restricted | OIDC tokens (in-flight only), `confluence-pat` | Secret Manager | rotated |
| Audit | admin actions, IAM changes, KMS access | Cloud Logging (Observability Suite) | 1 year (sink to BQ optional, AR-5) |

User free-text queries are classified Internal in POC. **No customer PII enters this system in POC** (locked decision); production must reassess.

## 5. Cross-references

- D2 physical: [D2_Physical.drawio](D2_Physical.drawio)
- D3 network: [D3_Network.drawio](D3_Network.drawio)
- STRIDE: [D5_STRIDE.md](D5_STRIDE.md)
- PSEC flows §5: [../PSEC/PSEC_Answers.md](../PSEC/PSEC_Answers.md)
