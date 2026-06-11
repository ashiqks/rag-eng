# Architecture Review Meeting - Diagrams to Produce

> **Meeting**: AI Architect review (Biswajeet Mishra) - 2026-05-20
> **Source**: screenshots in this folder (`Screenshot 2026-05-20 *.png`)
> **Status**: stub - parked for follow-up work after the dashboard-data-agent direction is locked.

---

## 1. Meeting context (short)

Biswajeet covered two threads:

### 1.1 Re-affirmation of the VAIS + ADK approach (no action; we already match this)

- Use the **Google-managed Vertex AI Search index** as the base; do **not** hand-roll the chunk -> embed -> index pipeline. *"That vector store remains same, that vector index remains same... that is the most complex part. Don''t build that pipeline, give it to Google to do the job."*
- On top of the managed index, build an **ADK agent** whose **skills** do the RAG customisation. *"Rather than writing a full-fledged RAG agent that has a separate retrieval module, generation module, an augmentation module... use agent skills to do the job."*
- Only recreate a managed module yourself if it fails - and even then, expose it as an ADK skill, not a parallel pipeline.
- Run end-to-end through Google''s stack first; tune later only if the **golden eval set** says retrieval accuracy is below target.
- Maintain a **golden evaluation dataset**: question + thought-process + source document(s) + correct answer + reason. **Sign-off from end users / client stakeholders is non-negotiable** - if 1000 questions, then 1000 reviewed answers. Same sign-off rigour as the architecture itself.
- Summary line: *"Googlify all the services that you guys are using... ensure that you''re using as many Google services to get this done as possible."*

> **No architectural change required** - this is exactly the variant locked in [../Vertex_AI_Search_Variant/](../Vertex_AI_Search_Variant/). Recorded here only so the meeting is on the record.

### 1.2 Diagrams still owed beyond the HLD

Biswajeet flagged that we have the **HLD** covered but the package is incomplete for client review / PSEC sign-off. We owe the four diagrams + one document listed below.

---

## 2. Diagrams to produce (list)

| # | Artefact | What it shows | Notes from the meeting | Status |
|---|---|---|---|---|
| D1 | **High-Level Design (HLD)** | Logical components, request flow, user-visible boundaries | Already done - see [../High_Level_Design.md](../High_Level_Design.md) + [../High_Level_Design.drawio](../High_Level_Design.drawio) + [../GCP_RAG_Architecture.drawio](../GCP_RAG_Architecture.drawio) | DONE |
| D2 | **Physical diagram** | *"What is the project, what is the region of this project, what is the service that I am using, what services within that service I am using"* - shows project / region / each GCP service (e.g. Vertex AI = AI Platform, with the specific sub-service like Search index) and how services are **physically wired** | Per-service GCP resource ID, region (`us-central1`), VPC, project (`gap-genai-discovery`); connectors with direction. Base list lives in [../Vertex_AI_Search_Variant/GCP_Services_Required.md](../Vertex_AI_Search_Variant/GCP_Services_Required.md). Output: [D2_Physical.drawio](D2_Physical/D2_Physical.drawio) + [D2_Physical.md](D2_Physical/D2_Physical.md) + [D2_Physical.d2](D2_Physical/D2_Physical.d2) + [D2_Physical.svg](D2_Physical/D2_Physical.svg) (ELK auto-layout). | DONE |
| D3 | **Network diagram** | Subnets, VPC, ingress/egress paths, IAP gate, Private Service Connect / `googleapis` PSC | *"Even that you are on Google, you are using everything within Google. There is no external stuff happening, but it is a good idea to create a network diagram."* PSEC Q23 ports/protocols already enumerated in [../Vertex_AI_Search_Variant/Architecture.md](../Vertex_AI_Search_Variant/Architecture.md) section 6. Output: [D3_Network.drawio](D3_Network/D3_Network.drawio) + [D3_Network.md](D3_Network/D3_Network.md) + [D3_Network.d2](D3_Network/D3_Network.d2) + [D3_Network.svg](D3_Network/D3_Network.svg) (ELK auto-layout). | DONE |
| D4 | **Data-flow diagram (DFD)** | What integration moves between which services - Confluence -> Exporter -> GCS -> VAIS, /chat -> agent -> VAIS `:answer`, agent -> managed BigQuery MCP (`bigquery.googleapis.com/mcp`) -> view `v_experiment_kpis` | *"You will have to write a pipeline that gets the data from Confluence, puts it on the GCS, right? And then GCS, VAIS runs, does the job for you."* Flows already enumerated in [../Vertex_AI_Search_Variant/Architecture.md](../Vertex_AI_Search_Variant/Architecture.md) section 5. Output: [D4_DataFlow.drawio](D4_DataFlow/D4_DataFlow.drawio) + [D4_DataFlow.md](D4_DataFlow/D4_DataFlow.md) + [D4_DataFlow.d2](D4_DataFlow/D4_DataFlow.d2) + [D4_DataFlow.svg](D4_DataFlow/D4_DataFlow.svg) (ELK auto-layout). | DONE |
| D5 | **STRIDE security document** | Per-asset threat model: Spoofing / Tampering / Repudiation / Information disclosure / DoS / Elevation of privilege; risks + mitigations | *"Diagram that shows how your systems are secured, and what kind of risks can happen, and how you are mitigating those risks - which is normally called a STRIDE document."* Building blocks in [../PSEC/](../PSEC/). Output: [D5_STRIDE.md](D5_STRIDE/D5_STRIDE.md) + [D5_STRIDE.drawio](D5_STRIDE/D5_STRIDE.drawio) + [D5_STRIDE.d2](D5_STRIDE/D5_STRIDE.d2) + [D5_STRIDE.svg](D5_STRIDE/D5_STRIDE.svg) (ELK auto-layout). | DONE |

Biswajeet''s priority hint at 17:19: *"I would suggest focus on the high-level diagram, physical and network diagram, and then if there is any data-flow diagram is also needed."*

Suggested order: **D2 (Physical) -> D3 (Network) -> D4 (DFD) -> D5 (STRIDE)**.

---

## 3. Input material we already have (no need to re-research)

| Diagram | Source material in repo |
|---|---|
| D2 Physical | [../Vertex_AI_Search_Variant/GCP_Services_Required.md](../Vertex_AI_Search_Variant/GCP_Services_Required.md) |
| D3 Network | [../Vertex_AI_Search_Variant/Architecture.md](../Vertex_AI_Search_Variant/Architecture.md) section 6 |
| D4 DFD | [../Vertex_AI_Search_Variant/Architecture.md](../Vertex_AI_Search_Variant/Architecture.md) section 5; [../Vertex_AI_Search_Variant/Multi_Session_Flow.md](../Vertex_AI_Search_Variant/Multi_Session_Flow.md) |
| D5 STRIDE | [../PSEC/PSEC_Answers.md](../PSEC/PSEC_Answers.md), [../PSEC/Vendor_Access.md](../PSEC/Vendor_Access.md), [../PSEC/User_Provisioning_And_Audit.md](../PSEC/User_Provisioning_And_Audit.md) |

---

## 4. Open thread - dashboard-data agent (point 1)

The pitch Figma (`Recent Experiments` / `Experiment Performance Overview`) shows aggregate KPI tiles + per-experiment cards driven by a search box like *"what are the experiments for Banana Republic"* with filters such as **Time Range (3M / 6M / 9M / 12M)**.

KPIs visible: `Total Experiments Run`, `Completed Experiments`, `Successful Experiments`, `Active Experiments`, `Avg Conversion Lift`, `Total Revenue Impact`, `Avg AOV Lift`, `UPT Lift`, `Total Category Sales Impact`; per-card `Category / Stores / Region / Duration / Conversion Lift / Revenue Lift / AOV Lift / Confidence / Success badge`.

These are **structured aggregates**, not free-text answers. Confluence test reports are the narrative source but not queryable in aggregate. We consume a structured DB owned by another team (new tables `gap_genai_app.experiments` + `gap_genai_app.experiment_clusters`) via an **ADK skill served by the Google-managed BigQuery MCP server** (`bigquery.googleapis.com/mcp`) against the authorized view `v_experiment_kpis`. Pipeline / ingestion is **out of scope** for this solution. Direction locked - see [../Vertex_AI_Search_Variant/Architecture.md](../Vertex_AI_Search_Variant/Architecture.md) "Dashboard Data Agent + MCP integration" section.

---

*Source: `arch-meeting/Screenshot 2026-05-20 17xxxx.png` (18 screenshots).*
