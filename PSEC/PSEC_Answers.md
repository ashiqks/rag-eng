# PSEC - Product Security Questionnaire - Proposed Answers

> **Purpose**: canonical answer sheet for the Gap PSEC Forms submission. Each answer below is paste-ready. Source citations point back to the architecture / design documents in this repo.
>
> **Project**: GenAI Knowledge Discovery POC (Experimentation Report Discoverability - ERD)
> **Submitter**: Athul Babu (Mathco) on behalf of David's team (GAP Experimentation)
> **Last updated**: 2026-05-20
>
> **STATUS**: DRAFT - 3 P0 blockers remain (Q8, Q21, Q1/Q3). See §6.

---

## 1. Basic Information

| Q | Question | Proposed answer | Source |
|---|----------|-----------------|--------|
| Q1 | Existing PSEC story # | **TBD - open a PSEC Jira before submission** (P0 blocker) | n/a |
| Q2 | Project name | GenAI Knowledge Discovery POC - Experimentation Report Discoverability (ERD) | Project_Documentation.md §1 |
| Q3 | Link to architecture documents (PDD / AAD / ATOM) | **TBD - need to either rebrand the existing design artefacts into Gap's PDD / AAD / ATOM templates, or produce three Gap-templated cover pages pointing at the existing artefacts** (P0 blocker) | `Vertex_AI_Search_Variant/Architecture.md`, `Vertex_AI_Search_Variant/GCP_Services_Required.md`, `High_Level_Design.md`, `GCP_RAG_Architecture.md`, `Project_Documentation.md` |
| Q4 | Applications / products in scope | Single application: ERD Web App + Backend (ADK Discovery Agent) on GCP Cloud Run, fronted by an External HTTPS Load Balancer with Identity-Aware Proxy. Source: Atlassian Confluence (Test and Learn COE space, read-only). | Vertex_AI_Search_Variant/Architecture.md §4 |
| Q5 | Category of request | **Architecture / POC** | (selected) |

---

## 2. Product Details

| Q | Question | Proposed answer |
|---|----------|-----------------|
| Q6 | Internally developed / Vendor-hosted / Hybrid | **Internally developed application** - we own the Web App + Backend codebase. We *consume* Gap-subscribed managed services (Vertex AI, BigQuery, Cloud Run, GCS, Secret Manager) and a Gap SaaS source (Atlassian Confluence). No third-party application is hosting our code. *(Hybrid is acceptable if PSEC reviewer prefers, but "Internally developed" is the closer match.)* |
| Q7 | Style / type of service | **PaaS + SaaS** (tick both). PaaS: Cloud Run, Vertex AI Search, Vertex AI Model Garden, BigQuery, GCS, Secret Manager, Cloud Logging. SaaS: Atlassian Confluence (source of truth, read-only). IaaS: **not used** (no Compute Engine VMs - everything is serverless). |
| Q8 | Where will the application be hosted? | **P0 BLOCKER - the form has no GCP option.** Our entire design is on GCP project `gap-genai-discovery`, region `us-central1`. **Action**: confirm with PSEC reviewer whether (a) GCP is an approved Gap-subscription hosting target and the form needs a new option, (b) we should select "**Other**" and write "GCP (Gap subscription) - project `gap-genai-discovery`, region us-central1", or (c) GCP is not approved and we must replan. **Current draft answer**: `Other -> GCP (Gap subscription) - project gap-genai-discovery, region us-central1`. |
| Q9 | Existing or new application | **New** |
| Q10 | Please explain how the application is being built | Two services on Cloud Run: (i) **Web App** (React + Vite) served via External HTTPS LB + Cloud Armor + IAP (Gap SSO); (ii) **Backend** (Python ADK Discovery Agent) reached by the Web App over Cloud Run-to-Cloud Run with IAM `run.invoker`. The Backend issues a single call per turn to **Vertex AI Search `:answer`** which performs retrieval + grounded synthesis + session append against a GCS-hosted HTML corpus. A **weekly ingest** pipeline (two Cloud Run Jobs triggered by Cloud Scheduler) pulls Confluence pages, renders to HTML in GCS, and triggers a Vertex AI Search reindex. Telemetry to Cloud Logging -> Pub/Sub -> BigQuery. Source: `Vertex_AI_Search_Variant/Architecture.md` §4-5. |
| Q11 | Are APIs involved? | **Yes** (both Gap and vendor APIs). |
| Q12 | List all of the APIs involved | See API inventory in §4 below. **Confluence REST API is a Gap API - a penetration-test request will be opened via the link on the form once the Confluence PAT is provisioned.** |
| Q13 | Will any systems or applications be replaced or deprecated? | **No.** The application augments today's manual Confluence-search workflow used by the senior analyst team but does not replace or deprecate any Gap system. Confluence remains the authoritative system of record for experiment results. |

---

## 3. Authentication and Authorization

| Q | Question | Proposed answer |
|---|----------|-----------------|
| Q14 | Does the application use Gap credentials? | **Yes, SSO** - Gap Workspace OIDC enforced by Identity-Aware Proxy (IAP) in front of the External HTTPS LB. Domain restricted to `gap.com`. |
| Q15 | What authorization controls are in place? | Three layers: (1) **edge** - IAP enforces Gap SSO + (optional) Google-Group membership check on every request; (2) **infrastructure** - GCP Cloud IAM least-privilege bindings on 4 service accounts (`sa-gateway`, `sa-agent`, `sa-exporter`, `sa-reindex`); (3) **application** - flat read access (no app-level RBAC) - any authenticated `gap.com` user can search any Confluence experiment page, because Confluence is already open to all GAP IDs and one PDM owns a site section across all four brands (validated with Prateek in Meeting 4). Two Google Groups gate elevated rights: `gap-genai-users` (read) and `gap-genai-admins` (config-write + audit-view). |
| Q16 | How will the data / application be accessed? | (1) **UI** - browser -> External HTTPS LB (TLS 1.2+) -> Web App (Cloud Run); (2) **Internal API** - Web App -> Backend over Cloud Run internal HTTPS with IAM `run.invoker`; (3) **APIs to managed services** - Backend -> Vertex AI Search `:answer`, BigQuery, Secret Manager (Google APIs over TLS, IAM-authenticated); (4) **BigQuery direct read** - the Gap analytics team has BQ Data Viewer on `gap_genai_app.*` for usage / quality dashboards. No direct DB calls from end users. |
| Q17 | Will vendors have access to any systems? | **Yes.** One vendor surface: **Mathco contractors** (5-7 named individuals) - developer access to the GCP project in **lower envs only** (`dev` + `staging`). The application makes **no app-side third-party LLM call** - retrieval and grounded synthesis happen inside Vertex AI Search `:answer`, so there is no Anthropic / OpenAI API key in the project. |
| Q18 | What systems will the vendors have access to and how? | See `PSEC/Vendor_Access.md`. Summary: Mathco devs are granted time-bound IAM roles on the `gap-genai-discovery-dev` GCP project (Cloud Run + BigQuery developer, Vertex AI user, Secret Manager viewer on dev secrets only). Access is brokered by Gap SSO; no shared accounts; **no production access**. Anthropic is reached only via Vertex Model Garden (Google-billed, IAM-only). |
| Q19 | How are users provisioned / de-provisioned? What audit controls are in place? | See `PSEC/User_Provisioning_And_Audit.md`. Summary: end-user access is governed by Google-Group membership (`gap-genai-users`, `gap-genai-admins`); group membership is managed in Gap's Workspace admin console and follows the existing joiners / movers / leavers SOP. Contractor access (Mathco) is provisioned via Gap's contractor onboarding workflow (the MFA + contractor-ID approval flow tracked as Meeting 4 A4). Audit: **Cloud Audit Logs** (Admin Activity + Data Access) sink to BigQuery `gap_genai_app.audit_logs` with 1-year retention; all IAM changes, secret accesses, BigQuery reads, and IAP sign-in events are captured. |
| Q20 | Who are the users that will have access? | 4 validated personas plus internal team: (1) **Senior Analyst** - Gap Experimentation team (Prateek's group); (2) **PDM** - Product Discovery Manager covering a site section across all four brands; (3) **Brand Manager** - per-brand partner; (4) **Leadership** - read-only consumer of dashboards. Internal: Gap Experimentation engineering, Gap analytics team (BigQuery dashboards), `gap-genai-admins` group (3-5 named SREs / engineers). Mathco contractors only in lower envs. |
| Q21 | Will the application store secrets or certificates in Vault? | **P0 BLOCKER.** Our design stores secrets in **GCP Secret Manager** (Confluence PAT only - the Backend has no secrets; managed-service calls are IAM-authenticated). **Action**: confirm with PSEC reviewer whether HashiCorp Vault is mandatory at Gap or whether GCP Secret Manager is an accepted equivalent. **Current draft answer**: `Yes - secrets are stored in GCP Secret Manager (Gap-subscribed managed equivalent of Vault). The only secret today is the Confluence read-only PAT. TLS certificates for the external LB are managed by Certificate Manager.` |

---

## 4. Network

| Q | Question | Proposed answer |
|---|----------|-----------------|
| Q22 | Does the application have a mobile interface? | **No.** Web-only (responsive layout, but no native mobile app). |
| Q23 | Please explain the data flow (inbound and outbound communications) - ports and protocols | See the table in §5 below. All flows are TLS 1.2+. No port other than 443 is used end-to-end. |
| Q24 | Will the users be accessing the application from the Internet or a non-Gap Network? | **Yes.** Although the application is gated by Gap SSO at the edge (Identity-Aware Proxy), the External HTTPS Load Balancer is Internet-reachable so that Gap analysts can access from home / VPN / mobile carrier. Cloud Armor enforces WAF + geo-fence (US-only ingress); IAP enforces `gap.com` SSO + Google-Group membership before any byte reaches the Web App. **No public anonymous access.** |
| Q25 | Who has access to the data repositories? | (1) **GCS `gap-genai-discovery-corpus-html`** - write: `sa-exporter`; read: VAIS service agent + `sa-reindex`; no human read access. (2) **BigQuery `gap_genai_app`** - write: `sa-agent`, `sa-gateway` (logs/feedback only via fixed schema); read: Gap analytics team (Data Viewer on selected tables), `gap-genai-admins`. (3) **BigQuery `gap_genai_app.audit_logs`** - read: `gap-genai-admins` only. (4) **Vertex AI Search index** - admin: `sa-reindex`; query: `sa-agent`; no direct human access. (5) **Secret Manager** - read: `sa-exporter` (Confluence PAT only); no human read access. Mathco contractors: read access in **dev / staging only**. |
| Q26 | Will there be any use of non-encrypted network protocols? | **No.** Every hop is TLS 1.2+ (Cloud Run HTTPS endpoints, IAP, Confluence HTTPS, Vertex AI / BigQuery / Secret Manager / GCS over TLS, Cloud Logging over TLS). |
| Q27 | If yes, explain why the application will use non-encrypted protocols | N/A (Q26 = No). |
| Q27b | What region(s) will users be accessing the application from? | **North America** only (Gap analytics population is US-based; Cloud Armor enforces a US-only geo-fence). |

---

## 5. Data flow table (answer to Q23)

| # | Source | Destination | Protocol / Port | Direction | Auth |
|---|--------|-------------|-----------------|-----------|------|
| 1 | End-user browser | External HTTPS LB | TLS 1.2+ / 443 | Inbound (Internet) | Cloud Armor WAF + IAP enforces Gap SSO (Workspace OIDC) |
| 2 | LB | Web App (Cloud Run) | HTTPS / 443 | Internal (Google-managed) | Serverless NEG + IAP-injected user identity header |
| 3 | Web App (Cloud Run) | Backend (Cloud Run) | HTTPS / 443 | Internal Cloud Run | IAM `run.invoker` (sa-gateway) |
| 4 | Backend | Vertex AI Search (`discoveryengine.googleapis.com`) | gRPC over TLS / 443 | Outbound to Google APIs | IAM SA (`sa-agent`) |
| 5 | Backend | BigQuery `gap_genai_app` (`bigquery.googleapis.com`) | HTTPS / 443 | Outbound to Google APIs | IAM SA (`sa-agent`, `sa-gateway`) |
| 7 | Confluence Exporter Job | Atlassian Confluence REST | HTTPS / 443 | Outbound to Gap-corp Atlassian | Confluence PAT (from Secret Manager) over Basic Auth header |
| 8 | Confluence Exporter Job | GCS `gap-genai-discovery-corpus-html` | HTTPS / 443 | Outbound to Google APIs | IAM SA (`sa-exporter`) |
| 9 | Reindex Trigger Job | Vertex AI Search admin (`discoveryengine.googleapis.com`) | HTTPS / 443 | Outbound to Google APIs | IAM SA (`sa-reindex`) |
| 10 | All services | Cloud Logging (`logging.googleapis.com`) | HTTPS / 443 | Outbound to Google APIs | IAM SA (per-service) |
| 11 | Cloud Logging sink | Pub/Sub topic -> BigQuery `request_logs` | Internal (Google-managed) | Internal | Google-managed service agent |
| 12 | Cloud Audit Logs | BigQuery `gap_genai_app.audit_logs` | Internal (Google-managed) | Internal | Google-managed service agent |

**No port other than 443 is opened.** No SFTP, no JDBC, no SMTP, no inbound Internet to any service other than the LB.

---

## 6. P0 blockers - questions to send back to Gap PSEC reviewer

| # | Question to ask | Why it matters |
|---|------------------|----------------|
| B1 | Is GCP an approved hosting target at Gap? (Q8 has no GCP option) | Could invalidate the entire architecture; we are GCP-only. |
| B2 | Does "Vault" in Q21 accept GCP Secret Manager as equivalent? | If Vault is mandatory we must add HashiCorp Vault + CSI/sidecar integration to the design. |
| B3 | Is IAP-gated External HTTPS LB considered "Internet-accessible" for Q24? | Determines Q24 answer and may trigger additional pen-test scope. |
| B4 | Does the Confluence pen-test request linked in Q12 apply when we only **read** via PAT? | Determines whether ingest is gated on a pen-test. |
| B5 | Hybrid vs Internally-developed (Q6) - does the classification route the review differently? | Drives the answer to Q6. |
| B6 | Is there a Section 5 (Data) part of the questionnaire? Can we preview the questions so we can pre-stage answers (data classification, PII, retention, encryption-at-rest, CMEK)? | Avoids second review cycle. |
| B7 | What is the PSEC SLA from submission to approval, and what artefacts (PDD/AAD/ATOM) are strictly required for "Architecture/POC" category vs optional? | Drives Q3 effort estimate. |

---

## 7. Already correct (no change needed)

- Q5 Architecture / POC (selection correct)
- Q9 New application (selection correct)
- Q14 Yes, SSO (selection correct)
- Q22 No mobile interface (selection correct)
- Q13 No deprecation (selection correct)
- Q27b North America (selection correct)

---

## 8. References

- `Vertex_AI_Search_Variant/Architecture.md` - retrieval + synthesis + sessions design
- `Vertex_AI_Search_Variant/GCP_Services_Required.md` - full service catalog
- `Vertex_AI_Search_Variant/Backend_Developer_Guide.md` §8 (Secret Manager), §10 (IAM)
- `Vertex_AI_Search_Variant/Architecture.md` §6 (ports + data flow)
- `PSEC/Vendor_Access.md` - Q17/18 detail
- `PSEC/User_Provisioning_And_Audit.md` - Q19 detail
- `Meeting 4/Meeting_Details.md` §9 - ACL/governance validation with Prateek
