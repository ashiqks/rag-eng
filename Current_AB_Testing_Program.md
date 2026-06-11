# GAP — Current A/B Testing Program (As-Is)

> **Purpose**: A standalone reference describing how GAP runs A/B testing **today** — independent of the GenAI / RAG project. Use this as the canonical "As-Is" for any new joiner, design discussion, or scoping conversation.
>
> **Sources**: Meeting 1 walkthrough (April 28, 2026) + Meeting 2 working session with Prateek Oberoi (May 6, 2026) + Confluence template screenshots + SharePoint Experimentation Catalog screenshots + Power BI dashboard screenshots.
>
> **Owner of the program (GAP)**: David Rose (Director, Test and Learn) · Prateek Oberoi (Senior Manager, Digital Experimentation)

---

## Table of Contents

1. [Program Overview](#1-program-overview)
2. [Organisation & Personas](#2-organisation--personas)
3. [The End-to-End Workflow](#3-the-end-to-end-workflow)
4. [Idea Sources & Brainstorming](#4-idea-sources--brainstorming)
5. [Feasibility & Test Build Strategy](#5-feasibility--test-build-strategy)
6. [Test Execution & Measurement](#6-test-execution--measurement)
7. [Documentation in Confluence](#7-documentation-in-confluence)
8. [The Confluence Templates (in detail)](#8-the-confluence-templates-in-detail)
9. [The SharePoint Experimentation Catalog](#9-the-sharepoint-experimentation-catalog)
10. [Reporting — Power BI Dashboard & Excel Pivots](#10-reporting--power-bi-dashboard--excel-pivots)
11. [Outcome Classification](#11-outcome-classification)
12. [Tactic Categories](#12-tactic-categories)
13. [Cross-Brand & Repeated Tests](#13-cross-brand--repeated-tests)
14. [Metrics — Standard & Test-Specific](#14-metrics--standard--test-specific)
15. [Volumes & History](#15-volumes--history)
16. [Tools & Platforms in the Stack](#16-tools--platforms-in-the-stack)
17. [Pain Points (today)](#17-pain-points-today)
18. [Constraints & Conventions](#18-constraints--conventions)
19. [Glossary](#19-glossary)

---

## 1. Program Overview

GAP runs a centralised digital experimentation program out of the **Test and Learn COE**. The program covers the full A/B test lifecycle for the digital properties of all four brands — **Old Navy, Gap, Athleta, Banana Republic** — across **PLP, PDP, Shopping Bag, Checkout**, and supporting surfaces (homepage, search, etc.).

A separate (smaller) track inside the same org owns **in-store / retail** experimentation, with a dedicated resource. That track is **out of scope** for this document.

The program ships ~450–500 closed digital tests per year. Every closed test is documented as a Confluence Test Plan + Test Results pair (the canonical write-up) and a row in the SharePoint Experimentation Catalog (the metadata index).

---

## 2. Organisation & Personas

### 2.1 Org structure

| Layer | Role | Notes |
|-------|------|-------|
| Executive sponsor | **Aravindhan** | Strategic owner; recently visited Google Next; drove the GCP / Gemini direction |
| Director, Test and Learn | **David Rose** | Owns digital + customer + store programs; primary day-to-day contact |
| Senior Manager, Digital Experimentation | **Prateek Oberoi** | Reports to David; one of two people whose institutional memory of past tests "lives in their head" |
| Analysts (5–10) | Test designers | Decide sample size, MDE, randomisation, control vs test split |
| Retail experimentation | Dedicated resource | Out of scope for this document |

### 2.2 Stakeholder personas (people who interact with the program)

| Persona | Role in the program | Notes |
|---------|--------------------|-------|
| **Product Decision Makers (PDMs)** | Own value streams (PLP, PDP, Bag, Checkout). Future single intake channel for new test requests. | Recently introduced through a value-stream restructure |
| **Brand teams** (Old Navy, Gap, Athleta, BR) | Drive many ideas; raise ad-hoc requests; final consumer of results | Athleta + BR cater to premium customers; Old Navy + Gap to discount-focused customers |
| **Experimentation team (David's org)** | Run tests, define metrics, build Confluence pages, give recommendations | |
| **Engineering / Dev** | Implements server-side variants | |
| **Executives (VPs, SVPs, Aravindhan)** | Consume "what's working?" insights | Currently rely on David to manually pivot Excel |

### 2.3 New org context (per Meeting 2)

GAP recently restructured by **value streams** — PLP, PDP, Shopping Bag, Checkout — each with a dedicated PDM. The experimentation team is planning to align analysts to value streams (still TBD). Going forward, **PDMs are the intended single intake channel**, but brand-driven ad-hoc requests still flow in parallel today.

---

## 3. The End-to-End Workflow

The process is **circular, not linear**. Insights from completed tests feed straight back into the next brainstorming cycle.

```
        Brainstorming ──▶ Generate Ideas ──▶ Determine Feasibility ──▶ Coding
              ▲                                                            │
              │                                                            ▼
        Recommendations ◀── Data Analysis ◀── A/B Test (Optimizely + Adobe)
```

### 3.1 Stage map

| # | Stage | Owner | Tools | Notes |
|---|-------|-------|-------|-------|
| 1 | Brainstorming | PDMs + Brand teams + Experimentation team | Meetings, Confluence | Three idea sources (see §4). Cadence is mixed — scheduled (PDM roadmap) + ad-hoc (brand) |
| 2 | Idea generation | Same group | — | Loops back from prior test learnings |
| 3 | Feasibility | Experimentation team | — | Two sub-decisions: *can it be built?* and *is it worth testing?* |
| 4 | Test build | Engineering | Optimizely | Client-side override or server-side coded variant |
| 5 | Execution | Optimizely | Optimizely | Power calculation drives sample size and duration |
| 6 | Measurement | Adobe Analytics | Adobe Experience Cloud, Databricks | Some metrics flow further into internal stores |
| 7 | Significance testing | Analyst | Excel | Pulls metrics → significance test → Win / Loss / Flat |
| 8 | Documentation | Experimentation team | Confluence | Test Plan + Test Results pages (templated since 2017) |
| 9 | Catalog row | Analyst | SharePoint | Manual metadata entry per test |
| 10 | Periodic pivoting | David | Excel pivots | Every 3–4 weeks, classified by tactic / brand / channel / device |
| 11 | Recommendation loop | Experimentation team → Brands / PDMs | Meeting + Confluence link share | Findings feed the next brainstorm |

### 3.2 End-to-end duration

Highly variable. A typical test runs **1–6 months** end-to-end, with most landing in the **3–4 month** band. Tests can be much shorter when they're promo-driven (e.g., 3-day windows, repeated across multiple promos to accumulate sample size).

---

## 4. Idea Sources & Brainstorming

Ideas come from **three independent streams** that all feed the same brainstorming cycle:

| # | Source | Cadence | Typical example |
|---|--------|---------|-----------------|
| 1 | **PDM roadmap** | Quarterly, scheduled | "We want to test repositioning the checkout payment buttons this quarter" |
| 2 | **Brand-driven ad-hoc** | Time-sensitive (days to 1–2 weeks) | "Our competitor just launched X — can we test this?" |
| 3 | **Experimentation team's own learnings** | Opportunistic | "We saw a +1.4% lift on Athleta last quarter — should we test on Old Navy?" |

The brainstorming session is **both scheduled** (PDMs work to a roadmap) **and ad-hoc** (brand asks land any day). Findings from prior tests are a first-class input — this is what makes the workflow circular.

---

## 5. Feasibility & Test Build Strategy

Feasibility actually answers two questions:

1. **Technical feasibility** — can the variant be built given platform / code constraints?
2. **Worth-testing decision** — for very small changes (e.g., a font change), the team often skips testing and rolls out directly.

### 5.1 Client-side vs server-side

| Aspect | Client-side | Server-side |
|--------|-------------|-------------|
| Mechanism | Optimizely overrides the page after it loads | Engineering codes the variant into the site / server |
| Build time | Fast | Slow (real engineering effort) |
| User experience | Possible visible "flash" / 1-second delay as override applies | Smooth — variant rendered before the page is served |
| Use case | Quick UI tweaks, simple iterations | Larger features, performance-sensitive variants |

Both are supported. The choice is part of the feasibility / planning conversation.

---

## 6. Test Execution & Measurement

| Activity | Tool |
|----------|------|
| Run the A/B test | **Optimizely** (licensed 3rd-party platform) |
| Capture customer behaviour | Tealium → Adobe Experience Cloud |
| Pull metrics (revenue, conversion, KPI) | **Adobe Customer Journey** (drag-and-drop), some via **Databricks** |
| Run significance tests | **Excel** |
| Power calculation (sample size + estimated duration) | Built into the **Test Plan template** |

Every test is an A/B (or A/B/n) — **no quasi-experiments, no DiD**.

---

## 7. Documentation in Confluence

Each test has two Confluence pages, both inside the **Test and Learn COE** space:

- **Test Plan** — authored *before* the test runs
- **Test Results** — authored *after* the test ends

Both use standardised templates that have been **largely unchanged since 2017** — small evolutions over time, but stable enough that automated parsers work.

The Confluence space contains test results going back to **2017** (visible folders 2017 → 2026 Test Results). It covers approximately **80% of all tests** the team has run; the remaining ~20% live in email, PDF, or PowerPoint deliverables for asks where Confluence wasn't created.

### 7.1 Access

Anyone with a `gap.com` email can read the Test and Learn COE space. In practice PDMs and brand teams **rarely traverse it themselves** — they wait for the experimentation team to bring findings, or ask for a specific page link when a similar test resurfaces. This is one of the core pain points the new GenAI tool addresses.

---

## 8. The Confluence Templates (in detail)

### 8.1 Test Plan page — fields

- Brand
- Page / Funnel / Channel
- Audience Limitation (e.g., All Customers)
- Problem Statement
- Hypothesis
- Experimental Changes — Control vs Challenger description
- Additional Documents — comparison snapshots
- **Significance Calculations & Experimental Design**

| Field | Example |
|-------|---------|
| Brand | Old Navy |
| Scenarios | 1 Control + 1 Challenger |
| Primary KPI | OPV |
| Minimum Detectable Lift | ~0.4% |
| Confidence Threshold | ~80% |
| Power Threshold | 80% |
| Sample Size | ~7.2MM visits per variation |
| Estimated Duration | ~2–3 weeks |
| Sample Size Calc Assumptions | Documented in the page |
| Test Exposure | 100% (50/50 split) |
| Secondary Metrics | Per test |

- Adobe Dashboard Link (Adobe Experience Cloud)
- **Measurement** (4 buckets):
  - Metrics (All Experiments) — Conversion Rate (OPV), Net RPV, AOS, UPT, AUR, Total Visits, Visits Split by Visit/Visitor, Variation Overlap
  - Metrics (Test Specific) — e.g., PDP Views/Visit, Add-to-Bag Rate, PDP→Bag Conversion, PDP Certona Engagement Rate, PDP Exit Rate
  - Segments (All Experiments) — New vs Returning
  - Segments (Test Specific) — Desktop vs Mobile
- **Custom Metrics** — Description / Location, Custom Variable & Name in Analytics, Notes (track once / always / etc.)

### 8.2 Test Results page — fields

- Overview (restated hypothesis)
- Variation Description with Control + Challenger **screenshots**
- DETAILS — directional commentary, statistical significance disclaimer, breakdowns by Device Type and Visit Type
- **Impacts table** — Net RPV · OPV · AOS · UPT · AUR · Product Views/Visit · PDP→SB · Add-to-Bag Rate · Exit Rate · Engagement Rate · Incremental delta row
- Product Mix
- Gross Margin (GMS/Visit)
- Findings summary at the top
- Recommendation
- Optimization Opportunities (these feed the next brainstorming cycle)

### 8.3 Concrete example

A real Test Results page from the corpus: **"[ON WEB + APP] Internal Product Recommendation Model V3 vs V2 on PDP Test — Results"** (last updated Apr 24).

- Hypothesis: Internal Product Recommendation will provide at least the same value as Certona containers on PDP.
- Control: PDP Internal Rec Model V2 · Challenger: PDP Internal Rec Model V3.
- Outcome: directional negative impact on Net RPV (~−1.1%), driven by a ~−0.9% conversion drop. Engagement on recommendation containers was similar between groups.
- Findings: not statistically significant; flat-to-slightly-negative on Desktop, flat-to-slightly-positive on Mobile.

---

## 9. The SharePoint Experimentation Catalog

A flat list — **one row per test** — that acts as the index of every experiment. Maintained manually by the analyst at the end of each test.

### 9.1 Fields

Test Name · Test Description · Brand · Market · Source · Start Date · End Date · Platform · Device · Channel · Channel Section · Audience · Vendor · Primary KPI · Other KPI · Other KPI — Winning / Losing Delta · Estimated Annualized Value (input) · Recommendation · Confluence Result Link · Recommendation Adopted · Test Insights · Return Rate · Attachments

### 9.2 Standard views (statuses)

- **All Items**
- **Closed Tests** (with an outcome: Win / Loss / Flat)
- **Inflight** (planned, not yet started)
- **Live** (currently running)

The SharePoint list is the **source of truth for dashboard metadata** — every dashboard tile and filter ultimately reads from this list.

---

## 10. Reporting — Power BI Dashboard & Excel Pivots

### 10.1 Power BI dashboard ("Gap Inc Experimentation Control Center")

A stopgap dashboard built by Aditya's team. Top tiles:

| Tile | Example value |
|------|---------------|
| Total Tests | 490 |
| Needs Attention | 10 (closed but missing outcome) |
| Incremental Revenue | $220M |
| Averted Revenue Loss | -$144M |

Three columns underneath: **Closed Tests (427)** / **Live Tests (31)** / **Inflight Tests (22)** with the latest 3 in each list.

**Drill-down view** has:
- Filters: Start / End Date · Brand · Market · Source · Platform · Device · Channel · Channel Section · Audience · Vendor · Primary KPI · Other KPI · Tactic · Recommendation Adopted
- Counters: Closed Tests / Wins / Losses / Incremental Revenue / Averted Revenue Loss
- **Program Insights** pane (text bullets — e.g., "Out of 79 closed tests, 14 wins vs 12 losses…")
- **Test Insights** pane (per-test summary, e.g., the BOPIS bag-simplify test result)
- **Result Breakdown** donut (Flat 67% / Win 18% / Loss 15%)

This dashboard is being **replaced** by the new GenAI app's dashboard view.

### 10.2 Excel pivot routine (David, every 3–4 weeks)

David maintains an Excel workbook with sheets per brand (`AT Records`, `BR Records`, `GP Records`, `ON Records`, `PDM Records`) and a `PIVOTS` sheet that classifies tests by **tactic** and **outcome**. Representative output:

| Tactic | Win | Loss | Flat |
|--------|-----|------|------|
| Quality | 21% | 7% | 72% |
| Time Savings | 43% | 9% | 48% |
| Urgency | 0% | 100% | 0% |
| Value | (variable) | 13% | 67% |

This pivot is the input for David's monthly executive narrative.

---

## 11. Outcome Classification

| Outcome | Meaning | What happens next |
|---------|---------|-------------------|
| **Win** | Variant has a positive, statistically significant impact on the target KPI | Roll out to 100% of customers |
| **Loss** | Variant has a negative impact | Do NOT roll out — counted as **"averted revenue loss"** |
| **Flat** | No statistically significant difference | Most tests fall here. Often tested again later with refinements or in a different brand context |

---

## 12. Tactic Categories

Used by David's pivot to classify every test:

| Tactic | Examples |
|--------|----------|
| **Quality** | Improvements to product / feature quality (e.g., review modules, content) |
| **Time Savings** | Reduce friction or steps (e.g., simplified bag, single-page checkout) |
| **Urgency** | Drive faster action (e.g., countdown timers, scarcity messaging) |
| **Value** | Pricing, promos, perceived value (e.g., free-shipping thresholds) |

---

## 13. Cross-Brand & Repeated Tests

### 13.1 Same test, different brand

The same test is **frequently rerun across brands** because customer bases differ:

- Athleta + Banana Republic — premium customers
- Old Navy + Gap — discount-focused customers

Rules of thumb:

- **Trivial change** (font size, copy tweak) — tested once, rolled across brands
- **Funnel-critical change** (Bag, Checkout) — **tested per brand** because customer behaviour diverges meaningfully

### 13.2 Same test, same brand, repeated over time

Common for **promo-driven tests** (e.g., 50% off vs 80% off). Each promo window is too short for sample size, so the same test is repeated at intervals (e.g., every 2 weeks over a month).

### 13.3 Implication

When looking at the corpus, "the same idea" can show up as 3–8 distinct Confluence pages across brands and time. Any tool that summarises across the corpus must handle this multiplicity.

---

## 14. Metrics — Standard & Test-Specific

### 14.1 Always tracked

| Metric | Notes |
|--------|-------|
| Conversion Rate (OPV) | Primary KPI for many tests |
| Net RPV | Revenue per visit |
| AOS | Average Order Size |
| UPT | Units Per Transaction |
| AUR | Average Unit Retail |
| Total Visits | |
| Visits Split by Visit/Visitor | |
| Variation Overlap | Customers exposed to multiple variants |

### 14.2 Test-specific (examples for a PDP test)

PDP Views Per Visit · Add-to-Bag Rate · PDP → Shopping Bag Conversion · PDP Certona Engagement Rate · PDP Exit Rate

### 14.3 Filtering for stakeholders

The team looks at **all funnel metrics internally** but **only shares page-relevant metrics** with brands — e.g., for a PDP test, only PDP-relevant metrics — to avoid information overload. Filtering happens at the experimentation team's end.

### 14.4 New / unfamiliar metrics

Occasionally a new metric is introduced for a specific test (e.g., "Gross Margin Dollar per Visit"). Brands need a definition the first time they encounter it. There is currently **no shared metric definitions glossary** — brands ask the experimentation team and the answer is given verbally.

---

## 15. Volumes & History

| Metric | Value |
|--------|-------|
| Lifetime experiments | ~1,500 (last 6–7 years, 2017 → present) |
| FY 2025 | 450–490 closed tests |
| FY 2026 (so far) | 20–30 tests |
| Two-year window | ~700 tests |
| Confluence coverage of all tests | ~80% (rest in email / PDF / PPT) |
| Closed tests in latest dashboard snapshot | 427 |
| Live tests in latest dashboard snapshot | 31 |
| Inflight tests in latest dashboard snapshot | 22 |

---

## 16. Tools & Platforms in the Stack

| Tool | Role |
|------|------|
| **Optimizely** | A/B test execution (client + server side) |
| **Adobe Experience Cloud / Adobe Customer Journey** | Primary measurement & dashboarding |
| **Tealium** | Tag management feeding Adobe |
| **Databricks** | Deeper analytics on test outputs (Greg Christensen owns) |
| **Confluence (Test and Learn COE space)** | Canonical home of Test Plans + Test Results |
| **SharePoint Experimentation Catalog** | Metadata index (one row per test) |
| **Excel** | Significance testing + David's tactic pivot |
| **Power BI Dashboard** | Stopgap "Experimentation Control Center" — being replaced |
| **Email / PDF / PowerPoint** | Used ad-hoc for ~20% of tests where Confluence wasn't created |

---

## 17. Pain Points (today)

| # | Pain | Who feels it |
|---|------|--------------|
| 1 | **Discoverability** — 1,500 Confluence pages exist, no one knows what's collectively in them | PDMs, brand teams, executives, newer analysts |
| 2 | **Institutional memory in two heads** — only David and Prateek can recall older tests confidently | The whole org |
| 3 | **Self-service search is impossible today** — PDMs and brand teams don't traverse Confluence on their own; they wait for the experimentation team | PDMs, brand teams |
| 4 | **Cross-test recall is manual** — designing a new test means manually trawling years of Confluence | Experimentation team |
| 5 | **Insights live in unstructured prose** — current dashboard / pivot can only do simple metadata aggregations | Executives ("what's working?") |
| 6 | **No metric definitions glossary** — newly introduced metrics need verbal explanation each time | Brands, new joiners |
| 7 | **Possible duplicate tests** — unclear if same test gets re-run unintentionally across teams (open question) | Unknown |
| 8 | **Manual SharePoint row entry + manual Excel pivoting every 3–4 weeks** | David, analysts |
| 9 | **~20% of tests live outside Confluence** — visible-only to whoever has the email / deck | The whole org |

---

## 18. Constraints & Conventions

These reflect explicit positions stated by David / Prateek and that any tooling around the program **must respect**.

| # | Constraint |
|---|------------|
| 1 | The **human writes the Test Results write-up**. This is not to be automated. |
| 2 | All experiments are **A/B (or A/B/n)** — no quasi-experiments, no DiD. |
| 3 | The Confluence template is the **canonical artefact**. Other formats (PPT, PDF, email) exist but are not standardised. |
| 4 | **Phase 1 of any tooling = Confluence-only** — the ~20% non-Confluence content is deferred. |
| 5 | **Insights ≠ Recommendations.** Forward-looking "what should I test?" is a future capability, not part of today's program. |
| 6 | **Digital and in-store are separate tracks** with different owners. |
| 7 | **PDMs are the intended single intake channel** going forward, but brand-driven ad-hoc requests still flow today. |
| 8 | **Recommendations Adopted** is tracked separately and is a real KPI for the program. |

---

## 19. Glossary

| Term | Meaning |
|------|---------|
| A/B test | Experiment with a Control and one or more Challenger variants |
| Adobe Customer Journey | GAP's primary customer-behaviour analytics tool |
| AOS | Average Order Size |
| AUR | Average Unit Retail |
| Averted revenue loss | $ value of NOT rolling out a losing variant |
| Brainstorming | The kickoff stage where ideas are generated; circular — fed by prior learnings |
| Challenger | The variant being tested against the Control |
| Client-side test | Optimizely overrides the rendered page after load |
| Closed test | Completed test with an outcome (Win / Loss / Flat) |
| Confluence | Atlassian wiki — canonical home of Test Plans + Test Results |
| Control | The current production experience |
| Estimated Annualized Value | Projected $ if a winning variant rolls out at scale |
| Experimentation Catalog | The SharePoint list with one row per test |
| Flat | No statistically significant impact (most common outcome) |
| Inflight test | Planned but not yet started |
| Live test | Currently running |
| Loss | Negative outcome — variant not rolled out |
| MDE | Minimum Detectable Effect — smallest effect size the test is powered to detect |
| Net RPV | Net Revenue Per Visit |
| OPV | Order Placement / Conversion Rate KPI |
| Optimizely | Licensed 3rd-party A/B testing platform |
| PDM | Product Decision Maker |
| Power threshold | Statistical power target for the test (typically 80%) |
| Recommendation Adopted | Whether a test's recommendation was actually rolled out |
| Sample size | Visits per variation required to hit MDE at the chosen confidence + power |
| Server-side test | Variant rendered before page load (engineered into the app) |
| Tactic | Test category — Quality / Time Savings / Urgency / Value |
| Test Plan | Confluence page authored before a test runs |
| Test Results | Confluence page authored after a test ends |
| UPT | Units Per Transaction |
| Value stream | New GAP grouping by site section (PLP / PDP / Bag / Checkout) |
| Win | Positive outcome — variant rolled out |

---

*This is the standalone As-Is reference for GAP's current A/B testing program. For the GenAI / RAG project that builds on top of this program, see [Project_Documentation.md](Project_Documentation.md), [GCP_RAG_Architecture.md](GCP_RAG_Architecture.md), and the variant deep-dive in [Vertex_AI_Search_Variant/](Vertex_AI_Search_Variant/) (`Architecture.md`, `Backend_Developer_Guide.md`, `Frontend_Developer_Guide.md`).*
