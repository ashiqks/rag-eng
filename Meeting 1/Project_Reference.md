# GAP Experimentation Discoverability — Project Reference

> **PURPOSE**: This is the canonical reference for the project. Read it at the start of every working session to refresh context. It captures every detail surfaced in the April 28, 2026 walkthrough meeting — including small details that may matter later.
>
> **Source**: GAP - Experimentation Discoverability Walkthrough · April 28, 2026 · 1h 0m 55s
> **Last updated**: From transcript only (no client confirmation yet)

---

## 1. Stakeholders & Personas

### 1.1 Customer-Side People

| Person | Title / Role | Importance | Notes |
|--------|--------------|-----------|-------|
| **Aravindhan** | Senior leader (executive sponsor) | Top of escalation chain | Everything rolls up to him. Likely less flexible on timelines than David/Holly. Recently visited Google for Google Next — strategic shift to GCP/Gemini is his initiative. |
| **David Rose** | Director, Test and Learn | **Primary day-to-day contact** | Owns digital, customer, and store tests. "A little chill on timeline." Believes the human element of writing results should NOT be automated. |
| **Pratik Oberai** | Senior Manager, Test and Learn | Reports to David | One of two people whose institutional knowledge of past experiments lives "in their head." |
| **Holly** | (Aditya's reporting line on GAP side) | Less time-pressure-driven | Aditya described her as "a little bit lazy" re: timelines. Previous IDs raised for someone went to Holly but should now go to David. |
| **David's team (5–10 people)** | Analysts, senior analysts | Test designers | Decide test plan: N, MDE, randomization, control vs test split. |
| **PDM teams** | Product Decision Makers | Test requestors | Brand-level, app owners, UX folks who request experiments. They DO add rows to the current SharePoint/Excel. |
| **Brand owners / Digital folks / UX leads** | Test idea originators | Same persona class as PDMs |

### 1.2 Solution User Personas

| Persona | What They'll Use the App For | Landing View |
|---------|-----------------------------|--------------|
| **Executive (Aravindhan, VPs, SVPs)** | "What is working in experiments? What kind of tests are winning?" — high-level summary | Dashboard view (closed tests count, wins, losses, incremental revenue, averted loss) |
| **David / Pratik / Test & Learn analysts** | Discovery, brainstorming, knowledge transfer across team | Chatbot + dashboard |
| **PDM / Brand / App owners** | "Has this kind of test been done before? What were the learnings?" before requesting a new test | Chatbot |

### 1.3 Delivery Team (Mathco / Vendor Side)

| Person | Role |
|--------|------|
| **Aditya Govind Ravikrishnan** | Has built the current dashboard (stopgap); SF-based; the project context-holder |
| **Syed Muzaffar J** | Engagement lead; traveling to Atlanta (Coke build resource) |
| **Kaushik B** | **Offshore lead for this project** |
| **Athul Babu** | Onsite (Sunnyvale); going to India end of May for visa stamping (~2 weeks) |
| **Nilim Borah** | Offshore resource (confirmed) |
| **Nithin Chandra** | Engineering (was part of prior engineering work for the dashboard) |
| **Designer** | 1 designer onboarded, name TBD |
| **Ayush** | Mentioned re: communications/escalation |
| **Mansi (Javelin team)** | Did the Figma solutioning mockup |
| **Justin** | Returning May 4–5 — coordinate meeting around that |
| **Bansi, Atul** | Earlier conversation participants (held context originally) |

---

## 2. Customer Business Process (Today — As-Is)

### 2.1 The End-to-End Experimentation Workflow

```
Step 1: Idea Origination
   - Source: PDM, Brand, App owner, UX team, Digital folks
   - Examples: "Should we change the checkout button position?", "Show vs. hide free shipping thermometer",
     "Bubble vs. Pop-up for email acquisition", "AI fitting (à la Zara)", "Loyalty/Rokt-related changes"

Step 2: Test Design (David's team)
   - Decisions: sample size (N), Minimum Detectable Effect (MDE), randomization, test/control split
   - Note: ALL experiments are A/B tests (no quasi-experiments, no DiD)
   - Test runs: 1 to 6 months (most are 3-4 months)

Step 3: Test Execution (Optimizely - 3rd-party licensed platform)
   - Optimizely is a licensed marketing/experimentation automation tool
   - Runs the experiment end-to-end on GAP's behalf
   - Has AI-driven marketing experiment products (used for some tests)

Step 4: Results Pulling (Adobe Customer Journey / Databricks)
   - Customer keys for test/control exist in Adobe / Databricks
   - When test ends, analyst drag-and-drops in Adobe to pull revenue / CTR / KPI metrics

Step 5: Significance Testing (Excel)
   - Numbers pulled into Excel
   - Basic significance tests run in Excel
   - Outcome classified as: Win / Loss / Flat

Step 6: Documentation (Confluence)
   - Each test gets a full Confluence write-up
   - Sections: Hypothesis, Variation Description (Control vs Challenger),
     screenshots/video of the change, full-text findings summary, win/loss revenue impact,
     "Who did this", learnings
   - Example seen: "[BRONGA APP] iOS Shopping Bag Payment Buttons Collapse Results"

Step 7: Metadata Capture (SharePoint List)
   - Analyst manually adds a row in the SharePoint Experimentation Catalog
   - Fields: Test Name, Test Description, Brand, Market, Source, Start/End Date, Platform,
     Device, Channel, Channel Section, Audience, Vendor, Primary KPI, Other KPI,
     Winning/Losing Delta %, Estimated Annualized Value ($), Recommendation,
     Confluence Result Link, Recommendation Adopted, Test Insights, Return Rate, Attachments
   - Statuses: All Items / Closed Tests / Inflight / Live

Step 8: Pivoting (Manual — David, every 3-4 weeks)
   - David goes into pivot tables in Excel
   - Pivots by tactic (Quality, Time Savings, Urgency, Value), brand, channel, device
   - Generates simple insights like:
     "Quality tests are mostly flat (72% flat, 21% win, 7% loss)"
     "Time Savings tests win more often (43% win, 48% flat, 9% loss)"
     "Urgency tests: 100% loss (small sample)"
     "Value tests: 67% flat, 13% loss, 77% other"

Step 9: Power BI Dashboard (Current Stopgap)
   - Built by Aditya's team
   - Shows: Total Tests (490), Needs Attention (10), Incremental Revenue ($220M),
     Averted Revenue Loss (-$144M), Closed Tests (427), Live Tests (31), Inflight Tests (22)
   - Drill-down view shows: Closed/Wins/Losses, Program Insights (text), Result Breakdown donut,
     Test Insights with summarized results
   - Filters: Start Date, End Date, Brand, Market, Source, Platform, Device, Channel,
     Channel Section, Audience, Vendor, Primary KPI, Other KPI, Tactic, Recommendation Adopted
```

### 2.2 Test Outcome Definitions

| Outcome | Meaning |
|---------|---------|
| **Win** | Making this change increases revenue / CTR / target KPI by X% |
| **Loss** | Making this change loses money — referred to as "averted loss" because they then DON'T make the change. They count this as money they "stopped from being lost" |
| **Flat** | The change makes no statistically significant difference. **Most tests fall into this bucket.** |

### 2.3 Tactic Categories (for classification)

- **Quality** — improvements to product/feature quality
- **Time Savings** — reduce friction or steps
- **Urgency** — drive faster action (e.g., countdown timers)
- **Value** — pricing, promos, perceived value

### 2.4 Volume Statistics

| Metric | Value |
|--------|-------|
| Total experiments lifetime | ~1,500 (across last 6–7 years) |
| FY 2025 | ~450–490 tests |
| FY 2026 (so far) | ~20–30 tests |
| Two-year window | ~700 tests |
| One-year window | ~500 tests |
| Phase 1 scope (proposed) | FY25/26 → ~500–600 Confluence reports |

---

## 3. The Pain Points (Why This Project Exists)

### 3.1 Pain Point 1 — Discoverability (PRIMARY)

- 1,500 Confluence reports exist; **no one knows what's in them collectively**
- Only David and Pratik carry institutional memory of past tests
- When Aravindhan asks "what's working?", David has to manually pivot or dig
- Senior leadership (VPs, SVPs, executives) have **no easy way to discover** experiment learnings
- PDM team can't easily check "has this been done before?" before designing a new test

### 3.2 Pain Point 2 — Insights Lost in Unstructured Text

- Confluence has rich textual analysis and learnings written by humans
- The current dashboard / Excel can only do simple metadata aggregations
- All the **nuanced learnings live in unstructured natural language** that is invisible to the dashboard
- David has tried pasting into ChatGPT and gets reasonable insights — but nothing systematic
- Quote from David's experience: "When I show this to a GPT, it gives me random insights" — confirming there's value in LLM-based summarization but it must be grounded in the actual Confluence content

### 3.3 Pain Point 3 — Manual Effort

- Manual row entry in SharePoint
- Manual pivoting by David every 3–4 weeks
- Manual creation of Confluence pages (this WILL stay manual — David's belief)

### 3.4 Pain Point 4 — Possibly: Duplicate Tests

- Kaushik asked: do they ever run duplicate tests?
- Aditya: "Quite possibly they could be wasting a lot of time… but I'm not fully sure if they catch these things beforehand"
- **Question to validate with David at kickoff** (see Open Questions doc)

---

## 4. Solution — Phase 1 (Committed Scope)

### 4.1 What We Are Building

A **web application** with:
1. **Chatbot interface** as the primary interaction model (natural-language Q&A over historical experiments)
2. **Dashboard view** as a secondary surface (replaces the current Power BI stopgap)
3. **Persona-aware landing pages**:
   - Executive persona → dashboard (high-level metrics) with chatbot at the bottom
   - Analyst/PDM persona → chatbot first, with toggle to dashboard view

### 4.2 Capability Set (Phase 1)

| Capability | Description |
|------------|-------------|
| **Discovery search** | "What checkout-related tests have we done?" → returns matching tests with metadata |
| **Summarization** | "Summarize the learnings from these 15 tests" → grounded summary across Confluence content |
| **Level-1/Level-2 insights** | "5 similar tests ran, 4 won, 1 was flat. Successful tests had X characteristic." |
| **Citations** | Links back to source Confluence pages |
| **Filters** | Brand, market, channel, device, tactic, primary KPI, etc. (mirroring the dashboard) |
| **Metrics tiles** | Total tests, wins/losses/flat counts, $ incremental revenue, $ averted loss |

### 4.3 What is OUT of Phase 1 Scope

| Out of Scope | Notes |
|--------------|-------|
| **Image content extraction from Confluence** | Documented as a Phase 1 limitation (Athul confirmed). Team will experiment with GCS bucket → LLM scan → image store as a stretch. |
| **Forward-looking recommendations** | "What should I test next?" without context — Phase 2 |
| **Post-scaling monitoring** | Tracking whether wins held up after rollout — Phase 2 |
| **Adobe / Databricks automation** | David explicitly does NOT want the human write-up of results to be automated |
| **Store and customer-related tests** | All work to date is on digital tests; store/customer is "more recent and they want to document it" — likely Phase 2 |

### 4.4 Phase 2 (Not Committed)

1. **Forward-looking recommendations** — "Given my idea, what should I test next?"
2. **Scaled-experiment tracking** — Track tests post-win to see if predicted lift holds at scale
3. **Image content** in Confluence
4. **Store/customer tests** parsing

### 4.5 Important Boundary

> "Insights ≠ Recommendations" — Syed
>
> Phase 1 = Summarization + simple historical patterns ("5 tests, 4 won").
> Phase 1 should NOT answer cold "What should I test?" questions without context.
> Phase 1 CAN say "Given last year's checkout tests, X% won — this might be a fair test to run" once the user has provided context.

---

## 5. Technical Architecture (As Discussed)

### 5.1 Mandated Technology Choices

- **Data layer**: **GCP** (mandate from David — strategic shift across GAP)
- **GCP-based storage**: Confluence content extracted → GCP Storage (likely GCS bucket)
- **Application hosting**: TBD by us — David is flexible. Customer is "fully on GCP" but not opinionated on the app layer.
- **Authentication / Identity**: GAP IDs (Ping ID provisioning); requested via David (NOT Holly going forward)

### 5.2 Inferred Architecture (Not Yet Confirmed)

```
Confluence (1,500 pages)
    ↓ [Pipeline: data engineers]
GCP Storage (raw + structured)
    ↓
Vector store + Metadata store
    ↓
Chatbot (RAG) + Web App + Dashboard view
    ↓
GAP users (executives, David's team, PDMs)
```

### 5.3 Source Systems (Read-Only)

| System | Purpose | In Scope for Phase 1? |
|--------|---------|----------------------|
| **Confluence** | Primary knowledge source — 1,500 detailed reports | ✅ Yes — primary |
| **SharePoint Experimentation Catalog** | Metadata rows | ✅ Yes (lighter — already structured) |
| **Excel "All / PIVOTS / BR / GP / ON / PDM" workbooks** | Aditya: "Just a summarized version of the Confluence" | ⚠️ Unlikely separate ingest needed |
| **Power BI dashboard** | Current stopgap | ❌ Not a source — being replaced |
| **Adobe Customer Journey** | Source of test results | ❌ Not in scope |
| **Databricks** | Source of test results | ❌ Not in scope |
| **Optimizely** | Test runner | ❌ Not in scope |

### 5.4 Tech Stack Status at GAP

| Tool | Status |
|------|--------|
| **Microsoft Copilot** | Currently the only AI tool Aditya has access to |
| **GAP GPT** | Recently released internally (access tier unclear) |
| **Claude / OpenAI** | Not currently available at GAP |
| **Google Enterprise (Gemini)** | NOT yet provisioned, but expected in next 6–7 months |
| **Nucleos** | Tried, but had issues in GAP environment — abandoned for this project |

---

## 6. Solution Inspiration — Figma Mockup

- **Created by**: Mansi (Javelin solutioning team)
- **Status**: Inspirational only — NOT a binding commitment
- David Rose liked it. Aravindhan has been shown it.
- The "look" included: filter pane + metrics tiles + recent tests list + chatbot/search
- **Important**: Syed flagged that the SOW estimate was NOT scoped against this exact mockup — what we ultimately build is "fully on us"
- **4 Pillars from Figma** (per Kaushik's reference): the 4th pillar mentioned "AI generated recommendations based on historical outcomes"
  - Aditya clarified: "summarization of what you have done in the past and insights from it" — NOT future recommendations

---

## 7. Timeline & Project Plan

### 7.1 Key Dates

| Date | Event |
|------|-------|
| **April 28, 2026** | This walkthrough meeting |
| **End of week (May 1)** | Identify remaining 6 offshore resources |
| **May 4–5, 2026** | Customer kickoff (Mon/Tue) |
| **~May 4** | Project officially starts |
| **End of May (2 weeks)** | Athul in India for visa stamping — coverage needed |
| **~September 4, 2026** | Phase 1 V1 target (4 months from start, per SOW) |
| **Next 6–7 months** | GAP transitions to Google Enterprise (parallel to our project) |

### 7.2 Phasing of Work (First 4 Months)

| Weeks | Focus | Resources |
|-------|-------|-----------|
| **Weeks 1–3** | Design discussions with customer; access provisioning; pipeline build (Confluence → GCP) | Designer, Nilim, Kaushik, data engineers |
| **Weeks 3+** | AI engineers begin prompt engineering; front-end devs build app | AI engineers, FE devs |
| **Throughout** | Weekly status updates to customer; transparent risk/delay communication | All |

### 7.3 Internal Mathco POV on Effort

- **Nithin**: Initial estimate was lower; SOW timeline was extended "due to some conversations" (i.e., to make it a bigger engagement)
- **Syed**: Believes solution "can be executed, built, and delivered way more efficiently than the quote we've given to the customer"
- **Engagement is "ours to lose"** — high visibility, high usability, strong team

---

## 8. Team Structure

### 8.1 Confirmed Roles

| # | Role | Person |
|---|------|--------|
| 1 | Onsite engagement lead | Syed Muzaffar J (also on Coke — Atlanta-based) |
| 2 | Onsite point | Aditya Govind Ravikrishnan (San Francisco) |
| 3 | Onsite | Athul Babu (Sunnyvale; India travel late May) |
| 4 | Engineering | Nithin Chandra |
| 5 | **Offshore lead** | **Kaushik B** |
| 6 | Offshore resource | Nilim Borah |
| 7 | Designer | 1 onboarded (name TBD) |
| 8–13 | 6 more offshore resources | TBD by Syed via DelOps |

### 8.2 Resource Profile Needed

| Profile | Likely Count |
|---------|-------------|
| Data engineer (Confluence → GCP pipelines) | 1–2 |
| AI engineer (RAG, prompt eng) | 1–2 |
| Front-end developer | 1–2 |
| Designer | 1 (already onboarded) |
| Lead | 1 (Kaushik) |

---

## 9. Access & Onboarding

### 9.1 GAP ID Provisioning

- **Time**: 2–3 days for ID; ID provided by IT
- **Channel**: Ping ID creation; onboarding doc + recording exists (Aditya will share)
- **Requestor**: Must go through **David** (NOT Holly — last time it went to Holly and stalled)
- **Required from team**: Full name + phone number per resource
- **Athul** to share a document with these details

### 9.2 Access Required

| System | Status / Lead Time | Notes |
|--------|--------------------|----|
| **GAP ID (Ping)** | 2–3 days | Standard onboarding |
| **Confluence** | Comes with GAP ID | |
| **SharePoint** | Comes with GAP ID | |
| **Databricks** | TBD | |
| **GCP (in GAP env)** | **UNKNOWN — biggest unknown** | Aditya hasn't worked on GCP in GAP environment yet |

### 9.3 Internal (Mathco) Setup

| Item | Owner | Status |
|------|-------|--------|
| Teams group + linked SharePoint for project | Kaushik (raise IT request) | To do today |
| GAP SharePoint with shared artifacts | Aditya | Will populate with Excels and onboarding docs |
| Excel artifacts (sit in Aditya's environment) | Aditya | Will share via SharePoint |

---

## 10. Communication & Governance

### 10.1 Cadence (As Implied)

- **Weekly status to customer**: "Boss, this is what we did. Delays happened because of us / because of you" — Syed
- **Customer kickoff**: Mon/Tue next week
- **Working sessions with customer**: Post-kickoff — define metrics, layout, app design
- **In-person customer meetings**: Syed plans to meet David, Holly, et al. in person after May 6 (post Atlanta trip)

### 10.2 Cultural / Tonal Notes

- David is "chill on timelines"
- Holly is "a little lazy" / less time-pressure-driven
- Aravindhan may be tighter on timelines
- Project has "very high visibility" (per Ayush, mentioned 3-4 times)
- Customer needs **transparent communication** and **proactive accountability** on timelines

---

## 11. Detailed Decisions & Alignments Made in This Meeting

| # | Decision | Owner / Source |
|---|----------|---------------|
| 1 | Phase 1 = Discoverability + summarization + Level 1 insights only | Syed + Aditya alignment |
| 2 | Phase 2 = Forward-looking recommendations + scaled-test tracking | Syed (proposed) |
| 3 | Start with FY25/26 confluences (~500) for tuning, expand to all 1,500 once pipeline works | Nithin proposed; team agreed |
| 4 | Image content in Confluence is OUT of Phase 1 scope (text only) | Athul confirmed; documented limitation |
| 5 | Stretch: experiment with image extraction (GCS → LLM scan → store) | Nithin proposed; Syed agreed (no commit) |
| 6 | Web application + chatbot UI (NOT Nucleos) | Aditya — Nucleos had GAP environment issues |
| 7 | Persona-aware landing: Executive sees dashboard, Analyst/PDM sees chatbot first | Syed proposed |
| 8 | GCP is the data backbone (mandated by customer) | Customer mandate |
| 9 | App hosting layer is our call (sustainable, low maintenance) | David flexible |
| 10 | Confluence is the single primary source — Excel/PPT are derivatives | Aditya |
| 11 | Human writes the Confluence result reports — NOT to be automated | David's stated belief |
| 12 | Kickoff Mon/Tue next week | Syed |
| 13 | Kaushik leads offshore | Confirmed |
| 14 | Weekly transparent status to customer (delays attributed proactively) | Syed |
| 15 | Phase 1 V1 target: ~Sept 4, 2026 | Per SOW (4 months from May 4) |

---

## 12. Risks & Open Items (Snapshot)

(See `Open_Questions.md` for the full list of clarifications.)

| Risk | Severity | Mitigation |
|------|----------|-----------|
| GCP access in GAP environment is unfamiliar | High | Aditya to investigate ASAP |
| 6 offshore resources not yet identified | Medium | Syed via DelOps by end of week |
| Image content limitation may surprise customer | Low | Already documented in proposal |
| "Recommendations" expectation mismatch | Medium | Level-set in kickoff |
| Aravindhan's timeline rigidity unknown | Medium | Manage via David; weekly status |
| Athul out for ~2 weeks late May (visa stamping) | Low | Plan coverage |
| Confluence parsing complexity (tables, screenshots, video links) | Medium | Document parser choice early |
| Duplicate-test detection — unclear if a real customer ask | Low | Validate at kickoff |

---

## 13. Glossary

| Term | Meaning |
|------|---------|
| **A/B test** | Experiment with a control group and one or more challenger variants |
| **MDE** | Minimum Detectable Effect — smallest effect size the test is powered to detect |
| **Win / Loss / Flat** | Test outcome classifications — winning lift / negative impact / no significant change |
| **Averted loss** | Money "saved" by NOT rolling out a losing variant |
| **Tactic** | Test category — Quality, Time Savings, Urgency, Value |
| **Inflight test** | Planned but not yet started |
| **Live test** | Currently running |
| **Closed test** | Completed with an outcome |
| **Confluence report** | Atlassian Confluence page with full hypothesis, variation, results, learnings |
| **Optimizely** | Licensed 3rd-party experimentation platform that runs the actual A/B tests |
| **PDM** | Product Decision Maker — internal product/brand stakeholders who request tests |
| **Discoverability** | Primary project goal — making 1,500 historical experiments findable |
| **Estimated Annualized Value** | Projected $ value if a winning test is rolled out at full scale |
| **Recommendation Adopted** | Field tracking whether the test's recommendation was actually implemented |

---

*If anything in this document conflicts with what the customer says at kickoff, the customer wins. Update this document immediately.*
