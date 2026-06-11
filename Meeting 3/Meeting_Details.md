# Meeting 3 — Detailed Notes (Tool Walkthrough: Optimizely + Adobe Analytics)

> **Date**: 2026-05-07
> **Source**: `20260507 - GAP ERD - Tool Walkthrough Session with Prateek-en-US.docx` + screenshots in this folder
> **Host / SME**: Prateek (GAP Experimentation team)
> **Attendees**: Soumya, Atul, Kaushik (Mathco); Prateek (GAP)
> **Duration**: ~45 min
> **Purpose**: Close out the open ends from Meeting 1 + 2 by walking through the *actual tools* used to set up and measure A/B tests at GAP, so the GenAI POC team knows exactly where the source data comes from, what's deterministic, and what's analyst-judgement.

For a one-page summary see [Meeting_Overview.md](Meeting_Overview.md).

---

## 1. Optimizely — Test Setup

### 1.1 Suites and brand isolation

- Optimizely is organised into **separate suites per brand** (Athleta Marketing, Banana Republic, Old Navy, Gap, plus server-side variants per brand).
- A test is set up inside the suite of the brand that owns it.
- Suites visible in the screenshot include: *Profile UI [Development]*, *Profile UI [Production]*, *Reco-ML Experiments*, *Server-Side Experimentation [Development] / [Production]*, *Server-Side Experimentation Factory [Development] / [Production]*, *Server-Side Experimentation CA [Dev] / [Prod]*, *ServiceWorker Optly*, plus legacy projects.

### 1.2 Client-side vs server-side

| Dimension | Client-side | Server-side |
|-----------|-------------|-------------|
| Speed to launch | Fast | Slow |
| Where the change lives | JS injected by Optimizely at runtime | Backend code change in GAP's site code |
| Who sets it up | Developer (often) — David's team validates | **PDM owns it** |
| Visibility to David's team | Helps with setup + validates | Not touched much |

> **Implication for GenAI POC**: both flavours land in Confluence the same way after analysis, so retrieval doesn't need to distinguish them. We *could* surface "test type" as a metadata field if Confluence templates capture it.

### 1.3 Campaign anatomy

Inside each campaign:
1. **Variations / panels** — Holdback (0%), Variation #1 (100%), or arbitrary splits (50/50, multi-arm, personalisation, swim-lanes, waterfall).
2. **Variation code** — added by the developer; brands QA in the dev/stage preview before go-live.
3. **Targeting / Activation** — defines which pages of the site the experiment runs on (e.g., PDP only).
4. **Integrations checkbox** — single toggle that pushes Optimizely cookies into Adobe Analytics. **If unchecked, no test data flows to Adobe.** Critical and easy to miss.
5. **Schedule** — start/stop date-time (e.g., "scheduled to start May 13 12:00 AM, stop June 8 11:59 PM, America/Los Angeles") or manual start/stop.

### 1.4 Statistical significance

- Optimizely *has* a built-in significance feature, but **GAP cannot use it** because the platform allows **cross-brand checkout** (a basket can contain Banana + Gap + Old Navy + Athleta items). Optimizely sees only the aggregate basket, so it can't attribute brand-level metrics correctly.
- **Significance is therefore computed outside Optimizely** — Excel, an online calculator, or SQL — using the cleaned segment data from Adobe.

---

## 2. Optimizely → Adobe Integration

- One toggle in Optimizely ("Integrations" checked) creates the linkage.
- Once a test is live, **data lag is ~1 hour** before Optimizely cookies start flowing into Adobe.
- In Adobe, **two cookie variables** are exposed:
  - `AB Test Client-Side (lv2)` — captures the client-side Optimizely cookie value.
  - A separate **server-side cookie variable** — captures server-side experiences.
- Analysts read these cookie values to **build segments** representing Control and Challenger groups (often 4+ cookie combinations per arm to fully define a group).

> **Implication for GenAI POC**: this plumbing is invisible to our retrieval — we're consuming the *Confluence write-up* that summarises the analyst's final answer. But it's worth noting that "no Adobe data" is one of the failure modes that would show up in the Confluence page as "test invalidated" or similar.

---

## 3. Adobe Analytics — Measurement

### 3.1 The Workspace project

The screenshot shows a live Workspace project: `[BR US + BRFS] Acquisition Bubble V3 Test`, project root *Banana Republic Factory US — Production*.

Top section: **KPI tiles** (the "executive view" the analyst exposes to brand partners):
- Net RPV Change ▲ 0.0%
- OPV Conversion Change ▼ 0.9%
- Total Net Demand Change ▲ 0.1%
- Total Visits Change ▲ 0.1%
- Email ▲ 2.8%
- SMS ▼ 0.2%

Below: a **`Primary_A` table** broken by segment (Control vs Challenger) with Visits, Orders, Net Demand [Approved], Net RPV, Conversion Rate, Net AOS — each with a sparkline trend across the test window (Apr 23 — May 30, 2026).

Filter strip across the top: *Return vs New Visits*, *Segment* (Global Blanket Correction Segment [Approved]), *Device Type*, *Page Type*, *Extreme Orders* (COE - Exclude Extreme), with reset and drag-to-filter affordances.

### 3.2 Metric strategy

| Bucket | Always included | Test-specific |
|--------|-----------------|---------------|
| Primary | Revenue, Conversion, Basket size | — |
| Funnel | Visits, exits, entry pages | Only the funnel pages the test actually touches |
| Engagement | Search engagement, PDP element interaction | Only when relevant |

- Analyst pulls from a library of ~200 metrics; **shares only the 10–30 relevant to the test** with the brand partner — to avoid information overload.
- During the test, the analyst **adds break-downs as questions arise** (device, loyalty tier, product style, women's dresses subset, etc.). This does *not* affect the experiment integrity — it's post-hoc segmentation over already-collected data.

### 3.3 Mid-point check (standard practice)

- The **Test Plan page** in Confluence captures the *estimated duration* and *expected sample size*.
- The analyst does a **mid-point check** to see if metrics are trending in the expected direction. If flat or wrong-direction, deeper drill-down begins (device, loyalty tier, product style, etc.).
- Daily checks happen "if time allows" but daily noise is too high to act on — the mid-point check is the formal milestone.

### 3.4 Visualisation

- Adobe doesn't auto-flag significance; the analyst hand-builds visuals (bar / line / Venn / metric tiles) per their preference.
- "There is no right or wrong visual" — preference-driven.
- Significance is calculated outside (see §1.4).

---

## 4. From Adobe → Confluence (or PPT / email)

| Path | Share | When used |
|------|-------|-----------|
| **Confluence write-up** (standard template) | **80–90%** | Default; what we are indexing |
| **PowerPoint deck** (linked into Confluence as an attachment, or stood alone) | ~10% | Leadership-audience tests |
| **Email-only** | ~5% | Time-pressured turnaround; no formal write-up |

- Export from Adobe is via **CSV download** or copy-paste into Excel; no automated handoff.
- Some analysts (e.g., David) build the report directly inside Adobe Workspace; others (e.g., Prateek) prefer Excel for additional formula-based analysis.
- **Template uniformity**: the Confluence template is the same across the team — that's why deterministic metadata extraction (§4.2 of the design doc) is feasible.
- **The 10–15% PPT/email gap** is a known blind spot for the chatbot in Phase 1 — it's already captured in the design doc as Constraint **C2** (~80% Confluence coverage).

---

## 5. User Personas (re-confirmed)

| Persona | Behaviour today | What they need from the chatbot |
|---------|-----------------|--------------------------------|
| **Leadership / Executives** (Aravindhan, VPs, SVPs) | Look at PowerBI stopgap dashboard, ask analysts ad-hoc | Dashboard tiles + drill-through; chatbot for "summarise this program" questions |
| **PDMs** | Reach out to David's team to ask "have we tried X?" | Self-service chatbot search with citations, before they escalate |
| **Brand partners (in-ecosystem)** | Ad-hoc requests through PDMs or directly to David | Same chatbot — natural-language lookup of past tests by brand / page / tactic |
| **Experimentation analysts (David's team)** | Search Confluence + Adobe themselves; institutional memory | Cross-test recall to find prior cross-brand variants when designing a new test |

> **Brand partners** is now an explicitly-named persona (was previously folded into "PDM/Brand"). Update §1.1 of the design doc accordingly.

---

## 6. Sample Queries (Prateek's directional examples)

These are the kinds of prompts the chatbot should handle on day-1:

1. *"Have we done this particular test in the past?"*
2. *"If yes, for which brand did we do it?"*
3. *"Can you summarize the findings for those brands?"*
4. *"What were the recommendations from the last time we tested X on PDP?"*

The Mathco team will produce a **per-persona sample-query set** for Prateek + David to validate (action **A1**).

---

## 7. Adoption + Device Expectations

| Question | Prateek's answer |
|----------|-----------------|
| Day-1 user count | **10–20**, growing with adoption |
| Primary device | **Desktop** |
| iPad / mobile | "Park for later" — to be probed in user interviews |
| Throughput | Tens of queries/day at most in the pilot — no infra concerns |

Confirms the POC sizing of **5–20 users** in [Infra_Provisioning_Day1.md](../Infra_Provisioning_Day1.md) — no change required.

---

## 8. Process gaps Mathco surfaced (still open)

| # | Gap | Status |
|---|-----|--------|
| G1 | 10–15% of test results never reach Confluence (PPT/email-only) | Acknowledged; out of Phase 1 scope (Constraint C2) |
| G2 | No formal trigger that a test result is "ready" — write-ups appear when the analyst gets to them | Will be probed in Phase 1 user interviews |
| G3 | Significance computation lives in spreadsheets / notebooks outside the system | Out of POC scope; metadata only captures the *outcome*, not the calculation |

---

## 9. Action items (recap)

| # | Action | Owner | Due |
|---|--------|-------|-----|
| A1 | Share **sample user queries** per persona | Mathco → Prateek/David | Next week |
| A2 | Share **interview questionnaire** per persona | Mathco → Prateek/David | Next week |
| A3 | Identify **focus-group participants** (1–2 per persona, sticky across releases) | David Rose | Next week |
| A4 | Connect Mathco with **Greg Christensen** (warehouse / data API standards) | Prateek | This week |
| A5 | Complete **MyIdentity + Ping MFA provisioning** for 7 more contractors | Atul + Kaushik | In progress |

---

## 10. Cross-references

- High-level summary: [Meeting_Overview.md](Meeting_Overview.md)
- Word transcript: `20260507 - GAP ERD - Tool Walkthrough Session with Prateek-en-US.docx`
- Plain-text transcript: `transcript_extracted.txt`
- Screenshots: `Screenshot 2026-05-11 110837.png` (Optimizely projects), `Screenshot 2026-05-11 111114.png` (Adobe Workspace KPIs), `Screenshot 2026-05-11 112237.png` (Optimizely campaign experiences)
- Related design context: [GenAI_Design_Document.md](../GenAI_Design_Document.md) §1.1, §1.2 (Constraints C2, C7)
