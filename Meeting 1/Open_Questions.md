# Open Questions & Clarifications

> **Purpose**: A consolidated list of clarifications, ambiguities, and questions surfaced from the April 28, 2026 walkthrough. Some are for the **customer** (kickoff and beyond), some are for **internal alignment**, and some are **doubts I have** while reading the transcript that may be worth validating.
>
> **Use this list to drive the kickoff agenda and the first 2 weeks of working sessions.**

---

## 1. Questions for the Customer (Kickoff — David, Pratik, Aravindhan)

### 1.1 Scope & Outcome

| # | Question | Why It Matters |
|---|----------|---------------|
| 1.1.1 | Do you confirm Phase 1 = **discoverability + summarization + Level 1 insights** only, with forward-looking recommendations explicitly Phase 2? | Anchors the "wow factor" boundary; avoids scope creep |
| 1.1.2 | Are we scoping ingestion to **FY25/26 confluences (~500)** initially, with a path to all 1,500 once the pipeline is stable? | Aditya wasn't part of the scope conversation; need explicit confirmation |
| 1.1.3 | What does "success" look like for V1 in September? Specific KPIs (e.g., # confluences ingested, # personas live, query latency, accuracy benchmark)? | We don't have an exit-criteria definition |
| 1.1.4 | Is **post-scaling tracking** (whether wins held at scale) something you'd like in Phase 2? Should we instrument now to enable it later? | Syed proactively raised this; David hadn't fully thought about it |
| 1.1.5 | Do you want **store tests** and **customer tests** included in Phase 1, or is digital-only acceptable? | Aditya said "100% of our work was digital"; store/customer tests are recent and less organized |

### 1.2 Personas & UX

| # | Question | Why It Matters |
|---|----------|---------------|
| 1.2.1 | Persona-aware landing: do executives (Aravindhan, VPs, SVPs) get a **dashboard-first** view and analysts/PDMs get **chatbot-first**? | Drives entire UX design |
| 1.2.2 | Who exactly will have access? David's team only, or also PDMs, brand managers, leadership across orgs? | Drives auth/RBAC complexity |
| 1.2.3 | Do you want **role-based filtering** of content (e.g., should an executive see test-level details or only summaries)? | RBAC scope |
| 1.2.4 | Will users authenticate via **GAP SSO / Ping**? Are there any group/role mappings we need? | Implementation detail |

### 1.3 Insights & Recommendations Boundary

| # | Question | Why It Matters |
|---|----------|---------------|
| 1.3.1 | Confirm the boundary: chatbot will summarize past tests and provide **historical pattern insights** (e.g., "5 similar tests, 4 won"), but will NOT recommend novel tests for ideas not yet documented? | Prevent expectation mismatch |
| 1.3.2 | Are you OK with the chatbot saying "I don't have enough context to answer that" rather than guessing? | Sets quality bar |
| 1.3.3 | What level of citation is required? Link only? Link + relevant excerpt? Link + page anchor? | Implementation detail |

### 1.4 Data & Sources

| # | Question | Why It Matters |
|---|----------|---------------|
| 1.4.1 | **Image content in Confluence**: confirmed out of Phase 1 — but how often do critical findings live ONLY in images/screenshots? Could be a hidden gap. | Quality risk; may require stretch effort |
| 1.4.2 | Are there **embedded videos** in Confluence (one example seen)? Out of scope for V1? | Confirm |
| 1.4.3 | Are there Confluence pages **attached or linked** that must also be ingested (PDFs, decks, etc.)? | Crawler scope |
| 1.4.4 | Do you want the **SharePoint metadata** ingested in addition to Confluence (since it has structured fields like `Recommendation Adopted`, `Estimated Annualized Value`, etc.)? | These structured fields are higher signal than free text |
| 1.4.5 | What is the **freshness requirement** — daily / weekly / on-demand re-ingestion as new Confluence pages get written? | Pipeline design |
| 1.4.6 | When an analyst writes a **new** Confluence page, do they tag it consistently? Are there templates we can rely on? | Affects parsing reliability |
| 1.4.7 | Is the SharePoint list authoritative, or is Confluence authoritative when they disagree? | Conflict resolution rule |

### 1.5 Technology & Hosting

| # | Question | Why It Matters |
|---|----------|---------------|
| 1.5.1 | GCP is mandated for data — what about **app hosting**? GKE? Cloud Run? App Engine? Is Vertex AI the expected LLM backbone? | Architecture decision |
| 1.5.2 | Has a **GCP project** been provisioned for this work? Who is the project admin? | Critical access path |
| 1.5.3 | When does the **Google Enterprise / Gemini license** become available? (Aditya: 6–7 months out.) Should our LLM choice anticipate this? | LLM provider decision |
| 1.5.4 | In the interim, can we use **Vertex AI Gemini** or **OpenAI via Azure/etc.**? What's GAP's data egress / vendor approval policy? | Compliance + LLM choice |
| 1.5.5 | What is GAP's policy on storing PII / customer data in vector embeddings? Are Confluence reports considered confidential data? | Security design |
| 1.5.6 | Is **GAP GPT** (recently released) something we can leverage, or is it for other use cases? | Tooling option |

### 1.6 Operational

| # | Question | Why It Matters |
|---|----------|---------------|
| 1.6.1 | Who is the **product owner** on the customer side day-to-day? David himself, Pratik, or an analyst? | Working session cadence |
| 1.6.2 | Cadence for working sessions / standups / showcases? | Project rhythm |
| 1.6.3 | Are there any **compliance reviews** (security, privacy, IT architecture review board) we must pass before go-live? | Hidden timeline cost |
| 1.6.4 | What happens to the existing **Power BI dashboard** at V1 launch — sunset, run in parallel, or decommission later? | Rollout plan |
| 1.6.5 | What is the **deprecation plan for the SharePoint list** — keep as the metadata source, or replace? | Source-of-truth question |
| 1.6.6 | Would David like a **change-management plan** to onboard analysts/PDMs to the new chatbot? | Adoption risk |

### 1.7 Pain-Point Validation

| # | Question | Why It Matters |
|---|----------|---------------|
| 1.7.1 | **Do duplicate experiments actually happen?** Aditya wasn't sure. If they do, this is a strong demo angle. | Validate pain point #4 |
| 1.7.2 | What's a **realistic "wow" demo scenario** — e.g., "PDM types 'I'm thinking of testing X' and the bot returns 3 prior similar tests"? | Demo design |
| 1.7.3 | What's the **frequency of leadership asks** (Aravindhan asking David "what's working")? Daily, weekly, monthly? | Sets latency / freshness bar |

### 1.8 Phase 2 / Stretch

| # | Question | Why It Matters |
|---|----------|---------------|
| 1.8.1 | If we deliver early on Phase 1, would you fund a **Phase 1.5** to add image extraction? | Internal stretch goal alignment |
| 1.8.2 | For Phase 2 (forward-looking recommendations), is there a desired **input format** — free-text idea, structured form, integration with the existing SharePoint test-creation flow? | Pre-design Phase 2 |
| 1.8.3 | Do you imagine the bot ever being **embedded in Confluence directly** as a sidebar, vs. a standalone web app? | Channel future |

---

## 2. Internal Mathco Alignment Questions

### 2.1 Scope & SOW

| # | Question | Owner |
|---|----------|-------|
| 2.1.1 | The Figma mockup is "inspirational only" — is anyone on the customer side treating it as committed scope? Need to confirm with David. | Aditya / Syed |
| 2.1.2 | If we deliver image extraction as a stretch (GCS → LLM scan), do we want to **announce** it to the customer, or quietly include it as a "delight"? | Syed |
| 2.1.3 | Syed believes the SOW timeline is padded — do we plan to **deliver early** and use the headroom for stretch goals? | Syed / Kaushik |

### 2.2 Team

| # | Question | Owner |
|---|----------|-------|
| 2.2.1 | Of the 6 unidentified offshore resources, what skill mix do we need? (Suggested: 2 data engineers, 2 AI/ML, 1 frontend, 1 backend) | Syed |
| 2.2.2 | Coverage plan for Athul during late-May India travel | Syed / Athul |
| 2.2.3 | Does Kaushik need a **delivery manager** above him given the "very high visibility" framing? | Syed |

### 2.3 Architecture / Build

| # | Question | Owner |
|---|----------|-------|
| 2.3.1 | Vector DB choice on GCP — Vertex AI Vector Search? Self-hosted Qdrant on GKE? AlloyDB + pgvector? | Tech lead |
| 2.3.2 | LLM choice for the interim period before Gemini is fully provisioned | Tech lead |
| 2.3.3 | Confluence content extraction tool — Atlassian REST API? Custom HTML parser? Unstructured.io? | Data engineer |
| 2.3.4 | Chunking strategy for Confluence pages (which often have hypothesis + variation + results sections — clear semantic boundaries) | AI engineer |
| 2.3.5 | Re-ranker — Cohere? BGE-Reranker? Vertex AI built-in? | AI engineer |
| 2.3.6 | Evaluation framework — Ragas? Custom golden-set tests against David's Excel-pivot insights? | AI engineer |
| 2.3.7 | How do we **ground** insights to avoid hallucination? Citations on every claim? | AI engineer |

### 2.4 Project Management

| # | Question | Owner |
|---|----------|-------|
| 2.4.1 | Sprint cadence — 1 week or 2 week sprints? | Kaushik |
| 2.4.2 | Demo cadence to customer — every sprint or every 2 sprints? | Kaushik |
| 2.4.3 | What "sustainable, low-maintenance" means in the context of David's request — 1 year support? 2 years? | Syed |
| 2.4.4 | Risk register format and review cadence | Kaushik |

### 2.5 Communication

| # | Question | Owner |
|---|----------|-------|
| 2.5.1 | Should we proactively brief Ayush on the timeline / scope nuances, given his repeated "high visibility" comments? | Syed |
| 2.5.2 | What's the escalation chain when David is "chill" but Aravindhan is not? Do we route status to both? | Syed |
| 2.5.3 | Will Syed's onsite trip include intro meetings with David, Holly, and Aravindhan for relationship-building? | Syed / Aditya |

---

## 3. My Doubts / Things to Validate (Reading the Transcript)

These are ambiguities I noticed in the transcript that may or may not be issues — flagging for the team to validate.

| # | Doubt | Where in Transcript |
|---|-------|---------------------|
| 3.1 | Aditya says Confluence is the "primary" source and Excel/PPT are derivatives — but Kaushik specifically asked because the proposal lists Excel + PPT as sources. **Is the SOW out of date with Aditya's understanding?** | Around minute 30 |
| 3.2 | Aditya: "We try to move them to SharePoint so it's easier for maintenance." Implies SharePoint adoption is **incomplete** — some tests may still only be in old Excels. Coverage gap? | ~minute 19 |
| 3.3 | Aditya isn't 100% sure post-scaling tracking happens at all today. **If it doesn't, can we even build Phase 2 tracking later?** Where would the post-scale data come from? | ~minute 15 |
| 3.4 | The transcript mentions "Adobe Customer Analytics Journey or Adobe Customer Journey or Databricks" as data sources — but they're explicitly out of scope. **Are we sure no test result data needs to come from there?** | ~minute 4 |
| 3.5 | "GAP GPT" was mentioned as recently released, but no one knew the access tier. **Worth investigating** — could be cheaper / faster than custom LLM |  |
| 3.6 | "Nucleos had some issues, at least in the gap environment" — we're picking web app over Nucleos, but **Nucleos issues are unspecified**. Could the same issues hit our web app? | ~minute 36 |
| 3.7 | Aditya says all of David's belief is that the human-written Confluence report should NOT be automated. But **could we offer a "draft" template or auto-fill of metadata fields** as a delight? Not auto-write, but auto-assist? | ~minute 30 |
| 3.8 | The dashboard in the screenshot shows "Needs Attention: 10 — Tests that have ended but are missing an outcome." **Should our V1 surface this gap too as a quality-of-life feature?** |  |
| 3.9 | Athul says "Image data and Confluence will not be searchable or included in the analysis is a limitation that we have brought up." **Has this been signed off in writing by the customer?** Or just spoken? | ~minute 42 |
| 3.10 | The pivot table screenshot shows tactic-level breakdowns (Quality, Time Savings, Urgency, Value). **Should our chatbot replicate these specific pivots as common queries?** Or let the user freeform them? |  |
| 3.11 | Confluence reports are written by analysts — there's likely **inconsistency** in style, structure, and depth across years. **How do we handle this for retrieval consistency?** |  |
| 3.12 | Estimated Annualized Value is an *input* (the analyst predicts it). **No one tracks whether the prediction was correct.** If we expose this, we may surface its unreliability. | ~minute 15, screenshot |
| 3.13 | Aditya: "Some certain levels" might have access to GAP GPT. **What level of access do offshore resources get?** Affects what tools we can use during dev |  |
| 3.14 | Aditya mentioned he hasn't worked on **GCP in the GAP environment yet**. This is a **big unknown** — provisioning, IAM, networking, billing all TBD | ~minute 47 |
| 3.15 | Test outcomes lifecycle: tests run 1–6 months. **During that window, does the chatbot need to surface "live" tests differently from "closed" ones?** Inflight, Live, Closed are filter views in the SharePoint |  |
| 3.16 | "AI fitting" was mentioned as a recent test type. **GAP is itself running AI experiments** — might they want our solution to track AI/non-AI tests as a distinct dimension? |  |
| 3.17 | Aditya offered to share Excels via SharePoint. **Make sure these are received and reviewed before kickoff** — they contain real test data and will inform demo scenarios | ~minute 46 |
| 3.18 | "Project ours to lose" / high visibility — **we should plan a customer reference / case study upfront**, not just deliver V1 |  |

---

## 4. Suggested Kickoff Agenda Items

Based on all the above, here's what I'd insist on covering at the kickoff with David:

1. **Confirmed scope statement** — what's in / out of Phase 1 (read aloud, get verbal sign-off)
2. **Persona walkthrough** — who uses this, with what landing page
3. **"Insights vs. Recommendations" boundary** — explicit wording in the kickoff deck
4. **FY25/26 vs. all 1,500 tests** — confirm phasing
5. **Image content limitation** — confirm in writing
6. **GCP provisioning and access plan** — names, dates, blockers
7. **Success criteria for V1** — what does David need to see in Sept to call this a win?
8. **Working session cadence** — weekly with David, daily standup internal, demo every 2 weeks?
9. **Risk register** — share top 5 risks transparently
10. **Phase 2 teaser** — show we're already thinking ahead (forward-looking recos, post-scale tracking, image extraction)

---

*Last updated from transcript review only. Validate every item with David before treating any answer as final.*
