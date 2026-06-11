# Meeting 4 - Overview (ERD Senior Analyst Interview, Prateek)

> **Date**: 2026-05-13
> **Type**: Persona user interview (Senior Analyst - the first of four ERD persona walkthroughs)
> **Host / SME**: Prateek Oberoi (GAP, Senior Analytics Manager)
> **Attendees**: Sowmiya, Athul, Kaushik, Nilim (Mathco); Prateek (GAP)
> **Duration**: 38 min
> **Focus**: Validate the Senior-Analyst persona model and walk Prateek through the WIP Figma Hi-Fi (search, result cards, AI chatbot) to lock the Phase-1 UX scope.

For deep dive see [Meeting_Details.md](Meeting_Details.md). Raw transcript: [transcript_extracted.txt](transcript_extracted.txt).

---

## One-line summary

Prateek validated the Senior-Analyst persona (levels don't matter - scope changes, flow stays the same), endorsed the Figma cards, asked for a **1-2 line "learning / recommendation"** per result, asked for **click-to-fill prompt chips** under a **minimal-wording** search bar, **rejected** a Glean-style aggregated summary, and confirmed **no RBAC** is needed (Confluence pages are open to any GAP ID).

---

## Top takeaways

| # | Takeaway | Implication for the GenAI POC |
|---|----------|-------------------------------|
| 1 | Persona levels don't matter - all analysts run the same flow, only scope/volume differs. | One Senior-Analyst persona covers the whole analyst track. |
| 2 | Tool switching (Optimizely + Adobe) is *accepted*, not a pain point. | Drop "tool unification" from the analyst's challenge list. |
| 3 | Three search triggers: PM/PDM context, brand-partner cross-brand check, time-decayed re-check. | Filters must cover brand, site-section AND time-window equally. |
| 4 | Confluence labels are optional and inconsistent; brand prefix in title is *mostly* applied. | Cannot rely on labels for retrieval - use embeddings + structured table cells. |
| 5 | Ideal search = minimal wording + helper prompt chips ("give me winners from past 5 years"). | Add a suggested-prompts row under the search bar. |
| 6 | Each result card needs a 1-2 line **learning / recommendation** snippet. | Extract `learning_snippet` from Confluence; render on the card. |
| 7 | **Glean-style aggregated summary REJECTED** - bad search -> bad summary -> wrong decision. | Keep chatbot answers per-experiment for Phase 1. |
| 8 | No persona-conditional rendering ("for PMs show X, for Leadership show Y"). | One canonical results view; reader self-selects depth. |
| 9 | Chatbot seed prompts come from SharePoint columns: site-section x device x brand x time. | Build the prompt library directly from those columns. |
| 10 | **No RBAC** - all Confluence pages are open to any GAP ID; one PDM covers all 4 brands. | Auth boundary stays at corporate SSO only. |

---

## Persona model - Senior Analyst (validated)

- **Role**: Analytics Manager / Senior Data Scientist supporting all four brands.
- **Flow**: Briefing from PM/PDM -> set up + monitor test -> analyse results -> write recommendations -> share with PMs / Brand / Leadership.
- **Challenges**: inconsistent Confluence naming, recall after new joiners, repeated cross-brand asks, optional/retroactive tagging.
- **Outcome wanted**: self-service for non-analyst partners so the senior analyst stops being the human search engine.

---

## Action items

| # | Item | Owner | ETA |
|---|------|-------|-----|
| A1 | Send Excel with the full **filter shortlist** for search (low-priority email follow-up) | Athul -> Prateek | This week |
| A2 | Confirm names for **PM + Brand Manager interviews** | Prateek (after sync with David) | Next day |
| A3 | Schedule the **biweekly WBR** (Prateek + David); Friday AM preferred, Thu after 13:30 fallback | Athul (via Aditya) | Same week |
| A4 | Approve **MFA / contractor ID** requests for the remaining 7 Mathco members | Prateek to chase Dave | Open |
| A5 | After all four persona interviews, Mathco circles back to Prateek + David with the consolidated POV | Mathco | After PM + Brand Manager interviews |

---

## Updates to project artefacts

- **Project_Documentation.md / Vertex_AI_Search_Variant/Architecture.md** - add Senior Analyst as an explicit persona at par with PDM / Brand Partner / Leadership; record `learning_snippet` as a required extracted field on every Confluence page; mark `confluence_labels` as low-confidence metadata; restate no in-app ACL (SSO-only boundary). *(Note: the standalone `GenAI_Design_Document.md` has been retired; its content lives in `Project_Documentation.md` plus the `Vertex_AI_Search_Variant/` deep-dive.)*
- **Vertex_AI_Search_Variant/Frontend_Developer_Guide.md** - add suggested-prompts row under search; render `learning_snippet` on result cards.
- **Vertex_AI_Search_Variant/Backend_Developer_Guide.md** - extend `format_citations` response shape with `learning_snippet`.
- **synthetic_corpus/generate.py** - add `learning_snippet` to generated metadata so smoke tests cover the new card layout.

---

## Open questions deferred to upcoming interviews

1. At which **stage** of a test do PMs / Brand Managers use the tool (ideation, mid-flight, post-launch)?
2. Do PMs/BMs want a different prompt-chip set than the analyst persona?
3. Is there ever a need for **aggregated** answers across multiple tests for non-analyst personas? (Prateek said no for analysts; PMs may disagree.)
