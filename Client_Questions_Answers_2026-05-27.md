# Client questions — answers

**Date:** 2026-05-27  
**Scope:** Confluence-grounded GenAI Discovery + Dashboard Data Agent variant  
**Baseline:** Post-ARB 2026-05-25 (AR-1…AR-12) + 2026-05-27 MCP refactor (managed BigQuery MCP replaces the self-hosted MCP toolbox)

> **[Outdated premise]** = question reflects a prior architecture; answer states the current design.

---

## 1. Engagement model — installed product or bespoke build

**Bespoke build on Gap's own GCP (staff-augmentation), not a vendor product install.**

- Every Cloud Run service / Job, GCS bucket, BigQuery dataset, VAIS engine, KMS keyring, Secret Manager secret, VPC, PSC endpoint and IAM binding is provisioned in **Gap's GCP project** and billed to Gap.
- MathCo delivers source code, Terraform and the LLDs in this repo; MathCo hosts nothing and retains no data.
- The only Google-managed surfaces used (VAIS, Vertex AI Model Garden Gemini 2.5 F/P, the managed BigQuery MCP server, Vertex AI Evaluation, Cloud Observability Suite) are first-party GCP services consumed under Gap's existing enterprise agreement.
- Vendor access is time-bound and IAM-conditional via Gap-issued Workspace identities; no MathCo identity has standing access to prod. See [PSEC/Vendor_Access.md](PSEC/Vendor_Access.md).

**Review implication:** architecture review of Gap-owned infra with a third-party build partner — **not** a vendor product review.

---

## 2. Confluence PAT — personal or service account

**Dedicated read-only Atlassian service-account PAT** (AR-1). Not a personal token.

- Stored in Secret Manager, CMEK-encrypted, mounted as a **volume** (never env var) by the ingest Cloud Run Job. Only the ingest job's SA holds `secretmanager.secretAccessor` on the secret.
- Org policy disables SA-key creation; workload identity only. Quarterly rotation; every access emits a Cloud Audit Log row.
- **Open:** PSEC Q21 (Vault vs Secret Manager) is parked at the platform team; if Vault is mandated, the secret-access flow changes.
- **Provisioning status:** AR-1 decision is reflected in diagrams and code paths; the Atlassian-side SA-PAT issuance ticket is **OPEN** and must close before pilot promotion.

---

## 3. Data classification of the experiment corpus

**Internal — Confidential business IP. No customer PII, no PCI in POC** (locked; production reassesses).

- Content: A/B test write-ups, conversion / revenue / AOV / UPT lifts, confidence figures, store-level results, brand × region segmentation, taxonomy. Confidential business IP — not customer data.
- Storage: GCS bucket with UBLA on, `storage.publicAccessPrevention=enforced` (org policy), CMEK, versioning + retention lock. Write only by ingest SA; read only by the reindex SA and the VAIS indexer.
- Index: VAIS engine sits inside a **VPC-SC perimeter**, reachable only via PSC, queryable only by the agent SA.
- Runtime access: IAP + Workspace OIDC (`hd: gap.com`); user identity hashed into a `user_pseudo_id` so users cannot cross-read sessions.
- Ingest is scoped to the Test & Learn COE Confluence space only (not a global crawl). Production go-live runs a DLP scan against the corpus to confirm zero PII before pilot.
- Free-text queries are also Internal — Gateway redacts PII regex patterns before any logging; full-prompt logging is admin-only and off by default.

---

## 4. BigQuery log contents — query / response retention

**[Outdated premise]** Under AR-5, request logs, skill invocations, traces and latencies **no longer live in BigQuery** — they live in the **Cloud Observability Suite**.

Current state:

- **BigQuery holds product data only:** `feedback`, `golden_evals`, `eval_runs`, `app_config.*`, plus the upstream `experiments` and `experiment_clusters` tables surfaced via the **authorized view** `v_experiment_kpis`. CMEK-encrypted, partitioned daily, 90-day retention (POC).
- **Observability Suite (Logging + Monitoring + Trace)** holds OTel events with attributes `request_id`, `user_pseudo_id`, `skill_name`, `model_id`, `llm_tokens_in/out`, `latency_ms`. Default 30-day retention; cold-tier to GCS optional.
- **Query / response text:**
  - Gateway redacts PII and known-secret patterns **before** logging. Structured entries carry redacted text + a hash; the raw prompt is **not** persisted.
  - Column-level access policy on `question_text` restricts read to the admin group; opt-in full-prompt logging is per-environment and off in prod.
  - Model responses are not stored verbatim — only token counts, citation IDs and the answer hash; cite-then-quote rendering keeps responses traceable.
- **Dataset access:** agent SA has `dataEditor` on `feedback` only, `dataViewer` on the view only, `jobUser` for `jobs.query`; reindex SA on the ingest-state table only; admin group for break-glass. An **IAM deny policy** blocks the read-write `execute_sql` MCP tool — only `execute_sql_readonly` is callable.
- **Audit:** every MCP-driven BQ call is auto-tagged `goog-mcp-server:true` in Cloud Audit Logs with the agent SA as principal. The `_Required` audit bucket is immutable, 1-year retention, `iam.disableAuditLogExemptions` enforced.

---

## 5. IAM and service-account least-privilege

**Yes** — per-component SAs, least-privilege, IAM review done at ARB 2026-05-25 (AR-10) and re-verified 2026-05-27 after the MCP refactor reduced SA count from **6 → 5**.

| Component | SA scope (high-level) |
|---|---|
| Cloud Run web | invoke gateway only |
| Cloud Run gateway | invoke agent only |
| Cloud Run agent | `discoveryengine.user`, `aiplatform.user`, `mcp.toolUser`, `bigquery.jobUser`, `bigquery.dataViewer` on view only, `bigquery.dataEditor` on `feedback` only. **IAM deny policy** removes the read-write `execute_sql` MCP tool. |
| Ingest Cloud Run Job | `storage.objectAdmin` on corpus bucket only; `secretmanager.secretAccessor` on Confluence PAT only. **No** BigQuery, no Vector-Search admin, no Cloud Run invoke. |
| Reindex Cloud Run Job | `discoveryengine.editor` (data store + engine), `storage.objectViewer` on corpus bucket |

Controls:

- Org policy `iam.disableServiceAccountKeyCreation` enforced; workload identity only.
- IAM bindings Terraform-managed; every change is a reviewed PR.
- Agent has **no** read grant on the raw `experiments` / `experiment_clusters` tables — all reads transit the authorized view. The view's authorized grant is the only path.
- VPC-SC perimeter covers Discovery Engine, Vertex AI, BigQuery, GCS, Secret Manager, Logging, Monitoring. The managed BigQuery MCP rides the existing BigQuery PSC endpoint (same API host) — no new perimeter hole.
- Cloud Audit Logs `Data Access` enabled on all SAs. Quarterly SA-role review is planned.
- **2026-05-27 change:** decommissioning the self-hosted MCP toolbox Cloud Run service removed its dedicated SA entirely. The managed BigQuery MCP runs inside Google's infrastructure and propagates the caller's identity, so there is no third-party SA handling BigQuery on the agent's behalf.

STRIDE per asset: [D5_STRIDE.md](arch-meeting/D5_STRIDE/D5_STRIDE.md).

---

## 6. Enterprise Architecture alignment

**Partial.** AI Architect review completed 2026-05-25 (AR-1…AR-12 in [High_Level_Design.md](High_Level_Design.md) §5). **Formal EA / ARB sign-off against the in-progress Gap AI Agentic reference pattern is OPEN.**

- DONE: AR-5 (Observability Suite, BQ product-data-only), AR-6 (LLM token tracking + budget alerts), AR-7 (VAIS native sessions), AR-9 (React frontend), AR-10 (security on diagrams).
- OPEN: AR-11 (upload HLD + LLDs to the Confluence ARB review page), AR-12 (clarify ARB-reviewer document-set requirements). Gap's AI Agentic reference pattern itself is in-progress; reconciliation against it is gated on AR-11 / AR-12.
- This build aligns with the public Google reference [Single-agent AI system using ADK and Cloud Run](https://docs.cloud.google.com/architecture/single-agent-ai-system-adk-cloud-run) plus the AR-decisions above.
- **Recommendation:** schedule formal EA / ARB review once AR-11 lands; treat any deltas the reference pattern raises as production-blocking before pilot.

---

## 7. Vertex AI Evaluation Service — data submitted

**Curated golden-set prompts only** — **no raw user queries** are sent to Vertex Eval.

- Source: the `golden_evals` BigQuery table — hand-curated regression prompts (text + expected filters + expected citations + rubric), authored by the eval team. Not sampled from production traffic.
- Per run: the agent re-issues each golden prompt against the live engine; the `(prompt, model_response, retrieved_chunks, citations)` tuple is scored by Vertex Eval against the rubric and the result is written back to `eval_runs`.
- Residency: Vertex AI Evaluation runs in `us-central1`, the same region as VAIS, Model Garden and BigQuery. No cross-region or cross-cloud movement.
- Customer data: none (locked POC assumption — no customer PII enters the platform).
- Contractual: covered by the standard Vertex AI data-processing terms (no training on customer data, Google Cloud DPA, regional residency). Inputs are Gap-curated; outputs land in Gap's own BigQuery dataset — no extra obligation triggered beyond the existing Vertex agreement.
- Eval-run telemetry (latency, tokens, pass/fail) flows through the same OTel pipeline into the Observability Suite (AR-5/AR-6), so finance can attribute eval-run cost separately from production.
- **Future guard-rail:** if real production traffic is ever sampled into the golden set, candidate prompts must pass DLP + manual review before landing in `golden_evals`. Not in POC scope.

---

## Quick delta — what changed since some of these questions were written

| Older premise | Current architecture |
|---|---|
| Personal Confluence PAT | Read-only **SA-PAT** in Secret Manager, mounted as volume (AR-1) |
| `request_logs` / `skill_invocations` in BigQuery | **Cloud Observability Suite** (AR-5); BQ keeps product data only |
| Self-hosted MCP toolbox Cloud Run service + dedicated SA | **Decommissioned** — agent calls Google-managed BigQuery MCP via the agent SA against authorized view `v_experiment_kpis`. **5 SAs (was 6).** |
| Streamlit frontend | **React** (AR-9) |
| Custom session store | **VAIS native sessions** (AR-7) |
