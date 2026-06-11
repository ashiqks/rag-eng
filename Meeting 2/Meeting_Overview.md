# Meeting 2 — A/B Testing Workflow Walkthrough (Overview)

**Date:** 6 May 2026
**Duration:** ~36 minutes
**Type:** Working session with the GAP Test & Learn (Experimentation) team
**Primary Client SME:** Prateek Oberoi (Digital Experimentation, Test & Learn COE, reporting to Dave)
**Goal:** Level-set on GAP's *current* A/B testing process so the implementation team understands the personas, touchpoints, and platforms that the new GenAI Discoverability tool must integrate with.

---

## Purpose of the Call

The team had three explicit anchor questions for this session:

1. **Personas** — Which user personas are involved in the end-to-end A/B test process?
2. **Touchpoints** — What touchpoints do those personas have with the **Confluence pages** (test plan + test results) that the new tool will redesign / replace as the discoverability surface?
3. **Platforms** — What platforms are used across the workflow (ideation → execution → analysis → publication)?

Phase 1 of the project is intentionally scoped to **Confluence as the canonical input source**. PowerPoints, PDFs, and email-shared findings are **out of scope for Phase 1**.

---

## High-Level A/B Test Process (as confirmed by GAP)

The process is **circular, not linear** — insights from completed tests feed back into brainstorming.

```
Brainstorming → Generate Ideas → Determine Feasibility → Coding (Client/Server side)
        ↑                                                          ↓
   Recommendations  ←  Data Analysis  ←  A/B Test (Optimizely + Adobe Analytics)
```

| # | Stage | Owner | Notes |
|---|-------|-------|-------|
| 1 | Brainstorming | Brands + PDMs + Experimentation team | Ad-hoc + roadmap-driven; loops in prior learnings |
| 2 | Idea generation | Same group | Sources: PDM roadmap, brand asks, competitor signals, prior test learnings |
| 3 | Feasibility | Experimentation team | Includes "is it worth testing?" decision (very small changes may just be rolled out) |
| 4 | Test build | Engineering | **Client-side** (Optimizely override, faster) or **Server-side** (coded on site, slower but smoother UX) |
| 5 | Execution | Optimizely | Power calc determines duration / sample size |
| 6 | Measurement | Adobe Analytics | Some metrics flow further into internal data store |
| 7 | Documentation | Experimentation team | Manual creation of Confluence **Test Plan** + **Test Results** pages |
| 8 | Recommendation loop | Experimentation team → Brands/PDMs | Findings + optimization opportunities feed next brainstorm |

---

## Personas Identified

| Persona | Role in the Workflow |
|---------|----------------------|
| **Product Managers (PDMs)** | Own value streams (PLP, PDP, Bag, Checkout). Future single source of experimentation requests. |
| **Brand Teams** (Old Navy, Gap, Athleta, BR) | Drive many ideas; ad-hoc requests; often the final consumer of results |
| **Experimentation Team (Prateek + Dave's org)** | Run the tests, define metrics, build Confluence pages, give recommendations |
| **In-store Experimentation resource** | Separate digital track; owns retail tests (out of scope for this tool) |
| **Engineering / Dev** | Implements server-side test variants |
| **Mathco / Implementation team** | Building the GenAI discoverability tool |

---

## Platforms / Tools in the Workflow

| Platform | Purpose |
|----------|---------|
| **Optimizely** | A/B test execution (client + server side) |
| **Adobe Analytics / Adobe Experience Cloud** | Primary measurement & dashboarding |
| **Confluence (Test and Learn COE space)** | Canonical home of Test Plans + Test Results — **the primary RAG ingestion source for Phase 1** |
| **Internal data extracts** | Some Adobe data flows into internal stores for deeper analysis |
| **Email / PowerPoint / PDF** | Used ad-hoc for ~20% of tests; **excluded from Phase 1** |

---

## Confluence Coverage

- Confluence space goes back to **2017** (visible folders: 2017–2026 Test Results).
- Covers approximately **80% of tests** run by Prateek's team.
- The remaining ~20% live in email, PDFs, or PowerPoints (variation is informal).
- Templates exist for **Test Plan** and **Test Results** and have been "almost the same" since 2017 — small evolutions over time.

---

## Two Primary Pain Points the Tool Must Solve

1. **PDM/Brand self-service search** — Today, PDMs/brands must either ask Prateek's team or manually open many Confluence pages to find prior test findings. The tool should let them ask a question and surface the relevant tests directly.
2. **Cross-test recommendation support** — When a new request comes in, the experimentation team should be able to instantly see *all relevant prior tests* and synthesize recommendations, instead of doing a manual Confluence trawl.

> "I still get questions from tests that ran in 2023… if somebody can ask that question in the tool, it will show up." — Prateek

---

## New Organizational Context (Important for Design)

- GAP recently **restructured by value streams** (PLP, PDP, Bag, Checkout). Each value stream has a dedicated PDM.
- Experimentation team is **planning to align resources** to value streams (TBD).
- Going forward, **PDMs are intended to be the single intake channel**, but brand-driven ad-hoc requests will continue in parallel for now.

---

## Cross-Brand Test Behavior

- The same test is **frequently rerun across multiple brands** because customer bases differ significantly:
  - Athleta / Banana Republic — premium customers
  - Old Navy / Gap — discount-focused customers
- Trivial changes (e.g., font) are tested once and rolled out across brands.
- Critical-funnel changes (Bag, Checkout) are tested per brand.
- **Implication for RAG:** The tool must handle "same test, different brand" relationships and rerun frequency (e.g., promo tests run every 2 weeks).

---

## Confluence Page Structure (Inputs to RAG Ingestion)

### Test Plan page
- Brand
- Page / Funnel / Channel
- Audience limitation
- Problem statement & hypothesis
- Experimental changes (Control vs. Challenger)
- Significance Calculations & Experimental Design (KPI, MDE, confidence, power, sample size, duration, exposure split)
- Measurement: Metrics (All / Test-Specific) and Segments (All / Test-Specific)
- Custom metrics block
- Adobe dashboard link

### Test Results page
- Variation description (Control vs. Challenger) with screenshots
- Overview / Hypothesis recap
- DETAILS section with directional commentary
- Impacts table (Net RPV, OPV, AOS, UPT, AUR, Product Views/Visit, PDP→SB, Add-to-Bag, Exit Rate, Engagement Rate)
- Product Mix breakdown
- Gross Margin block
- Recommendations / Optimization opportunities

---

## Key Decisions & Action Items from the Meeting

| # | Item | Owner | Status |
|---|------|-------|--------|
| 1 | Phase 1 ingestion scope = **Confluence only** | Mathco / Project team | Confirmed |
| 2 | Raise system IDs for Mathco team (≈7 IDs) | Prateek to walk Kaushik through | Pending — same-day session |
| 3 | Dave to approve IDs once raised | Dave (via Prateek) | Pending |
| 4 | GCP project provisioning process | Aditya to follow up with Greg Christensen | Pending |
| 5 | Follow-up Q&A with Atul to collate remaining questions | Atul → Prateek | Pending |
| 6 | Phase 2 to address recommendation/augmented-analysis flows | Project team | Deferred |

---

## Outcome

The team now has a clear, validated picture of GAP's current A/B testing lifecycle, the personas at each stage, and the canonical Confluence artifacts (Test Plan + Test Results) that will feed the GenAI Discoverability tool's RAG pipeline. Phase 1 scope is locked to Confluence content with PDM/brand self-service search and experimentation-team cross-test recall as the two primary user journeys.
