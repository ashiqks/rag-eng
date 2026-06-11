# User Provisioning and Audit (PSEC Q19 / Q20)

> **Purpose**: answer the PSEC question on how users are provisioned / de-provisioned and what audit controls are in place.
> **Scope**: end users (gap.com employees) and admins. Vendor / contractor lifecycle is in `Vendor_Access.md`.

---

## 1. Identity model

| Layer | Provider | Used for |
|-------|----------|----------|
| Authentication | **Gap Google Workspace** (gap.com OIDC) | Establishing the user identity at the edge |
| Edge enforcement | **Identity-Aware Proxy (IAP)** on the External HTTPS LB | Allow / deny gap.com sign-in, inject identity headers, enforce Google-Group membership |
| Application authorization | **Google Groups** + GCP Cloud IAM | Grant access to the Web App, to BigQuery dashboards, to admin endpoints |
| Audit | **Cloud Audit Logs** + **IAP request logs** + **request_logs** in BigQuery | Capture every sign-in, every admin action, every data access |

There is **no application-level user table** and **no application-level role table**. Identity, group membership, and IAM bindings are the sole source of truth. (Validated with Prateek in Meeting 4 §9 - Confluence is open to any GAP ID and no app-level RBAC is desired.)

---

## 2. User population (PSEC Q20)

| Group | Members | Granted role | What they can do |
|-------|---------|--------------|------------------|
| `gap-genai-users@gap.com` | All gap.com users invited to the POC (5-20 pilot users) | IAP -> Web App access | Search experiments, view results cards, ask the AI bot, submit feedback |
| `gap-genai-admins@gap.com` | 3-5 named SREs / engineers (Mathco tech lead + Gap engineering owners) | IAP + GCP `roles/run.admin`, `roles/bigquery.dataViewer` on audit dataset, `roles/secretmanager.admin` (prod only via break-glass) | Toggle skills in the registry, re-run ingest, edit prompt config in BigQuery `app_config`, view audit logs |
| `gap-genai-analytics-viewers@gap.com` | Gap analytics team | `roles/bigquery.dataViewer` on `gap_genai_app.*` non-audit tables | Build usage / quality / cost dashboards in Looker |
| `gap-erd-vendor-*` (lower envs only) | Mathco contractors | See `Vendor_Access.md` §2.3 | Build the application in `dev` / `staging` |

### 2.1 Persona to group mapping

| Persona (per Meeting 1-4) | Google Group |
|---------------------------|--------------|
| Senior Analyst (Prateek, David's team) | `gap-genai-users@gap.com` (some also in `gap-genai-admins@gap.com` for config edits) |
| PDM (Product Discovery Manager) | `gap-genai-users@gap.com` |
| Brand Manager (per brand) | `gap-genai-users@gap.com` |
| Leadership | `gap-genai-users@gap.com` |
| Gap analytics team (David) | `gap-genai-users@gap.com` + `gap-genai-analytics-viewers@gap.com` |
| Mathco contractors | `gap-erd-vendor-*` (lower envs) - **not** in `gap-genai-users` |

---

## 3. Provisioning (joiner)

1. **Sponsor request**: a Gap manager opens a ticket in the same internal access-request system used for any other Workspace group.
2. **Approval**: ticket is routed to the application owner (David's team for `gap-genai-users`; SRE on-call for `gap-genai-admins`).
3. **Group add**: approver adds the user to the relevant Google Group in Gap Workspace admin.
4. **Effect**:
   - For `gap-genai-users`: next sign-in passes IAP -> reaches the Web App immediately (group membership is cached for at most 5 minutes by IAP).
   - For `gap-genai-admins` and `gap-genai-analytics-viewers`: Terraform-managed IAM bindings are already wired to the group, so adding the user grants the role at the next Workspace propagation (typically within minutes).
5. **No application change required** - we never INSERT a user row anywhere. The group is the row.

---

## 4. Moves (mover)

When a user changes role:

- The sponsor removes them from the old group and adds them to the new group via the same Workspace request.
- IAP re-evaluates group membership on the next sign-in.
- Cloud IAM updates within minutes via Workspace -> IAM propagation.

There are no application-side roles to update.

---

## 5. De-provisioning (leaver)

| Scenario | Effect | Mediated by |
|----------|--------|-------------|
| Employee leaves Gap | Gap leaver flow disables the Workspace account -> IAP rejects all further sign-ins immediately; group membership is also removed | Gap HR + IT |
| Employee changes role and no longer needs the tool | Sponsor removes from group; IAP rejects on next sign-in | Workspace admin |
| Suspicious activity | SRE on-call removes from group; if account-level compromise, SRE escalates to IT to disable Workspace account | `gap-genai-admins` runbook |
| Group disbanded / project sunset | Terraform deletes the group; IAM bindings vanish at next apply | Terraform |

> **Worst-case latency from leaver event to access revocation**: under 5 minutes for IAP-gated UI access; under 1 business day for IAM-gated BigQuery / admin actions (Terraform reconcile window). Emergency revocation is < 5 minutes via manual `gcloud iam groups members remove` plus IAP group cache clear.

---

## 6. Audit controls

### 6.1 What is captured

| Event class | Sink | Retention |
|-------------|------|-----------|
| Every Web App sign-in (gap.com identity, IAP decision, source IP) | IAP request log -> Cloud Logging -> BigQuery `gap_genai_app.iap_logs` | 1 year |
| Every API call (chat, feedback, list-sessions, delete-session) | Application telemetry -> Cloud Logging -> Pub/Sub -> BigQuery `gap_genai_app.request_logs` | 1 year |
| Every IAM change (binding add / remove / role change) | Cloud Audit Logs - Admin Activity -> BigQuery `gap_genai_app.audit_logs` | 1 year (Admin Activity logs are kept 400 days by Cloud Logging by default) |
| Every Secret Manager read | Cloud Audit Logs - Data Access -> same | 1 year |
| Every BigQuery `gap_genai_app.*` SELECT / INSERT | Cloud Audit Logs - Data Access -> same | 1 year |
| Every GCS object access on the corpus bucket | Cloud Audit Logs - Data Access -> same | 1 year |
| Every Vertex AI Search admin action (datastore import, engine update) | Cloud Audit Logs -> same | 1 year |
| Skill registry edits | Application emits a `skill_registry_changed` event -> Cloud Logging | 1 year |

### 6.2 Who can read the audit data

- `gap-genai-admins@gap.com` has `roles/bigquery.dataViewer` on `gap_genai_app.audit_logs`, `iap_logs`, and the audit views.
- `gap-genai-users@gap.com` cannot read any audit table.
- A monthly export of `audit_logs` is shared with the Gap GRC team via a Looker dashboard (read-only).

### 6.3 Alerts

| Alert | Condition | Channel |
|-------|-----------|---------|
| Unexpected IAM role grant | New binding on `gap-genai-discovery-prod` outside change-window | PagerDuty -> SRE on-call |
| Secret Manager read by an unexpected SA | Any SA other than `sa-exporter` reads `confluence-pat-prod` | PagerDuty |
| BQ dataset access by a non-allowlisted principal | Cloud Audit Logs filter on `gap_genai_app.*` reads | Slack #gap-genai-secops |
| IAP sign-in denied (rate-limit) | More than 50 denies / minute from a single source IP | Slack #gap-genai-secops |
| Vertex AI datastore deleted | Cloud Audit Log event | PagerDuty (P1) |

---

## 7. Joiner / Mover / Leaver SLA

| Action | Target latency |
|--------|----------------|
| Add a new pilot user (joiner) | 1 business day from sponsor approval |
| Role change (mover) | < 5 min (IAP re-evaluation on next sign-in) for UI; < 1 business day for IAM roles |
| Off-board on Gap leaver event | < 5 min IAP enforcement (Workspace disable propagates immediately); IAM revocation within 1 business day |
| Emergency revocation | < 5 min via SRE runbook |

---

## 8. Open items

- [ ] Confirm the existing Gap access-request system can be wired to gate `gap-genai-users` membership directly, or whether a Forms / ServiceNow shim is needed.
- [ ] Define the break-glass procedure for `gap-genai-admins` actions on `-prod` (current proposal: Just-in-time IAM via PAM workflow).
- [ ] Onboard the GRC Looker dashboard before pilot launch.
