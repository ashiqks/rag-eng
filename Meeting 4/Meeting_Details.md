# Meeting 4 - Analytics User Interview (ERD Senior Analyst Persona)

> **Date**: 2026-05-13
> **Type**: Persona user interview - Senior Analyst (ERD = Experimentation Report Discoverability)
> **Host / SME**: Prateek Oberoi (GAP, Senior Analytics Manager)
> **Attendees**: Sowmiya, Athul, Kaushik, Nilim (Mathco / consulting team); Prateek (GAP)
> **Duration**: 38 min
> **Focus**: Validate the senior-analyst persona (responsibilities / challenges / outcomes), then walk Prateek through the WIP Figma Hi-Fi and capture his expectations for search, result cards, summaries, and the AI chatbot.

---

## 1. One-line summary

Sowmiya walked Prateek through the **Mathco-built persona model** for the *Senior Analyst* and the **Experiment Intelligence Hub** Hi-Fi. Prateek validated the persona (levels don't matter - scope changes, flow stays the same), confirmed that **search will be the workhorse** with **minimal-wording prompts + click-to-fill helpers**, asked for a **1-2 line "learning / recommendation"** on each result card, **rejected** a Glean-style aggregated answer (bad search -> bad summary), confirmed **RBAC is NOT required** (all Confluence pages are open to any GAP ID), and committed the **WBR cadence** + the **PM / Brand Manager interview list** for follow-up.

---

## 2. Key takeaways

| # | Takeaway | Implication for the GenAI POC |
|---|----------|-------------------------------|
| 1 | **Persona levels don't matter** - junior/senior analysts run the same flow, only scope/volume differs. | One persona = "Senior Analyst" covers the whole analyst track; no role-tier splits needed in the app. |
| 2 | Constant tool-switching (Optimizely + Adobe) is a fact-of-life, **not a problem we need to solve**. It is a one-time per-test setup. | Drop "tool unification" from the analyst's challenge list - it's out of scope. |
| 3 | Three search triggers: (a) PM/PDM asking for past-test context, (b) Brand partner asking "did we test this on Banana?", (c) Internal re-check after several years (customer behaviour drifts). | Search must support brand + site-section + year filters AND free-text recall - all three personas use the same query box. |
| 4 | **Confluence page titles are NOT consistently named.** Brand prefix is *mostly* enforced; tags/labels are optional and analyst-applied retroactively. | Cannot rely on the title alone for retrieval. Embeddings + structured metadata fields (from the Confluence template tables) are required. |
| 5 | **Ideal search UX = minimal wording + click-to-fill helpers** ("give me winners from past 5 years", "all Old Navy tests on PDP", "category page facets"). | Add a **suggested-prompts row** under the search bar; persona-aware suggestions if possible. |
| 6 | **Result cards must include a 1-2 line "learning / recommendation"** alongside the standard metrics (lift, AOV, confidence). Click-through still goes to full Confluence. | Add `learning_snippet` to the Confluence-extracted metadata; render on the card. |
| 7 | **Glean-style aggregated summary across multiple cards is NOT wanted.** Quote: *"if your search is done incorrectly, the learnings that you're going to get on top will be incorrect."* | Keep the chatbot's answer **per-experiment** in Phase 1. Re-evaluate aggregated answers only after retrieval precision is proven. |
| 8 | **Page-level segmentation NOT needed** ("for PMs, show X; for leadership, show Y"). Prateek says everyone sees the same Confluence page and self-selects summary vs. detail. | Skip persona-conditional rendering on the results page; one canonical view per result. |
| 9 | **Common chatbot queries map to existing SharePoint columns**: site-section (PLP / PDP / search / shopping bag / checkout), device (app / web / desktop), brand, time-window. | Build the seed-prompt library directly from those columns. |
| 10 | **Trust = depends on response quality, not extra UI guardrails.** Prateek expects mixed/wrong answers to *be the* adoption killer; he is happy with the simple "link to the Confluence page" trust mechanism we already have. | No extra "human review" gating needed for POC; invest in retrieval precision + the "view source" link. |
| 11 | **RBAC is NOT required.** All Confluence experiment pages are open to anyone with a GAP ID (one PDM owns a section across **all four brands**, so cross-brand visibility is already the norm). | Confirms our Phase-1 decision to keep ACLs at the corporate-SSO boundary only. |
| 12 | **PMs and Brand Managers will be exploratory users**, possibly asking at every test stage; senior analysts will be more deterministic. | The two follow-up persona interviews (PM, Brand Manager) are now the next biggest unknown. |

---

## 3. Persona model - Senior Analyst (validated)

| Section | Validated content |
|---------|-------------------|
| **Role** | Analytics Manager / Senior Data Scientist supporting multiple teams across all four brands. |
| **Responsibilities** | (1) Get an experiment briefing from PM/PDM, (2) set up + monitor the test, (3) analyse results, (4) write recommendations and share with PMs / Brand / Leadership. |
| **Challenges** | (1) Inconsistent naming in Confluence, (2) past tests hard to recall when new joiners arrive, (3) repeated "did we test this on Banana?" asks, (4) tool switching (Optimizely + Adobe) - **accepted, not a friction**. |
| **Outcomes wanted** | (1) Fast, accurate recall of past tests with high-level learning. (2) Self-service for non-analyst partners so the senior analyst is not the human search engine. |
| **Product features to validate** | Search, result cards, summary view, chatbot. (See sections 5-8 for Prateek's feedback on each.) |

---

## 4. Three search triggers (verbatim)

1. **PM / PDM building a roadmap**: *"did we do this test in the past?"* - if yes, what were the findings, so they know whether to re-run.
2. **Brand partner cross-brand check**: *"if they want to try to run it on Banana, they want to understand if that test has been run on any other brand"*. Cross-brand precedence is the most common variant.
3. **Internal time-decayed re-check**: *"sometimes we tested something four years back, but now things have changed - traffic, customer behaviour - and people want to test it again to see if the learnings are still valid"*. **This is a legitimate re-test, not a duplicate.**

> Design implication: time-range filter is at least as important as brand or section. Add a "compare past 2y vs past 5y" capability in Phase 2.

---

## 5. Confluence naming + tagging conventions

### What is enforced

- Brand prefix in the page title - e.g. `[ON]` for Old Navy, `[GP]` for Gap, `[BR]` for Banana Republic, `[BRONGA]` for cross-brand, `[AT]` for Athleta. *Mostly* applied. Some pages have no brand prefix - Prateek showed one example live.
- The Confluence test-results template enforces a `Test Details` table with `Brand`, `Page/Funnel/Channel`, `Audience Limitation`, `Problem Statement`, `Control`, `Challenger`, etc. (See screenshot `image (15).png` - "[ON APP] Sale Accordian Test".) **These structured cells are the most reliable source for retrieval metadata.**

### What is NOT enforced

- Free-form **labels / tags** ("old-navy", "category-page", "facet") are optional. The page creator may or may not add them; the senior analyst often goes back and adds tags retroactively only when *they* need to find the page.
- **Naming consistency** within the same theme - "show / hide sister brand universal bar" can be expressed many different ways.

### Retrieval implications

| Signal | Reliability | Use it for |
|--------|-------------|------------|
| Brand prefix in title | High (mostly) | Coarse brand filter pre-retrieval |
| Test Details table cells | High | Structured metadata fields for filters |
| Confluence labels | Low | A *bonus* signal in the embedding context; **not** a primary filter |
| Folder-by-year structure | Medium | Time-window filter fallback when no `start_date` field exists |

---

## 6. Search expectations

### 6.1 Minimal-wording queries

> *"The best way for me would be to get the best results with the minimal wording... let's say if there's a person outside our team, they may not know each and every detail."*

The user might enter: `Did we test this on Old Navy in the past 5 years?` - no metric specified, no page section, no exact test name. **The system must still resolve this.**

### 6.2 Click-to-fill helpers under the search bar

Prateek explicitly asked for **suggested prompt chips** when the user clicks into the search bar:

- *"give me winners from past 5 years"*
- *"give me all Old Navy tests that ran on product page"*
- *"give me all tests that ran on category page"*

> Build these from the SharePoint columns Prateek listed: site section x device x brand x time-window. Persona-aware variants are a Phase 2 nice-to-have.

### 6.3 Filters (collected for the follow-up Excel)

Athul committed to send a follow-up Excel with the full filter shortlist. Confirmed candidates from this session:

- **Brand** (single or multi-select)
- **Site section / page funnel** (PLP, PDP, search, shopping bag, checkout)
- **Device** (app / web / desktop)
- **Time window** (past 6 / 12 / 24 / 60 months, or custom)
- **Outcome** (winner / loser / inconclusive)
- **KPI / primary metric** (Conversion Lift, Revenue Lift, AOV Lift, Units per Transaction Lift)

---

## 7. Result cards

The Figma Hi-Fi (see screenshots `image (13).png`, `image (14).png`) already showed:

- Header KPIs band: *Total Experiments Run*, *Completed*, *Successful*, *Active*.
- Business-impact band: *Average Conversion Lift*, *Total Revenue Impact*, *Average AOV Lift*, *Units per Transaction Lift*, *Total Category Sales Impact*.
- **Recent Experiments** grid - each card has: title, one-line hypothesis, category, region, stores count, duration, conversion lift, revenue lift, AOV lift, confidence, **Success / Failed badge**, View Details link.

### Prateek's only addition

Add a **1-2 line "Learning / Recommendation"** snippet per card. Quote:

> *"This test ran, these were the findings, this was the recommendation - in just a line or two - so they can get a glimpse without having to open it. And if they want, there will always be an option to get into the details."*

### Metadata needed to support this

- `learning_snippet` (1-2 lines, plain text) - **NEW field to extract from Confluence**.
- The 7 numeric KPIs already on the card map to deterministic cells in the Test Details table.

### What was rejected

- **Glean-style aggregated summary across the result set** (Athul proposed this). Prateek pushed back hard: bad query -> bad summary -> wrong decision. Per-experiment summaries only. Re-evaluate at Phase 2 when retrieval precision is measurable.

---

## 8. AI chatbot

### 8.1 Common predefined prompts (3-5 chips)

To be drawn from the SharePoint column set Prateek confirmed exists:

| Dimension | Values |
|-----------|--------|
| Test type | digital, store |
| Site section | PLP, PDP, search, shopping bag, checkout |
| Device | app, mobile web, desktop |
| Brand | Old Navy, Gap, Banana Republic, Athleta, BRONGA (cross-brand) |

Example chips for the chatbot landing:
- "All PDP tests in the last 12 months - summarise winners"
- "App-only tests for Old Navy with positive AOV lift"
- "Has this test been run before? <free text>"

### 8.2 Answer shape

| What Prateek wants in an answer | Required field |
|---|---|
| Has this test been run before? (yes/no) | resolved by retrieval |
| For which brand(s)? | `brand` |
| What were the findings? | `findings` / `learning_snippet` |
| Was there any lift? | KPI deltas + confidence |
| If multiple tests on the same theme - **combined summary**: were the findings consistent or contradictory? | aggregation across the result set **only when the user explicitly asks for a combined view** |

### 8.3 Stage-dependent usage (Nilim's point)

PMs and Brand Managers may use the chatbot at very different stages (exploratory ideation vs. pre-launch validation). Prateek confirmed but deferred: *"that would be best answered by them"* - we will answer it in the upcoming PM and Brand Manager interviews.

### 8.4 Trust + adoption

- No explicit "guardrails" UI requested. Trust is a *function of retrieval correctness*.
- Cite Confluence page link below every answer (already planned).
- If the response is "mixed" or "lots of words to absorb", users will silently fall back to pinging the analyst.

---

## 9. Access control + sharing

| Question | Answer |
|----------|--------|
| Is RBAC required? | **No.** Everything in Confluence is open to anyone with a GAP ID. |
| Cross-brand visibility? | Already the norm - one PDM owns a site section across all four brands. |
| Hierarchical access (senior vs. junior)? | None - no tier-based gating. |
| Will financial numbers in Confluence leak? | They are already visible to everyone today; not a new risk introduced by the tool. |

**Decision**: keep the application's authz model at the corporate-SSO boundary (gap.com Workspace OAuth). No row-level or document-level ACL needed inside the GenAI app.

---

## 10. Operational commitments + follow-ups

| # | Item | Owner | Status |
|---|------|-------|--------|
| O1 | Send Excel with the full **filter shortlist** for search | Athul -> Prateek | Within the week (email, low priority) |
| O2 | Provide names for **PM + Brand Manager interviews** (the next two persona slots) | Prateek (after his sync with David) | Tomorrow morning |
| O3 | Schedule the **biweekly WBR** with Prateek + David | Athul (via Aditya) | Best window: Friday morning; fallback Thursday after 13:30 |
| O4 | Approve **MFA / contractor ID** requests for the remaining 7 Mathco members | Prateek to chase Dave | Open |

---

## 11. Updates to existing project artefacts

- **Project_Documentation.md / Vertex_AI_Search_Variant/Architecture.md** *(the standalone `GenAI_Design_Document.md` was retired during the post-Meeting-4 cleanup; its content is now split between these two files)*
  - Personas - explicitly add *Senior Analyst* as a distinct persona at par with *PDM*, *Brand Partner*, *Leadership*. Note that level (senior/junior) does NOT change the flow.
  - Confluence corpus - add `learning_snippet` as a required extracted field. Mark `confluence_labels` as low-confidence metadata.
  - ACL - confirm that no in-app ACL is required; SSO-only boundary stands.
- **Vertex_AI_Search_Variant/Frontend_Developer_Guide.md** §3 / §8 - add the **suggested-prompts row** under the search bar; render `learning_snippet` on result cards.
- **Vertex_AI_Search_Variant/Backend_Developer_Guide.md** §4 - add `learning_snippet` to the `format_citations` output shape so the FE can render it without an extra round-trip.
- **synthetic_corpus/generate.py** - add a `learning_snippet` field to the metadata block of each generated HTML page so smoke tests can exercise the new card layout.

For the one-page summary see [Meeting_Overview.md](Meeting_Overview.md). Raw transcript: [transcript_extracted.txt](transcript_extracted.txt). Screenshots: `image (9).png`, `image (13).png`, `image (14).png`, `image (15).png`.
