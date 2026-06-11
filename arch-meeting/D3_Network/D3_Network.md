# D3 - Network Diagram (companion notes)

**File:** `arch-meeting/D3_Network/D3_Network.drawio`  
**Audience:** GCP networking, security/PSEC reviewers  
**Scope:** All L3/L4 paths in/out of project `gap-genai-discovery`

> **Update — 2026-05-25 ARB review:** the in-perimeter `Cloud Logging` tile is now the **Cloud Observability Suite** (Logging + Monitoring + Trace + Profiler + Error Reporting); log-based metrics `gap_genai/llm_tokens_in/out/calls/cost_usd` are wired to a Cloud Monitoring dashboard and Cloud Billing budget alerts (AR-5, AR-6). PSC paths and VPC-SC scope are otherwise unchanged.

## 1. Zones

1. **Internet (untrusted)** - end-users, Workspace IdP, Atlassian Confluence Cloud SaaS.
2. **Google front door (global edge, outside VPC)** - Cloud DNS, IAP (Cloud Run native).
3. **VPC `gap-genai-vpc`** - custom-mode, single subnet `gap-genai-sn-uc1` (`10.10.0.0/24`, us-central1), Private Google Access ON.
4. **VPC-SC perimeter `gap-genai-perimeter`** - red dashed; restricts the 7 protected APIs.

## 2. IP plan (single VPC, single region)

| CIDR | Purpose |
|---|---|
| `10.10.0.0/24` | Subnet `gap-genai-sn-uc1` |
| `10.10.10.0/28` | Serverless VPC Access connector `gap-genai-connector` |
| `10.10.20.0/28` | Reserved for PSC consumer endpoints (`*.p.googleapis.com`) |

## 3. Firewall rules (lowest priority number wins)

| Priority | Direction | Name | Source / Tag | Destination / Port | Action |
|---|---|---|---|---|---|
| 1000 | INGRESS | `allow-iap-tcp` | `35.235.240.0/20` | tag `iap-target` :8080/:443 | ALLOW |
| 1000 | EGRESS | `allow-vpc-connector-to-psc` | src `10.10.10.0/28` | `*.p.googleapis.com` (PSC range) :443 | ALLOW |
| 1000 | EGRESS | `allow-nat-egress` | tag `confluence-egress` | `0.0.0.0/0` :443 | ALLOW (NAT) |
| 65000 | EGRESS | `deny-internet-egress-default` | `10.10.0.0/24` | `0.0.0.0/0` | DENY |
| 65535 | INGRESS | default | any | any | DENY |

Hierarchical org policy adds: `deny-all-public-internet-egress` baseline + `allow-private-google-access`.

## 4. Private Service Connect endpoints (consumer)

PSC endpoints created in subnet for: `discoveryengine`, `aiplatform`, `bigquery` (also serves the managed BigQuery MCP server at `bigquery.googleapis.com/mcp`, same API host), `storage`, `secretmanager`, `logging`, `monitoring`. Cloud DNS private zones override `*.p.googleapis.com` to the PSC IPs (`10.10.20.x`). All API egress from Cloud Run goes via VPC connector -> PSC, never the public internet.

## 5. VPC-SC perimeter

Restricted services: `discoveryengine.googleapis.com`, `aiplatform.googleapis.com`, `bigquery.googleapis.com`, `storage.googleapis.com`, `secretmanager.googleapis.com`, `logging.googleapis.com`, `monitoring.googleapis.com`. Ingress policies allow:
- Cloud Build SA -> VPC-SC (deploy-time only).
- `gap-genai-admins` group from corporate IP ranges via Access Levels (ops/console).

Egress policies: NONE (perimeter is closed except for the explicit Confluence path through Cloud NAT, which is **not** a VPC-SC-protected service).

## 6. Cloud NAT - the only legitimate internet egress

`gap-genai-nat` attached to `gap-genai-router`, **1 manually-allocated static IP** added to the Atlassian Confluence Cloud allowlist. Only Cloud Run resources tagged `confluence-egress` (i.e. the `exporter` Job) are routed through NAT; everything else is denied by `deny-internet-egress-default`.

## 7. Request path summary

User browser HTTPS/443 -> Cloud DNS -> IAP (gap.com OIDC, Cloud Run native, managed TLS) -> Cloud Run `web` -> (VPC connector) -> Cloud Run `gateway` -> Cloud Run `agent`. Agent -> PSC -> VAIS / Vertex / BQ / GCS / Secret Manager. Exporter Job -> connector -> NAT -> Confluence Cloud.

## 8. Cross-references

- D2 physical: [D2_Physical.drawio](../D2_Physical/D2_Physical.drawio)
- DFD: [D4_DataFlow.drawio](../D4_DataFlow/D4_DataFlow.drawio)
- STRIDE: [D5_STRIDE.md](../D5_STRIDE/D5_STRIDE.md)
- Onboarding: [../Vertex_AI_Search_Variant/GCP_Services_Required.md](../../Vertex_AI_Search_Variant/GCP_Services_Required.md) section 10
