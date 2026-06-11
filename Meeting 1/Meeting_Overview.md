# GAP Experimentation Discoverability — Meeting Overview

> **Meeting**: GAP - Experimentation Discoverability Walkthrough
> **Date**: April 28, 2026 · 3:04 AM · 1h 0m 55s
> **Attendees**: Aditya Govind Ravikrishnan (presenter), Syed Muzaffar J, Kaushik B, Athul Babu, Nithin Chandra, Nilim Borah

---

## 1. Purpose of the Meeting

A walkthrough by Aditya to give the offshore delivery team **full context** on the GAP Experimentation Discoverability project before kickoff. The team had only minimal context from a prior conversation with Bansi and Atul. The session covered the customer's business, the current pain points, the proposed solution, scope, stakeholders, timelines, and immediate next steps.

---

## 2. Customer Context (One-Liner)

GAP Inc.'s **Test and Learn organization** runs ~500 A/B experiments per year across digital surfaces (web, app, desktop, email, store). Today the experiment knowledge sits in **~1,500 Confluence pages** plus Excel/SharePoint metadata — making it hard for leadership and product teams to discover what was tested, what won/lost, and what the learnings were. The institutional knowledge effectively lives in the heads of two people (David and Pratik).

---

## 3. Project Goal

Build a **web application with a chatbot interface** that:
- Makes 1,500+ historical A/B experiments **discoverable** via natural-language search
- **Summarizes insights and learnings** from related past tests
- Surfaces **basic recommendations** based on historical patterns (e.g., "5 similar tests were run, 4 won, 1 was flat")
- Replaces the existing Power BI dashboard / SharePoint list as a single discovery surface

---

## 4. Two Phases

| Phase | Scope |
|-------|-------|
| **Phase 1 (Committed — 4 months)** | Discoverability + summarization + low-level (Level 1/2) insights from historical tests |
| **Phase 2 (Future)** | Forward-looking recommendations on what to test next; tracking of scaled-up experiments post-win |

---

## 5. Key Stakeholders

| Person | Role | Notes |
|--------|------|-------|
| **Aravindhan** | Senior leader | Everything rolls up to him; strategic sponsor |
| **David Rose** | Director, Test and Learn | **Primary day-to-day customer contact**; owns digital, customer, and store tests |
| **Pratik Oberai** | Senior Manager, Test and Learn | Works under David |
| **Holly** | Aditya's manager (GAP side) | Less time-pressure-driven |
| **PDM teams / Brand teams / App owners** | Test requestors | Submit experiment ideas to David's team |

---

## 6. The Current (Manual) Process

```
PDM/Brand idea → David's team designs A/B test → Optimizely runs the test (1-6 months)
                       ↓
   Results pulled from Adobe Customer Journey / Databricks → Excel for significance test
                       ↓
   Analyst writes Confluence report (hypothesis, control vs challenger, results, learnings)
                       ↓
   Row added to SharePoint list (metadata: brand, market, KPI, win/loss, $ impact)
                       ↓
   Power BI dashboard (current "stopgap solution") displays aggregates
```

**Outcomes**: Win / Loss / Flat (most are Flat). Tactic categories: Quality, Time Savings, Urgency, Value.

---

## 7. Solution Approach (As Discussed)

- **Source of truth**: Confluence reports (~500 in the FY25/26 window; ~1,500 lifetime)
- **Data layer**: GCP (per customer mandate — strategic shift to Google in next 6–7 months)
- **Pipeline**: Confluence → GCP Storage → vector store + structured store
- **Front-end**: Web application with **chatbot as primary interaction** + dashboard view as secondary surface
- **User personas**: Executive view (high-level metrics) + Analyst/PDM view (search and discovery)
- **Phase 1 scope limitation**: Image content in Confluence will NOT be parsed/searchable (text only)

---

## 8. Key Decisions / Alignments

1. **Scope to FY25/26 confluences first** for tuning (~500 tests), then extend to all 1,500 once pipeline is stable
2. **Chatbot is the landing experience** for PDM/analyst persona; dashboard summary for executive persona
3. **Insights ≠ Recommendations** — Phase 1 delivers summarization + Level 1 insights from historical data; Phase 2 will add forward-looking "what to test next" recommendations
4. **Web app over Nucleos** — Nucleos had issues in the GAP environment
5. **Image extraction is OUT of scope** for Phase 1 (called out as a documented limitation), but team agreed to experiment with it as a stretch
6. **Internal POV**: Solution can be delivered faster than the SOW estimate; team will overdeliver where possible without over-promising

---

## 9. Team Structure (Offshore, 1+7)

| Role | Identified | Status |
|------|-----------|--------|
| Offshore Lead | Kaushik B | Confirmed |
| Designer | (1 onboarded — name TBD) | Onboarded |
| Resource | Nilim Borah | Confirmed |
| 6 more resources | TBD | Pending DelOps |

**Onsite touchpoints**: Aditya (San Francisco), Athul (Sunnyvale), Syed (traveling to Atlanta — Coke client).

---

## 10. Timeline

- **Project start**: ~May 4, 2026
- **Phase 1 target**: ~September 4, 2026 (4 months per SOW)
- **Kickoff with customer**: Monday or Tuesday next week (May 4–5, 2026)
- **First 2–3 weeks focus**: Design discussions + GCP/Confluence access + pipeline build
- **AI engineers and front-end devs**: brought in after design is locked

---

## 11. Immediate Next Steps

| Owner | Action |
|-------|--------|
| Kaushik / Nilim / Athul | Prepare kickoff deck |
| Kaushik | Raise IT request for Teams group + SharePoint |
| Athul | Share full names + phone numbers for GAP ID provisioning |
| Aditya | Raise GAP IDs (via David, not Holly); share onboarding doc; share Excel artifacts |
| Syed | Identify remaining 6 offshore resources by end of week |
| Team | Schedule customer kickoff for Mon/Tue next week |

---

## 12. Risks Called Out

- **GCP access** is the longest-pole dependency (Aditya hasn't worked on GCP in GAP environment yet)
- **Image-in-Confluence** parsing is hard; flagged as out-of-scope for Phase 1
- **Ambiguity on "recommendations"** — must align with David that Phase 1 is summarization + Level 1 insights only
- **Aravindhan's timeline expectation** unclear — David and Holly are flexible, but the executive sponsor may not be
- **Project is "ours to lose"** — high visibility, high usability bar
