# Required GCP Services - Onboarding Request

> Architecture: **Vertex AI Search variant** (single-region POC, `us-central1`, GCP project `gap-genai-discovery`).
> Include the following APIs and quota requests in the GCP onboarding ticket.
>
> **PSEC story #**: TBD (open before submission). **PSEC category**: Architecture / POC. **PSEC answer sheet**: [`../PSEC/PSEC_Answers.md`](../PSEC/PSEC_Answers.md). **Open P0 blockers** that may invalidate parts of this list before onboarding starts: (1) Q8 - form has no GCP option, confirm GCP is an approved Gap hosting target; (2) Q21 - confirm GCP Secret Manager is accepted in lieu of HashiCorp Vault.

---

## 1. Core required services

| # | GCP Service | API Identifier | Purpose in this design |
|---|-------------|----------------|------------------------|
| 1 | Cloud Run | `run.googleapis.com` | Web App, Backend (ADK Discovery Agent), and Cloud Run Jobs (Exporter, Reindex Trigger) |
| 2 | Cloud Storage (GCS) | `storage-api.googleapis.com` | `gap-genai-discovery-corpus-html` bucket - Vertex AI Search datastore source |
| 3 | BigQuery | `bigquery.googleapis.com` | `gap_genai_app` dataset — product data only: experiments, experiment_clusters, feedback, golden_evals, eval_runs, app_config.skill_registry, app_config.ingest_state (no log tables — AR-5) |
| 4 | Cloud Scheduler | `cloudscheduler.googleapis.com` | Weekly cron for Exporter and Reindex Trigger jobs |
| 5 | Secret Manager | `secretmanager.googleapis.com` | Confluence **read-only service-account PAT** (no employee tokens — AR-1) and any third-party API keys |
| 6 | Cloud IAM | `iam.googleapis.com` | Per-service accounts, least-privilege bindings |
| 7 | Cloud Logging | `logging.googleapis.com` | Structured logs from all Cloud Run services and Jobs |
| 8 | Cloud Monitoring | `monitoring.googleapis.com` | Metrics, uptime checks, alert policies, SLOs |
| 9 | Cloud Build | `cloudbuild.googleapis.com` | CI pipeline that builds container images from GitHub |
| 10 | Artifact Registry | `artifactregistry.googleapis.com` | Docker repos: `gap-web`, `gap-backend`, `gap-jobs` |

## 2. Vertex AI services (the core RAG engine)

| # | GCP Service | API Identifier | Purpose |
|---|-------------|----------------|---------|
| 11 | Vertex AI Search / Agent Builder | `discoveryengine.googleapis.com` | Search engine `gap-genai-discovery-search` (Enterprise + LLM Add-on), unstructured GCS datastore, Chat Sessions |
| 12 | Vertex AI Platform | `aiplatform.googleapis.com` | Evaluation Service (weekly golden-set), grounded-generation calls, embeddings if needed, **Vertex AI Model Garden** for `gemini-2.5-flash` (intent classification + param extraction) and `gemini-2.5-pro` (chained narrative summarisation) consumed by the ADK Agent via per-skill model bindings - no custom router class |

## 2a. MCP integration (Dashboard Data Agent - Day-1)

See [`Architecture.md`](Architecture.md) §7. Follows Google's [Single-agent ADK + Cloud Run reference](https://docs.cloud.google.com/architecture/single-agent-ai-system-adk-cloud-run).

| # | Component | Identifier | Purpose |
|---|-----------|------------|---------|
| 12a | **Managed BigQuery MCP server** | Google-hosted endpoint `https://bigquery.googleapis.com/mcp` (no Cloud Run service in our project, no container to deploy) | Google-managed MCP server bundled with the BigQuery API. Exposes generic tools (`execute_sql_readonly`, `list_dataset`, `get_table`, etc.). The ADK Agent reaches it via the MCP client built into ADK using `sa-agent` (OAuth2 + `roles/mcp.toolUser`). All access scoped to the authorized view `v_experiment_kpis`; raw tables hidden. Auto-logs to Cloud Audit Logs with `goog-mcp-server:true`. No new GCP API enablement beyond `bigquery.googleapis.com`. |
| 12b | **`experiments` + `experiment_clusters` tables** | BigQuery `gap_genai_app.experiments`, `gap_genai_app.experiment_clusters` (existing dataset, no new dataset) | Structured KPI data the Dashboard Data Agent reads on demand. **Pipeline / ingestion is owned by another team and is OUT OF SCOPE** for this onboarding request. We only need read access. |

**IAM bindings**:
- Backend Agent SA (`sa-agent`) gets `roles/mcp.toolUser` + `roles/bigquery.jobUser` + `roles/bigquery.dataViewer` scoped to the authorized view `gap_genai_app.v_experiment_kpis` only (no raw-table grant). An IAM **deny policy** blocks the read-write `execute_sql` MCP tool so only `execute_sql_readonly` is reachable.
- No `sa-mcp-toolbox` exists — the managed MCP runs in Google's infrastructure and uses the caller's identity (`sa-agent`). Total project SA count drops from 6 to 5.

## 3. Networking, gateway, and edge

| # | GCP Service | API Identifier | Purpose |
|---|-------------|----------------|---------|
| 13 | Compute Engine API | `compute.googleapis.com` | Required for VPC / Cloud Router / Cloud NAT only. (Edge LB / Cloud Armor not used — Cloud Run native IAP fronts the Web App.) |
| 14 | Certificate Manager | `certificatemanager.googleapis.com` | Not required for POC: Cloud Run native IAP provides a managed TLS cert for the custom domain. (Retain row only if a future custom-domain config opts out of the managed cert.) |
| 15 | Cloud DNS | `dns.googleapis.com` | DNS zone for `gap-genai.<gap-domain>` |
| 16 | Identity-Aware Proxy (IAP) | `iap.googleapis.com` | SSO / OIDC enforcement enabled directly on the Cloud Run `web` service (Cloud Run native IAP integration) |
| 17 | Serverless VPC Access | `vpcaccess.googleapis.com` | VPC connector so Cloud Run egress stays inside the VPC perimeter (needed once VPC-SC is enabled) |
| 18 | Service Networking | `servicenetworking.googleapis.com` | Private service connections, required by VPC-SC configurations |
| 19 | Access Context Manager | `accesscontextmanager.googleapis.com` | **VPC Service Controls** perimeter around `discoveryengine` + `storage` + `bigquery` |

> **API Gateway / Cloud Endpoints: NOT required.** Cloud Run native IAP fronts the Web App; the Backend is reached only by the Web App over its internal Cloud Run URL with IAM auth (`run.invoker`), so no separate API gateway is needed.

## 4. Observability and tracing

| # | GCP Service | API Identifier | Purpose |
|---|-------------|----------------|---------|
| 20 | Cloud Trace | `cloudtrace.googleapis.com` | OpenTelemetry traces across Web App -> Backend -> Vertex AI Search |
| 21 | Cloud Profiler | `cloudprofiler.googleapis.com` | Optional - latency hot-spot profiling on the Backend |
| 22 | Error Reporting | `clouderrorreporting.googleapis.com` | Aggregated exception view |

## 5. Security and key management

| # | GCP Service | API Identifier | Purpose |
|---|-------------|----------------|---------|
| 23 | Cloud KMS | `cloudkms.googleapis.com` | CMEK keys for GCS bucket and BigQuery dataset |
| 24 | Security Command Center (Standard) | `securitycenter.googleapis.com` | Org-level posture, surface findings for the project |

## 6. Eventing (optional, only if event-driven reindex is chosen over cron)

| # | GCP Service | API Identifier | Purpose |
|---|-------------|----------------|---------|
| 25 | Eventarc | `eventarc.googleapis.com` | GCS `OBJECT_FINALIZE` -> Reindex Trigger Job (instead of weekly Cloud Scheduler only) |
| 26 | Pub/Sub | `pubsub.googleapis.com` | Eventarc transport; also used by log-sinks to BigQuery |

## 7. Project administration

| # | GCP Service | API Identifier | Purpose |
|---|-------------|----------------|---------|
| 27 | Cloud Resource Manager | `cloudresourcemanager.googleapis.com` | Project/folder/org metadata, IAM policy management |
| 28 | Service Usage | `serviceusage.googleapis.com` | Enable / disable APIs programmatically (Terraform) |
| 29 | Cloud Billing Budgets | `billingbudgets.googleapis.com` | Monthly budget + alert thresholds on the project |

---

## 8. CI/CD options - what to ask onboarding for

| Item | Choice | Notes |
|------|--------|-------|
| Source of truth | GitHub (GAP enterprise org) | External - no GCP API needed |
| Build runner | **Cloud Build** | `cloudbuild.googleapis.com` - already in row 9. Triggers wired to GitHub via the Cloud Build GitHub App |
| Image registry | **Artifact Registry** (Docker, regional `us-central1`) | Row 10 |
| Deploy target | **Cloud Run** (Web App, Backend) + **Cloud Run Jobs** (Exporter, Reindex) | Row 1 |
| Optional: managed pipelines | **Cloud Deploy** (`clouddeploy.googleapis.com`) | Only if onboarding wants progressive delivery / approval gates. Not required for POC |

## 9. Gateway / Edge - what to ask onboarding for

| Item | Choice | Notes |
|------|--------|-------|
| Public ingress | **IAP enabled on the Cloud Run `web` service** (Cloud Run native IAP integration) | No External HTTPS LB / Serverless NEG / Cloud Armor required at POC scale |
| TLS | **Cloud Run managed certificate** for the custom domain | Provisioned automatically when IAP is enabled on Cloud Run |
| Identity | **IAP** OIDC against GAP IdP, restricted to `hd=gap.com` + group membership | Row 16 |
| Backend-to-backend | **Cloud Run-to-Cloud Run** with `run.invoker` IAM, no public exposure | No additional API |
| API Gateway? | **Not needed** | The Web App is the only public surface; the Backend is private |

## 10. Networking - what to ask onboarding for

| Item | Choice | Notes |
|------|--------|-------|
| VPC | Existing GAP shared VPC OR a project-local VPC `gap-genai-vpc` | `compute.googleapis.com` |
| Private Google Access | **Enabled** on the subnet | So Cloud Run can reach Google APIs without public IPs |
| Serverless VPC connector | `gap-genai-connector` (us-central1, /28) | Row 17, required once VPC-SC is on |
| Cloud NAT | Only if Cloud Run egress needs to reach the public internet (Confluence) AND egress must come from a fixed range | Confluence Cloud usually allows the Google ASN, so NAT may be optional |
| VPC Service Controls | Perimeter around `storage`, `bigquery`, `discoveryengine`, `aiplatform`, `secretmanager` | Row 19 |
| Cloud DNS private zone | Optional - only if backend services need private DNS names | Row 15 |

---

## 11. Single-shot enable-services command (for reference)

```bash
gcloud services enable \
  run.googleapis.com \
  storage-api.googleapis.com \
  bigquery.googleapis.com \
  cloudscheduler.googleapis.com \
  secretmanager.googleapis.com \
  iam.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  discoveryengine.googleapis.com \
  aiplatform.googleapis.com \
  compute.googleapis.com \
  certificatemanager.googleapis.com \
  dns.googleapis.com \
  iap.googleapis.com \
  vpcaccess.googleapis.com \
  servicenetworking.googleapis.com \
  accesscontextmanager.googleapis.com \
  cloudtrace.googleapis.com \
  clouderrorreporting.googleapis.com \
  cloudkms.googleapis.com \
  cloudresourcemanager.googleapis.com \
  serviceusage.googleapis.com \
  billingbudgets.googleapis.com \
  --project=gap-genai-discovery
```

Eventarc + Pub/Sub (rows 25-26) and Cloud Deploy / Profiler / Security Command Center are opt-in and can be enabled later if required.
