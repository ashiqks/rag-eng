# Meeting 3 — Tool Walkthrough (Optimizely + Adobe Analytics)

> **Date**: 2026-05-07
> **Type**: Tool walkthrough session
> **Host**: Prateek (GAP Experimentation team)
> **Attendees**: Soumya, Atul, Kaushik (Mathco / consulting team); Prateek (GAP)
> **Duration**: ~45 min
> **Focus**: How A/B tests are actually set up (Optimizely) and measured (Adobe Analytics), plus closing alignment on personas, sample queries, focus group, and access provisioning.

---

## 1. One-line summary

Prateek walked the team through the **end-to-end mechanics of a live A/B test at GAP** — campaign setup in Optimizely (client-side vs server-side), Optimizely → Adobe integration, segment + metric analysis in Adobe Analytics, and how results flow back into the Confluence write-up. Closed with confirmation that the GenAI tool's day-1 user base will be **10–20 people**, primarily PDMs + brand partners + analysts + leadership, mostly desktop.

---

## 2. Key takeaways

| # | Takeaway | Implication for the GenAI POC |
|---|----------|-------------------------------|
| 1 | Two test types: **client-side** (fast, JS injected by Optimizely) and **server-side** (slower, requires backend code change) | No POC change — both end up in Confluence the same way |
| 2 | **PDMs own server-side test setup**; David's team helps validate client-side setup | Confirms PDM as a primary persona for the chatbot |
| 3 | Optimizely → Adobe integration is a **single checkbox** in the campaign; without it no test data flows to Adobe | Out of scope for our tool, but useful context for any future "test health" check |
| 4 | **Optimizely cannot split metrics by brand** in cross-brand checkouts → all brand-level analysis happens in Adobe via Optimizely-cookie segments | Reinforces why brand-level metadata in Confluence write-ups is the *only* clean source for brand-level retrieval |
| 5 | **Statistical significance is computed outside both tools** (Excel / online calc / SQL), with a **mid-point check** as the standard practice | Good to capture in metadata schema (`outcome`, `significance_reached_at` if available) |
| 6 | **Metrics evolve during the test** — analyst keeps adding break-downs as questions come up; this does *not* invalidate results, it's just deeper segmentation | The chatbot must surface the *final* documented metrics, not intermediate ones |
| 7 | **80–90% of test results land in Confluence**; the remaining **10–15%** stay in **email or PowerPoint** (usually leadership-facing tests) | The PPT/email gap (~10–15%) is a known Phase-1 blind spot — already captured as Constraint C2 |
| 8 | Day-1 user base estimate: **10–20 users**; growth driven by adoption | Matches our POC sizing (5–20 users) — no infra change needed |
| 9 | Primary device = **desktop**; iPad / mobile responsiveness is a "park for later" item | We can scope mobile to Phase 2 |
| 10 | Personas confirmed: **Leadership, PDMs, Brand partners (within ecosystem), Experimentation analysts** | Add "Brand partners" explicitly to persona list (was implicitly under PDM/Brand) |

---

## 3. Confirmed Persona Set

| Persona | Source of need | Primary surface |
|---------|----------------|-----------------|
| **Leadership / Executives** | "What's the program doing?" | Dashboard View |
| **PDMs** | "Has anyone tested this before?" | Chatbot |
| **Brand partners (in-ecosystem)** | Ad-hoc test ideas / lookups | Chatbot |
| **Experimentation analysts (David's team)** | Cross-test recall when designing new tests | Chatbot |

---

## 4. Open items / Next actions

| # | Action | Owner | Due |
|---|--------|-------|-----|
| A1 | Share **sample user queries** per persona for validation | Mathco team → Prateek/David | Next week |
| A2 | Share **interview questionnaire** per persona | Mathco team → Prateek/David | Next week |
| A3 | Identify **focus-group participants** (1–2 per persona, ideally same people across feature releases) | David Rose | Next week |
| A4 | Connect Mathco team with **Greg Christensen** for data API / warehouse code guidelines | Prateek | This week |
| A5 | Provision **GAP contractor IDs + MyIdentity + Ping MFA** for 7 more team members | Atul + Kaushik | In progress |

---

## 5. Updates to existing project artefacts

- **GenAI_Design_Document.md §1.1 / §4.22** — persona list refined to include *Brand partners (in-ecosystem)* alongside PDMs.
- **Project_Documentation.md** — confirm 10–20 day-1 users (no change to sizing).
- **Infra_Provisioning_Day1.md** — no change; sizing already aligned.

For the full transcript and component-level findings, see [Meeting_Details.md](Meeting_Details.md).
