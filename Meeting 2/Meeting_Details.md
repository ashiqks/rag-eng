# Meeting 2 — Detailed Discussion Notes

**Date:** 6 May 2026
**Topic:** Walkthrough of GAP's current A/B testing workflow
**Participants:** Prateek Oberoi (GAP Test & Learn COE), Kaushik, Justin, Atul, Aditya, Sameera, Abbas, Shar (Mathco / project team)

This document captures every substantive point discussed in the meeting, in the order it was raised. Casual chit-chat, screen-sharing logistics, and scheduling small-talk are excluded.

---

## 1. Framing the Session

- The Mathco team had drafted an *initial* understanding of GAP's A/B testing process and walked Prateek through it first to "level-set" before he expanded on it.
- The team's stated reason for going first: their access IDs to GAP systems were not yet provisioned, so they needed Prateek's verbal walkthrough to keep momentum.
- Three explicit anchor objectives for the call:
  1. Identify all **user personas** in the process.
  2. Identify all **Confluence touchpoints** they have (since Confluence is the redesign target).
  3. Identify all **platforms** used end-to-end.

---

## 2. Mathco's Initial Understanding (validated by Prateek)

Mathco walked through their draft view:

- A **PM has an idea** (e.g., a feature, checkout placement).
- Idea is sent to the **experimentation team** (Dave's org) which validates the hypothesis and the planned duration.
- If approved, the test is moved into **Optimizely**, which executes the A/B test.
- A **Confluence page** is manually created in parallel with the test, capturing hypothesis details.
- When the test ends, results are appended into **the same Confluence page**.
- **Adobe** measures part of the test data; some metrics flow further "downstream" (a follow-up workaround was hinted at).
- The user manually feeds the outputs back into the Confluence page.
- Open question Mathco flagged: *what happens when the idea is rejected?* (logged as a question mark in their diagram)

Prateek confirmed this was largely correct and proceeded to add several layers of detail.

---

## 3. Recent Org Restructure — Value Streams

- GAP very recently restructured by **value streams**, defined as the major page sections of the site:
  - **PLP** (Product List Page — category & search)
  - **PDP** (Product Page)
  - **Shopping Bag**
  - **Checkout**
- Each value stream has a **dedicated Product Manager (PDM)**.
- The experimentation team's new operating model is to receive requests via these PDMs.
- *Today*, requests still come from multiple streams (legacy teams, brand-side teams). *Going forward*, PDMs are intended to be the single intake channel.
- Resourcing: the experimentation team is still planning **how to dedicate analysts to specific value streams** — this is TBD.

> Implication for the GenAI tool: the discoverability surface should be navigable by **value stream** because PDMs and analysts will increasingly be assigned per stream.

---

## 4. The "Three Months" Timeline Question

- Mathco asked whether ideation-to-execution truly takes ~3 months.
- Prateek's answer: **"It depends."** He did not confirm or refute the figure and pivoted into describing how ideas originate, suggesting the duration is highly variable.

---

## 5. Idea Sources — The Process Is a *Loop*, Not Linear

Prateek emphasized this point repeatedly. Ideas can originate from **any of three streams** simultaneously:

1. **PDM Roadmap** — scheduled, quarterly-planned work.
2. **Brand-driven ad-hoc requests** — e.g., "Our competitor just launched X, can we test this?" Often pushed for delivery in days or 1–2 weeks.
3. **Experimentation team's own learnings/recommendations** — observations from prior tests that suggest a new variant or follow-up test.

Findings from completed tests **flow back** into the brainstorming cycle, making the process explicitly circular. The "How the AB Test Process Works" diagram shared by Prateek (Brainstorming → Generate Ideas → Determine Feasibility → Coding → Testing → Data Analysis → Recommendations → back to Brainstorming) reflects this loop.

> Justin's reframing (confirmed by Prateek): "Three ways ideas come in — PDM roadmap, brand competitor-driven asks, and your own cross-brand recommendations. The new tool especially helps with the third."

---

## 6. Brainstorming — Cadence

- It is **both** scheduled and ad-hoc:
  - PDMs operate on a roadmap → predictable cadence.
  - Brands raise time-sensitive requests → ad-hoc.
  - Experimentation team's data-driven nudges feed in opportunistically.

---

## 7. Scope of Tests — Digital vs. Store

- Dave's team owns **both digital and in-store** experimentation.
- A separate dedicated resource handles **retail/store** experimentation.
- Prateek and the resources relevant to this project are on the **digital side**.
- The new tool is implicitly digital-only for Phase 1.

---

## 8. Feasibility Assessment — Two Sub-Decisions

Feasibility actually answers two distinct questions:

1. **Can the test be technically built?** (code limitations, platform support)
2. **Is the change material enough to be worth testing?** Some changes are so small the team simply rolls them out without an A/B test.

This second decision happens **inside the feasibility step**, not before it.

---

## 9. Test Implementation — Client-Side vs. Server-Side

| Aspect | Client-side | Server-side |
|--------|-------------|-------------|
| Mechanism | Optimizely overrides the page after it loads | Engineering codes the variant directly into the site/server |
| Build time | Fast | Slow (real engineering effort) |
| User experience | Possible visible "flash" / 1-second delay as override applies | Smooth — variant renders before page is served |
| Use case | Quick iterations, simple UI tweaks | Larger features, performance-sensitive variants |

Both approaches are supported. The choice is part of the feasibility / planning conversation.

---

## 10. Confluence Artifacts — Test Plan and Test Results

Two standardized template pages are created per test inside the **Test and Learn COE** Confluence space.

### 10a. Test Plan Page

Standardized fields shown by Prateek (and visible in the screenshots):

- **Brand** (e.g., Old Navy)
- **Page / Funnel / Channel** (e.g., Product Page)
- **Audience Limitation** (e.g., All Customers)
- **Problem Statement**
- **Hypothesis**
- **Experimental Changes** — Control vs. Challenger description
- **Additional Documents** — comparison snapshots
- **Significance Calculations & Experimental Design** block:
  - Brand
  - Scenarios (e.g., 1 Control + 1 Challenger)
  - Primary KPI (e.g., OPV)
  - Minimum Detectable Lift (e.g., ~0.4%)
  - Confidence Threshold (e.g., ~80%)
  - Power Threshold (80%)
  - Sample Size Calculations (e.g., ~7.2 MM visits per variation)
  - Estimated Duration (e.g., ~2–3 weeks)
  - Sample Size Calc Assumptions
  - Test Exposure (e.g., 100% / 50–50 split)
  - Secondary Metrics — Indicating Success
- **Adobe Dashboard Link** (Adobe Experience Cloud)
- **Measurement** section — four buckets:
  - Metrics (All Experiments) — Conversion Rate (OPV), Net RPV, AOS, UPT, AUR, Total Visits, Visits Split by Visit/Visitor, Variation Overlap
  - Metrics (Test Specific) — e.g., PDP Views Per Visit, Add to Bag Rate, PDP→Shopping Bag Conversion, PDP Certona Engagement Rate, PDP Exit Rate
  - Segments (All Experiments) — New vs. Returning
  - Segments (Test Specific) — Desktop vs. Mobile
- **Custom Metrics** table — Description/Location, Custom Variable & Name in Analytics, Notes (track once / always / etc.)

### 10b. Test Results Page

- **Overview** with restated hypothesis
- **Variation Description** with **screenshots** of Control and Challenger UIs (e.g., Old Navy PDP recommendation modules)
- **DETAILS** section with bullet commentary on directional findings, statistical significance disclaimer, and breakdowns by Device Type (Desktop/Mobile) and Visit Type (New/Returning)
- **Impacts** table — Net RPV, OPV, AOS, UPT, AUR, Product Views/Visit, PDP→SB, Add-to-Bag Rate, Exit Rate (PDP), PDP Certona 1 or 2 Engagement Rate, plus Incremental delta row
- **Product Mix** block
- **Gross Margin** block (GMS/Visit)
- **Findings summary** at top
- **Recommendation** section
- **Optimization Opportunities** that feed the next brainstorming cycle

---

## 11. Confluence Coverage and History

- The Confluence space contains test results going back to **2017** (folders 2017 → 2026 visible).
- It covers approximately **80%** of the tests Prateek's team has run.
- The remaining **~20%** live outside Confluence:
  - Shared via email
  - Shared as PDFs
  - Shared as PowerPoint decks (some teams prefer decks)
- These non-Confluence assets are explicitly **out of scope for Phase 1**. Mathco confirmed Phase 1 will work from where "most of the stuff is" — i.e., Confluence — and standardization of other formats is a follow-up.

---

## 12. Template Stability

- Asked whether the Confluence template has changed since 2017: Prateek confirmed it has been **"almost the same"** — small evolutions, but largely stable.
- This stability is important for the RAG pipeline: parsing rules can be relatively consistent across years.

---

## 13. Repeated / Duplicate Tests (Abbas's question)

Two scenarios where the same test recurs:

1. **Same test, different brand** — Done frequently, because customer bases differ:
   - Athleta & Banana Republic → higher-end customers
   - Old Navy & Gap → discount-focused customers
   - Trivial changes (font) tested once, rolled out everywhere.
   - Funnel-critical changes (Bag, Checkout) tested per brand.
2. **Same test, same brand, repeated over time** — Common for **promo-driven tests** (e.g., 50% off vs. 80% off) which only run during short promotional windows (sometimes only 3 days). Sample size is too small in a single window, so the test is repeated at intervals (e.g., every 2 weeks over a month).

> Implication for RAG: same metrics will recur across many tests with the same brand/page combination, and the system must surface results across reruns and across brand variants.

---

## 14. Metric Selection Patterns

- For the **same test type**, metrics largely remain the same.
- The team looks at **all funnel metrics internally**, but **only shares page-relevant metrics** with brands — e.g., PDP-relevant metrics for a PDP test — to avoid information overload.
- Filtering happens at the experimentation team's end.
- New, test-specific metrics are sometimes introduced; brands need a definition the first time they appear (e.g., *what is "gross margin dollar per visit"?*).

> Implication for RAG: metric definitions must be retrievable as a first-class artifact. The tool should be able to answer "how is X metric defined?" alongside surfacing the test result.

---

## 15. Confluence Access and Current Consumption (Kaushik's question)

- **Anyone with a `gap` email can access** the Confluence space — there is no team-level lockdown.
- However, in practice PDMs and brand teams **rarely traverse Confluence on their own**. They:
  - Have results **presented to them** by Prateek's team.
  - Come back to specific pages a month or two later when they need to re-check findings.
  - Ask Prateek's team to share specific pages when a new but similar test is being considered (e.g., "Old Navy wants to do what Athleta did — share the findings").
- The reason they don't traverse it: **there is no good way to discover relevant pages today.** This is exactly the gap the new tool addresses.

> Quote: "I still get questions from tests that ran in 2023. I know those tests ran because I did them. But if somebody asks someone else from my team, they might not know."

---

## 16. PDM/Brand Difficulty in Consuming Results (Atul's question)

- PDMs/brands are generally fluent in the standard metrics after years of working with the team.
- The friction point is the **occasional new metric** introduced for a specific test — they need a definition the first time they encounter it.
- They are not "unaware" — the metric is referenced in the commentary and summary — but seeing the *raw number in the table* is when the definition question arises.
- Sometimes they ask follow-ups like "you defined it this way; can we look at it differently?"

---

## 17. Two Primary Workflow Pain Points the Tool Solves (Justin's synthesis, accepted by Prateek)

1. **PDM/Brand self-service search** before they ever escalate to Prateek's team. Today this is impossible without opening many Confluence pages manually.
2. **Cross-test recall for the experimentation team** when a new request comes in — the tool surfaces all relevant prior tests with a summary, so any analyst (not just the one who ran them) can synthesize a recommendation.

> Prateek explicitly added: "It's not just me who can do it — anyone in the team can now look for it." This matters because the team is moving toward per-value-stream specialization.

---

## 18. Phase 2 Opportunities (out of scope for now)

Justin flagged technical/process-augmentation opportunities for a later phase:

- Suggesting the **type of analysis** for a new test
- Suggesting the **metrics** to track
- Suggesting the **success criteria**
- Suggesting **how the test should be run** (client- vs. server-side, duration, sample size)

These augmentations were explicitly **deferred to Phase 2** so that Phase 1 stays focused on discoverability.

---

## 19. Closing the Loop — Recommendations

- After running the test, the team:
  - Runs analytics
  - Shares recommendations
  - Creates the Confluence Test Results page
  - Brings findings into the **next brainstorming session** with brands & PDMs
- **Not every test produces an optimization opportunity.** Some tests result in a simple "this works — roll it out to 100%" decision.

---

## 20. Operational / Logistical Items

### 20a. System ID provisioning for the Mathco team
- Mathco needs **~7 IDs**.
- Today, raising it under Holly (Prateek's manager) would route approvals incorrectly.
- Plan: Prateek will walk Kaushik through raising the IDs **today** so they route to **Dave** (the appropriate approver, since Dave is also manager to Mathco's contract).
- After IDs are raised, GAP Sourcing approves, then Dave approves, then external MFA setup is completed.
- Total effort estimated at ~15 minutes today + Dave's approval tomorrow.

### 20b. GCP project provisioning
- Kaushik asked whether GCP project provisioning is straightforward once IDs exist or whether a solution-architecture review is required first.
- Prateek does not know the GCP-specific path; **Dave may**.
- Aditya will follow up with **Greg Christensen** to clarify the GCP onboarding process.
- For Databricks, Greg already supports Aditya — so a similar pattern is expected for GCP.

### 20c. Follow-up Q&A
- Several attendees still had questions when time ran out.
- Atul will **collate the remaining questions** and reach out to Prateek later in the day or via async channels.

---

## 21. Items Explicitly Confirmed for Phase 1 Scope

| Decision | Status |
|----------|--------|
| Phase 1 ingestion source = **Confluence only** | Confirmed |
| PowerPoint / PDF / email findings | Excluded for now |
| Two primary user journeys: PDM self-service + experimentation cross-test recall | Confirmed |
| Recommendation augmentation features | Deferred to Phase 2 |
| Retail/store experimentation | Out of scope (digital-only) |

---

## 22. Open / Unresolved Items From This Meeting

These were raised but not fully answered and should carry forward:

- What happens when an idea is **rejected** at the experimentation-team validation stage? (Mathco's original "?" still partially open.)
- Exact resourcing model for value-stream-aligned analysts (TBD inside GAP).
- GCP project provisioning process and any architecture-review gate (Aditya following up with Greg Christensen).
- Where the ~20% of non-Confluence findings (PDF/PPT/email) live and whether they should be in scope later.
- Exact metric **definitions glossary** — needs to be obtained (or generated) so the RAG tool can answer "what does metric X mean?"
