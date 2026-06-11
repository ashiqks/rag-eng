# D5 - STRIDE Threat Model

**System:** GAP GenAI Discovery POC  
**Project:** `gap-genai-discovery` (us-central1)  
**Companion DFD:** [D4_DataFlow.drawio](../D4_DataFlow/D4_DataFlow.drawio)  
**Network:** [D3_Network.drawio](../D3_Network/D3_Network.drawio)  
**Physical:** [D2_Physical.drawio](../D2_Physical/D2_Physical.drawio)  
**Method:** Microsoft STRIDE applied per asset, severity scored H/M/L on residual risk after planned mitigations.

> **Update — 2026-05-25 ARB review:** new threat **T13 (D)** LLM token-cost spike via prompt loops / runaway agent — Medium, mitigated by Cloud Billing budget alert + Monitoring alert policy on `llm_tokens_out` rate + Cloud Run max-instances cap (AR-6). DS9 is now the **Cloud Observability Suite** (AR-5); residual-risk rows on the old BQ-as-log-sink are updated accordingly.

## 1. Scope and assumptions

- **In scope:** the POC system as drawn in D2-D4. Single GCP project, single VPC, single region. Confluence Cloud is consumed read-only.
- **Out of scope:** Mathco vendor laptop hardening, GAP corporate network, Atlassian's own cloud security, supply chain of upstream Python/Node packages (assumed reviewed by `gap-genai-admins`).
- **Assumptions:**
  - Workspace IdP is the source of truth for user identity (`hd: gap.com` enforced by IAP).
  - All Cloud Run services have `ingress=internal` except `web` (`internal-and-cloud-load-balancer`).
  - All `*.googleapis.com` traffic from Cloud Run uses VPC connector + PSC (no public IP on the data path).
  - No customer/employee PII enters the system in POC. Free-text queries are classified Internal; users are advised in the UI not to paste PII.
  - All BQ datasets and the GCS bucket are CMEK-encrypted with keys in `gap-genai-kr`.

## 2. External dependencies

| Dep | What we trust them for | What can go wrong |
|---|---|---|
| Google Workspace IdP | OIDC issuance, MFA enforcement | Compromised gap.com user account, IdP outage |
| Atlassian Confluence Cloud | Source content integrity, PAT validation | PAT leak, content tampering at source, SaaS outage |
| GitHub | Source code integrity, OIDC -> Cloud Build | Repo compromise, malicious commit, push-token leak |
| Google Cloud (managed services) | Tenancy isolation, KMS, IAM | Catastrophic platform compromise (residual, accepted) |

## 3. Entry points

1. `https://gap-genai.<domain>` (Cloud DNS -> IAP-on-Cloud-Run -> web). Auth: Workspace OIDC.
2. Cloud Build trigger from GitHub repo (OIDC -> WIF). Auth: GitHub OIDC + branch protection.
3. Cloud Scheduler -> exporter / reindex / eval (internal). Auth: scheduler SA + run.invoker.
4. Console / `gcloud` admin access (`gap-genai-admins`). Auth: Workspace + MFA + IAM Conditions on corporate IP.

## 4. Trust levels

| Level | Who | Notes |
|---|---|---|
| L0 | Anonymous Internet | No access (default-deny + IAP) |
| L1 | gap.com authenticated user | Read-only to web UI |
| L2 | gap-genai-admins | Project IAM admin, KMS admin (split duty) |
| L3 | sa-* (workload identities) | Scoped least-privilege, no human use |
| L4 | Mathco contractor | Same as L1/L2 but with audit override + 90-day access review (PSEC Q on vendor access) |

## 5. Asset inventory and per-asset STRIDE

Severity = **H** (must mitigate before exposure) / **M** (mitigate before scale) / **L** (residual, monitor).  
Status = **Done** / **Planned** / **Open**.

### A1. User browser session (cookie + JWT in transit)

| | Threat | Severity | Mitigation | Status | PSEC ref |
|---|---|---|---|---|---|
| S | Session hijack via XSS in web SPA | M | CSP, HttpOnly+Secure+SameSite=Strict cookies, IAP rotates session | Planned | Q24 |
| T | MITM on transit | L | TLS 1.2+ (Cloud Run managed cert), HSTS on web SPA | Done | - |
| R | User denies asking a question | L | request_log + audit_log keyed by user email | Planned | - |
| I | Token disclosure in browser logs | M | no tokens in URL, Sentry/Logging redaction | Planned | - |
| D | Browser-side DoS (large payload) | L | Cloud Run max-instances cap + per-user rate-limit at gateway | Planned | - |
| E | Token replay across users | M | IAP signs short-lived JWT, gateway re-validates `aud`/`exp` | Planned | - |

### A2. IAP-issued OIDC token

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Forge JWT | H | gateway verifies signature against IAP public keys + `aud=projects/...` | Planned |
| T | - | - | - | - |
| R | Token used by wrong user | M | log `email` + `sub` + `iat` on every request | Planned |
| I | Token leak in logs | H | gateway scrubs `Authorization` headers from logs | Planned |
| D | - | - | - | - |
| E | Privilege via token swap | H | gateway enforces `groups` claim against `gap-genai-users` | Planned |

### A4. Cloud Run `web` service

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Service-to-service call without IAM | H | `ingress=internal-and-cloud-load-balancer` (Cloud Run native IAP), `run.invoker` only for IAP SA | Planned |
| T | Tampered SPA bundle | M | signed images from AR, immutable revisions | Planned |
| R | - | - | - | - |
| I | Stack trace leak | M | structured logs, no error detail to client | Planned |
| D | Cold-start storm | L | min instances = 1, Cloud Run max-instances cap | Done |
| E | RCE in Node deps | M | Cloud Build vuln scan, SBOM, weekly base-image rebuild | Planned |

### A5. Cloud Run `gateway` service

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Spoof identity to agent | H | only `sa-gateway` has `run.invoker` on agent | Planned |
| T | Prompt injection passed through | H | gateway runs prompt redaction + jailbreak filter; Vertex Safety on agent side | Planned |
| R | Quota abuse by single user | M | per-user `user_pseudo_id` rate-limit | Planned |
| I | Sensitive prompts logged | H | gateway redacts known PII patterns before logging; opt-in full-prompt log behind a flag for `gap-genai-admins` only | Planned |
| D | Token bucket exhaustion | M | per-user quota (100 q/min) + global circuit-breaker | Planned |
| E | Skills not in registry invoked | H | gateway validates skill name against `app_config.skill_registry` allowlist | Planned |

### A6. Cloud Run `agent` service (ADK)

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Tool-call confusion (LLM picks wrong skill) | M | strict tool descriptions, Vertex Eval on golden_evals | Planned |
| T | Output manipulation via grounding chunks | M | display only sanitized text + cite-then-quote pattern | Planned |
| R | Action without trace | L | every skill_invocation row has `request_id` + `user_pseudo_id` + `skill` + `args_hash` | Planned |
| I | Cross-session leakage via Sessions | H | VAIS Sessions keyed strictly by `user_pseudo_id`; gateway pins `user_pseudo_id = hash(email + project_salt)` | Planned |
| D | Runaway recursion in agent loop | M | max_steps=8, max_tokens cap, deadline 30s | Planned |
| E | sa-agent over-permissioned | H | `mcp.toolUser` + `bigquery.jobUser` + `bigquery.dataViewer` on view `v_experiment_kpis` only (no raw tables) + `bigquery.dataEditor` on `feedback` only; IAM **deny policy** blocks the read-write `execute_sql` MCP tool. Operational telemetry goes to Cloud Observability Suite, not BQ (AR-5). | Planned |

### A7. Managed BigQuery MCP server (`bigquery.googleapis.com/mcp`, Google-hosted)

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Foreign caller impersonates `sa-agent` to the managed MCP | H | OAuth2 + IAM (`roles/mcp.toolUser`) granted only to `sa-agent`; no SA keys (org policy `iam.disableServiceAccountKeyCreation`); workload identity only | Planned |
| T | Prompt-injection-driven `execute_sql` / DDL | H | IAM **deny policy** removes `execute_sql` (read-write); only `execute_sql_readonly` permitted. **Model Armor** floor settings inspect MCP request + response for injection + malicious URIs. | Planned |
| R | Unattributed query | L | Managed MCP automatically emits Cloud Audit Logs tagged `goog-mcp-server:true` with `sa-agent` as principal, plus the BQ `jobs.query` row carrying `request_id` label propagated from the agent | Done (auto) |
| I | Read of unintended tables | H | `sa-agent` `dataViewer` scoped to the **authorized view** `v_experiment_kpis` only; the view's authorized grant transitively reads `experiments` + `experiment_clusters`. The agent never receives `dataViewer` on raw tables. | Planned |
| D | BQ slot exhaustion / row-cap abuse | L | Managed MCP enforces 3-minute / 3000-row caps; on-demand quota + reservation cap | Done (managed) |
| E | Lateral movement via custom MCP tool registry | M | Removed: no self-hosted toolbox process and no custom tools.yaml. Only Google-published generic MCP tools are available, and they are pinned by the IAM deny policy. | Done |

### A8. Vertex AI Search engine + Sessions

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Foreign caller queries engine | H | `discoveryengine.user` only on `sa-agent`; VPC-SC perimeter | Planned |
| T | Index poisoning via tampered HTML | M | only `sa-reindex` can `documents.import`; corpus bucket write only by `sa-exporter` | Planned |
| R | Search-result citation cannot be reproduced | M | citation includes `document_id` + `version` + `etag` | Planned |
| I | Session content cross-user | H | Sessions keyed by user_pseudo_id; nightly prune; opaque IDs | Planned |
| D | Query rate spike | L | DE quotas per project + Cloud Run max-instances cap | Done |
| E | Engine config change unauthorised | H | only `gap-genai-admins` has `discoveryengine.editor` at engine level | Planned |

### A9. GCS `gap-genai-discovery-corpus-html`

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Identity that should not write does | H | only `sa-exporter` has `objectAdmin`; UBLA on, public access prevention enforced at org policy | Planned |
| T | Object overwrite with malicious HTML | M | object versioning + retention lock; reindex job validates page hash | Planned |
| R | Who uploaded what | L | data access logs to BQ audit_logs | Planned |
| I | Leak of corpus | L | Internal data only (Confluence COE), CMEK key-gcs | Done |
| D | Cost blow-up | L | bucket lifecycle (delete versions > 30d, POC) | Planned |
| E | Bucket made public | H | `storage.publicAccessPrevention=enforced` org policy | Done |

### A10. BigQuery operational tables (feedback, eval_runs, golden_evals, app_config.* — product data only after AR-5; request logs moved to Observability Suite)

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | sa-agent queries ops tables via the managed MCP | H | `dataViewer` for `sa-agent` is granted **only** on view `v_experiment_kpis`; the agent has no `dataViewer` on `gap_genai_app.*`; the IAM **deny policy** also blocks the read-write `execute_sql` MCP tool | Planned |
| T | Log row tampering | M | append-only via insertAll; daily integrity checksum job | Planned |
| R | - | - | - | - |
| I | PII in free-text query columns | H | gateway redacts PII before logging; column-level access policy on log-entry `question_text` field in the Cloud Observability Suite (admins only) | Planned |
| D | High-volume insert from agent loop | L | quotas + per-table partition limits | Done |
| E | dataEditor used to read other tables | H | scoped to 3 tables only via table-level IAM | Planned |

### A11. BigQuery `experiments` + `experiment_clusters` (read-only via authorized view `v_experiment_kpis`)

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Non-MCP caller reads | M | only the `v_experiment_kpis` authorized view holds the read grant; `sa-agent` has `dataViewer` on the view only; raw tables are hidden from every project SA | Planned |
| T | Source data drift | L | upstream owners are ETL teams; agent shows `as_of` timestamp | Planned |
| I | Sensitive cluster data | M | confirm classification with data owner before scale (PSEC Q: data classification) | **Open** |

### A12. Secret Manager `confluence-pat`

| | Threat | Severity | Mitigation | Status | PSEC ref |
|---|---|---|---|---|---|
| S | Wrong SA reads secret | H | `secretAccessor` only on `sa-exporter`, replicated user-managed (us-central1) | Planned | Q21 |
| T | Replace secret value | M | only `gap-genai-admins` has `secretmanager.admin`; version retention | Planned | - |
| R | Who rotated last | L | audit_logs row for every `AccessSecretVersion` | Planned | - |
| I | Secret leaked via logs | H | structured logging never serialises env vars; `confluence-pat` mounted via Secret Manager volume, not env | Planned | - |
| D | - | - | - | - | - |
| E | Vault vs Secret Manager dispute | H | **OPEN** - PSEC Q21 unresolved (Vault preferred but POC uses Secret Manager) | **Open** | Q21 |

### A13. Cloud KMS keys (key-gcs, key-bq)

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Decrypt by unintended SA | H | scoped `cryptoKeyEncrypterDecrypter` per service-agent SA only | Planned |
| T | Key rotation failure | M | rotation period 90d, alert on rotation skipped | Planned |
| R | Key access untracked | L | data access logs on KMS enabled | Planned |
| I | Key material exfiltration | L | KMS is HSM-backed by Google; export disabled | Done |
| D | Region outage -> data unreadable | M | accept POC risk; production must consider key replication | **Open** |
| E | Project owner can grant kms admin | H | split duty: `gap-genai-admins-kms` is a separate group | Planned |

### A14. BigQuery `audit_logs`

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| T | Tampered audit | H | append-only; logBucket `_Required` immutable + sink to BQ; alerts on schema change | Planned |
| R | Repudiation | L | both Cloud Audit Logs `_Required` AND application audit table | Planned |
| I | Sensitive admin actions exposed | M | column-level access on PII columns | Planned |
| E | Delete logs to hide tracks | H | sink with `iam.disableAuditLogExemptions`, retention lock 1y | Planned |

### A15. Cloud Run Jobs (exporter + reindex)

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Triggered by non-Scheduler SA | H | `run.invoker` granted only to Cloud Scheduler SA + `gap-genai-admins` | Planned |
| T | Confluence content tampered upstream | M | export captures Confluence `version` + `etag`; reindex skips unchanged | Planned |
| I | Confluence PAT logged | H | exporter redacts `Authorization` header; PAT mounted as volume | Planned |
| D | Confluence rate-limit | L | exponential backoff + 24h SLO budget for re-export | Planned |
| E | Job promoted to service | M | only Cloud Build deploy via signed images can change job spec | Planned |

### A16. Service accounts collectively

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Key created and exfiltrated | H | `iam.disableServiceAccountKeyCreation` org policy; workload identity only | Done |
| T | SA permissions escalated silently | M | terraform-only IAM bindings; PR review on `gap-genai-admins` group | Planned |
| R | SA actions untracked | L | Cloud Audit Logs `Data Access` enabled on all SAs | Planned |
| E | sa-agent escalation via custom role drift | H | use only predefined roles where possible; quarterly role review | Planned |

### A17. Cloud Build pipeline

| | Threat | Severity | Mitigation | Status |
|---|---|---|---|---|
| S | Forged trigger | H | GitHub OIDC + branch protection (`main` only) | Planned |
| T | Malicious dependency | H | SBOM scan, Vertex AI Workbench-style image allowlist, BCv2 vulnerability scanning | Planned |
| I | Build secrets leak | M | Cloud Build uses Secret Manager, no env vars in YAML | Planned |
| E | Build SA over-permissioned | H | Cloud Build SA scoped to AR push + `run.developer` on this project only | Planned |

## 6. Risk summary matrix (after planned mitigations)

| Asset | S | T | R | I | D | E |
|---|---|---|---|---|---|---|
| A1 user session | M | L | L | M | L | M |
| A2 OIDC token | H -> L | - | M -> L | H -> L | - | H -> L |
| A4 web | H -> L | M | - | M | L | M |
| A5 gateway | H -> L | H -> M | M | H -> M | M | H -> L |
| A6 agent | M | M | L | H -> M | M | H -> L |
| A7 BQ MCP (managed) | H -> L | H -> L | L (auto) | H -> L | L (managed) | M -> L |
| A8 VAIS+Sessions | H -> L | M | M | H -> M | L | H -> L |
| A9 GCS corpus | H -> L | M | L | L | L | H -> L |
| A10 BQ ops | H -> L | M | - | H -> M | L | H -> L |
| A11 BQ experiments | M | L | - | M (open) | - | - |
| A12 Secret Manager | H -> L | M | L | H -> L | - | H (open Q21) |
| A13 KMS | H -> L | M | L | L | M (open) | H -> L |
| A14 audit_logs | - | H -> L | L | M | - | H -> L |
| A15 Jobs | H -> L | M | - | H -> L | L | M |
| A16 SAs | H -> L (done) | M | L | - | - | H -> L |
| A17 Cloud Build | H -> L | H -> M | M | - | - | H -> L |

## 7. Top-5 residual risks (POC -> production)

1. **PSEC Q21 (Vault vs Secret Manager) unresolved** - currently `confluence-pat` is in GCP Secret Manager. If GAP standard mandates HashiCorp Vault, every secret-access flow must change. **Owner:** PSEC + platform.
2. **Free-text query PII** - users may paste internal-confidential or even regulated data into the chat. POC mitigation is gateway-side regex redaction; production needs DLP API + UI banner + classification policy. **Owner:** legal + platform.
3. **PSEC Q24 (Internet-accessible)** - the Cloud Run `web` service is Internet-reachable; only IAP (Cloud Run native) gates it. PSEC may require either VPN-only access or an internal-only ingress with Workspace SSO front. **Owner:** PSEC.
4. **PSEC Q8 (GCP hosting decision)** - confirms multi-cloud / data-residency posture. POC assumes us-central1 only. **Owner:** PSEC + cloud platform.
5. **Single-region resilience for KMS / VAIS** - if `us-central1` is down, the system is down and BQ data may be unreadable. POC accepts; production must consider multi-region keys, mirrored corpus, regional failover. **Owner:** SRE.

## 8. Cross-references

- D2 physical: [D2_Physical.drawio](../D2_Physical/D2_Physical.drawio)
- D3 network: [D3_Network.drawio](../D3_Network/D3_Network.drawio)
- D4 DFD: [D4_DataFlow.drawio](../D4_DataFlow/D4_DataFlow.drawio)
- PSEC answers: [../PSEC/PSEC_Answers.md](../../PSEC/PSEC_Answers.md)
- Vendor access: [../PSEC/Vendor_Access.md](../../PSEC/Vendor_Access.md)
- Service inventory: [../Vertex_AI_Search_Variant/GCP_Services_Required.md](../../Vertex_AI_Search_Variant/GCP_Services_Required.md)
