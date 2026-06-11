# Vendor Access (PSEC Q17 / Q18)

> **Purpose**: enumerate every non-Gap human or system that touches the ERD GenAI POC, the scope of their access, and the lifecycle controls.
> **Scope**: this document only covers vendor / contractor access. End-user (gap.com) access is in `User_Provisioning_And_Audit.md`.

---

## 1. Vendor surfaces

| # | Vendor | Type | What they access | How they access | Production access? |
|---|--------|------|------------------|-----------------|--------------------|
| V1 | **Mathco** (consulting partner) | Human contractors | GCP project `gap-genai-discovery-dev` and `-staging`; GitHub repo `gap-erd-genai`; Confluence (read-only via Gap-issued PAT during onboarding); Jira PSEC story | Gap-issued contractor ID + Gap SSO (gap.com Workspace) + MFA on every login | **No** - lower envs only |
| V2 | **Google LLC** | Managed cloud platform | All managed services in the project (Vertex AI Search, BigQuery, Cloud Run, GCS, etc.) | Google internal - no human-readable access path; controls per Google's standard cloud DPA + Gap's existing GCP subscription | n/a (platform provider) |
| V3 | **Atlassian** (Confluence) | Existing Gap SaaS source | Confluence Cloud / DC - already a Gap subscription, governed by existing Gap-Atlassian agreement | n/a - we *consume* Confluence via Gap-issued PAT; we do not grant Atlassian any access to our project | n/a (read source only) |

> **No third-party application is hosted inside our project. No vendor receives an exported corpus.** All data stays inside the Gap GCP tenant. **No app-side third-party LLM call**: retrieval and grounded synthesis happen entirely inside Vertex AI Search `:answer`, so there is no Anthropic / OpenAI integration to disclose.

---

## 2. Mathco contractor access (V1) - detail

### 2.1 Named individuals

| Name | Role | GCP project access | Confluence access | Status (as of 2026-05-20) |
|------|------|--------------------|-------------------|----------------------------|
| Athul Babu | Tech lead | `dev`, `staging` - all roles in §2.3 | Read-only via PAT | **MFA pending** (Meeting 4 A4) |
| Kaushik B | Architect | `dev`, `staging` - all roles in §2.3 | Read-only via PAT | **MFA pending** |
| Sowmiya S | UX / FE | `dev`, `staging` - FE-only roles | None | **MFA pending** |
| Nilim Borah | Data engineer | `dev`, `staging` - ingest-only roles | Read-only via PAT | **MFA pending** |
| (others) | TBD | TBD | TBD | TBD |

> The full list will be reconciled with the names David sent for contractor-ID approval. Each new contractor must be added to this table before access is granted.

### 2.2 Onboarding flow (joiner)

1. Gap sponsor (David) opens a contractor-ID request in Gap's onboarding system.
2. Contractor receives Gap email + MFA enrollment instructions.
3. Sponsor adds the contractor to the appropriate Google Group(s) (see §2.3).
4. Group membership grants IAM roles automatically via Terraform-managed bindings.
5. PSEC story is updated with the new name (this table).

### 2.3 IAM groups + roles (least-privilege)

| Google Group | Members | GCP roles bound on `gap-genai-discovery-dev` + `-staging` | Confluence | Production |
|--------------|---------|-----------------------------------------------------------|------------|------------|
| `gap-erd-vendor-dev-fullstack@gap.com` | Tech lead, architect | `roles/run.developer`, `roles/aiplatform.user`, `roles/discoveryengine.editor`, `roles/bigquery.dataEditor` (on `gap_genai_app` dev only), `roles/storage.objectAdmin` (corpus bucket dev only), `roles/secretmanager.viewer` (dev secrets only), `roles/logging.viewer` | Read-only PAT for FY25/26 test corpus | **Denied** |
| `gap-erd-vendor-dev-frontend@gap.com` | FE developer(s) | `roles/run.developer` (web service only), `roles/logging.viewer` | None | **Denied** |
| `gap-erd-vendor-dev-data@gap.com` | Data engineer(s) | `roles/aiplatform.user`, `roles/discoveryengine.editor`, `roles/bigquery.dataEditor` (corpus dataset dev only), `roles/storage.objectAdmin` (corpus bucket dev only), `roles/secretmanager.viewer` (dev secrets only), `roles/logging.viewer` | Read-only PAT | **Denied** |

> **Explicit deny**: a project-level `iam.deny` policy blocks every group above from `roles/owner`, `roles/editor`, `roles/iam.securityAdmin`, and from any role on the `gap-genai-discovery-prod` project. The deny is enforced at the org-policy level so an accidental binding cannot escalate.

### 2.4 Confluence PAT scope

- The PAT is issued against a **Gap service account** owned by the Experimentation Team, not against an individual contractor.
- Scope: **read-only**, restricted to the Test and Learn COE space.
- Stored only in **GCP Secret Manager** (`projects/gap-genai-discovery-dev/secrets/confluence-pat-dev`); never on a contractor laptop.
- Rotated every 90 days by the Gap admin who owns the service account (manual today, automation in Phase 2).
- Production PAT lives only in `-prod` secrets and is **not** accessible to any Mathco group.

### 2.5 Audit

Every contractor action is captured by:

| Surface | What is captured | Sink |
|---------|------------------|------|
| Cloud Audit Logs (Admin Activity) | IAM grants, IAM revokes, project-level config changes | BigQuery `gap_genai_app.audit_logs` (1-year retention) |
| Cloud Audit Logs (Data Access) | BigQuery reads, Secret Manager accesses, GCS reads | Same |
| IAP request logs | Every gap.com sign-in via the Web App | Cloud Logging + BigQuery `request_logs` |
| GitHub Audit Log | Repo clone, push, branch protection bypass | GitHub org audit log, retained per Gap GitHub policy |
| Atlassian audit | Confluence PAT usage | Atlassian admin console |

### 2.6 Off-boarding flow (leaver)

1. Sponsor removes the contractor from every `gap-erd-vendor-*` Google Group.
2. Terraform-managed IAM bindings are revoked at the next plan/apply (max 1 business day, or immediately via emergency runbook).
3. Contractor's Gap SSO is disabled via the standard Gap leaver flow - this severs IAP access immediately.
4. PAT remains untouched (it is service-account-owned, not contractor-owned).
5. PSEC story is updated; this table marks the contractor as `OFFBOARDED <date>`.

---

## 3. Open items (as of 2026-05-20)

- [ ] **A4 from Meeting 4**: MFA / contractor-ID approvals still outstanding for all Mathco contractors. Owner: Prateek to chase Dave.
- [ ] Confirm final Mathco roster (Sponsor: David).
- [ ] Decide on automated PAT rotation (Phase 2).
- [ ] Confirm whether Atlassian-side audit must also sink to BigQuery, or whether the Atlassian admin console is sufficient for Gap audit policy.
