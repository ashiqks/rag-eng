# Multi-Session Conversation Flow — UI ↔ Backend ↔ Vertex AI Search

> **Scenario**: A user (`ashiq.ks@gap.com`) had two prior conversations yesterday. Today they open the web app. We need to:
>
> 1. Show the two prior chats in a sidebar
> 2. Let them click one and resume from exactly where they left off
> 3. Optionally start a third (new) chat
>
> This document traces every hop — browser → Web App → API Gateway → ADK Agent → Vertex AI Search (VAIS) → BigQuery — for each of those actions.

---

## 0. Identity model (recap)

| App-side name | Maps to | Where it lives |
|---|---|---|
| `user_id` | VAIS `userPseudoId` | OAuth `sub` claim (Workspace SSO); opaque, stable per user |
| `session_id` | Last path segment of `engines/{engine}/sessions/{id}` | Minted by VAIS on `sessions.create` |
| `turn_id` | `query.queryId` | Minted by VAIS on each `:answer` call |
| `title` | Sidebar label | Stored in BQ `gap_genai_app.session_titles` keyed by `session_id` |

VAIS owns the **what was said**. BigQuery owns the **what to label it** + analytics. No other session state anywhere.

---

## 1. Page load — “show me my prior chats”

### What the user does
Opens `https://genai-discovery.gap.com`, completes Workspace SSO, lands on the chatbot page.

### End-to-end sequence

```
┌────────┐         ┌──────────┐        ┌──────────┐       ┌──────────┐      ┌──────────────┐     ┌────────┐
│Browser │         │ Web App  │        │  Gateway │       │  Agent   │      │     VAIS     │     │BigQuery│
└───┬────┘         └────┬─────┘        └────┬─────┘       └────┬─────┘      └──────┬───────┘     └───┬────┘
    │                   │                   │                  │                   │                 │
 1. │ GET /             │                   │                  │                   │                 │
    │──────────────────►│                   │                  │                   │                 │
 2. │                   │ 302 → Workspace SSO if no session    │                   │                 │
    │                   │ ... user signs in ...                │                   │                 │
 3. │                   │ ID token cached (httpOnly cookie)    │                   │                 │
    │                   │                   │                  │                   │                 │
 4. │ GET /api/genai/sessions               │                  │                   │                 │
    │  cookie: id_token=...                 │                  │                   │                 │
    │──────────────────►│──────────────────►│                  │                   │                 │
    │                   │                   │                  │                   │                 │
 5. │                   │                   │ verify OAuth → extract sub = user_id │                 │
    │                   │                   │ rate-limit check                     │                 │
    │                   │                   │ POST /agent/sessions:list            │                 │
    │                   │                   │ headers: X-User-Id: <user_id>        │                 │
    │                   │                   │──────────────────►                   │                 │
    │                   │                   │                  │                   │                 │
 6. │                   │                   │                  │ S5 list_sessions  │                 │
    │                   │                   │                  │ GET engines/{e}/sessions             │
    │                   │                   │                  │ ?filter=userPseudoId="<user_id>"     │
    │                   │                   │                  │ &orderBy=updateTime desc             │
    │                   │                   │                  │ &pageSize=50                         │
    │                   │                   │                  │──────────────────►                   │
    │                   │                   │                  │                   │                 │
 7. │                   │                   │                  │                   │ returns sessions[]: │
    │                   │                   │                  │                   │  [{name, createTime, │
    │                   │                   │                  │                   │    updateTime, turns:[…]}]│
    │                   │                   │                  │                   │                 │
 8. │                   │                   │                  │ join titles from BQ by session_id │
    │                   │                   │                  │──────────────────────────────────►│
    │                   │                   │                  │ SELECT session_id, title          │
    │                   │                   │                  │ FROM gap_genai_app.session_titles │
    │                   │                   │                  │ WHERE user_id=@u AND session_id IN UNNEST(@ids)│
    │                   │                   │                  │◄──────────────────────────────────│
    │                   │                   │                  │                   │                 │
 9. │                   │                   │                  │ shape response:                      │
    │                   │                   │                  │ [{session_id, title, last_active,    │
    │                   │                   │                  │   turn_count, preview_snippet}, …]   │
10. │                   │                   │◄─────────────────│                   │                 │
11. │                   │◄──────────────────│ 200 JSON list   │                   │                 │
12. │◄──────────────────│ renders sidebar  │                   │                   │                 │
    │                   │                   │                  │                   │                 │
```

### What the user sees

```
┌───────────────────────────────────────────────────────────┐
│  Chats           [+ New chat]                             │
├───────────────────────────────────────────────────────────┤
│  ▸ Old Navy sticky add-to-bag wins      yesterday  6 turns│
│  ▸ Gap 2025 PLP testing rollups         2 days ago 4 turns│
├───────────────────────────────────────────────────────────┤
│  (Right pane: empty state "Pick a chat or start a new one")│
└───────────────────────────────────────────────────────────┘
```

### Concrete VAIS REST call (step 6)

```http
GET https://discoveryengine.googleapis.com/v1/projects/<p>/locations/global/
    collections/default_collection/engines/gap-genai-discovery-search/sessions
    ?filter=userPseudoId%3D%22<user_id>%22
    &orderBy=updateTime%20desc
    &pageSize=50
Authorization: Bearer <sa-agent token>
X-Goog-User-Project: <p>
```

Response shape (truncated):

```json
{
  "sessions": [
    {
      "name": "projects/.../engines/gap-genai-discovery-search/sessions/18411582449178203485",
      "userPseudoId": "108234...",
      "state": "IN_PROGRESS",
      "startTime": "2026-05-14T09:12:03Z",
      "endTime":   "2026-05-14T09:18:41Z",
      "turns": [ { "query": {"text":"…","queryId":"q1"}, "answer":"…" }, … ]
    },
    { "name": ".../sessions/18411582449178203412", … }
  ]
}
```

The `name` field's last path segment is what we hand to the UI as `session_id`.

---

## 2. User clicks one of the prior chats — “resume this conversation”

### What the user does
Clicks **“Old Navy sticky add-to-bag wins”** in the sidebar.

### End-to-end sequence

```
┌────────┐         ┌──────────┐        ┌──────────┐       ┌──────────┐      ┌──────────────┐
│Browser │         │ Web App  │        │  Gateway │       │  Agent   │      │     VAIS     │
└───┬────┘         └────┬─────┘        └────┬─────┘       └────┬─────┘      └──────┬───────┘
    │                   │                   │                  │                   │
 1. │ click sidebar item                    │                  │                   │
    │ → router /chat/18411582449178203485   │                  │                   │
    │                   │                   │                  │                   │
 2. │ GET /api/genai/sessions/{id}/turns    │                  │                   │
    │──────────────────►│──────────────────►│                  │                   │
    │                   │                   │                  │                   │
 3. │                   │                   │ OAuth verify    │                   │
    │                   │                   │ POST /agent/sessions/{id}/turns      │
    │                   │                   │ headers: X-User-Id, X-Session-Id     │
    │                   │                   │──────────────────►                   │
    │                   │                   │                  │                   │
 4. │                   │                   │                  │ ACL gate:        │
    │                   │                   │                  │ GET engines/{e}/sessions/{id}        │
    │                   │                   │                  │ ?includeAnswerDetails=true           │
    │                   │                   │                  │──────────────────►                   │
    │                   │                   │                  │                   │
 5. │                   │                   │                  │                   │ returns session: │
    │                   │                   │                  │                   │ { userPseudoId, │
    │                   │                   │                  │                   │   turns:[{query,answer,citations,references}…]}│
    │                   │                   │                  │                   │
 6. │                   │                   │                  │ assert session.userPseudoId == X-User-Id │
    │                   │                   │                  │   else 403       │                   │
    │                   │                   │                  │                   │
 7. │                   │                   │                  │ shape turns[] for UI:                │
    │                   │                   │                  │ [{role:'user',  text:…},             │
    │                   │                   │                  │  {role:'assist',text:…, citations[]}…]│
 8. │                   │                   │◄─────────────────│                   │                  │
 9. │                   │◄──────────────────│ 200 JSON turns[]│                    │                  │
10. │◄──────────────────│ renders chat history into the right pane                 │                  │
    │                   │ user can now type their next message                     │                  │
```

### What the user sees

Right pane fills in with the full prior conversation:

```
You: What were the strongest Old Navy sticky add-to-bag tests?
Assistant: The strongest evidence comes from the Old Navy Android App test
           (TLCOE-2010225), where the challenger outperformed control by 5.05%…
           [10 citations]

You: Summarize all the returned results
Assistant: **Winners:** TLCOE-2010225 (+5.05%)…
           **Flat:** Mobile Web, Desktop variants…
           [10 citations]

[ Type your next message ▼ ]
```

The signed session cookie is updated so a refresh stays on this chat.

### Concrete VAIS REST call (step 4)

```http
GET https://discoveryengine.googleapis.com/v1/projects/<p>/locations/global/
    collections/default_collection/engines/gap-genai-discovery-search/
    sessions/18411582449178203485?includeAnswerDetails=true
Authorization: Bearer <sa-agent token>
X-Goog-User-Project: <p>
```

Response includes the full ordered list of turns plus every `answer.references[]` so the UI can render the citation chips exactly as the user saw them last time.

---

## 3. User types the next turn in the resumed chat

### What the user does
Types: **“Now compare those to the Gap mobile-web tests”**

### End-to-end sequence

```
┌────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│Browser │    │ Web App  │    │ Gateway  │    │  Agent   │    │   VAIS   │    │BigQuery │
└───┬────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘    └───┬─────┘
    │              │               │               │               │              │
 1. │ submit input │               │               │               │              │
    │─────────────►│               │               │               │              │
 2. │              │ POST /api/genai/chat          │               │              │
    │              │ body {text, session_id}       │               │              │
    │              │──────────────►│               │               │              │
 3. │              │               │ OAuth verify  │               │              │
    │              │               │ POST /agent/chat              │               │              │
    │              │               │ headers X-User-Id, X-Session-Id              │              │
    │              │               │──────────────►│               │              │
 4. │              │               │               │ S1 generate_answer            │              │
    │              │               │               │ POST :answer                  │              │
    │              │               │               │ body {                        │              │
    │              │               │               │   query.text,                 │              │
    │              │               │               │   session: engines/.../sessions/{id},│       │
    │              │               │               │   queryUnderstandingSpec: {   │              │
    │              │               │               │     queryRewritingSpec: {disable:false},│    │
    │              │               │               │     naturalLanguageQueryUnderstandingSpec: { │
    │              │               │               │       filterExtractionCondition:'ENABLED'}}, │
    │              │               │               │   answerGenerationSpec.includeCitations:true}│
    │              │               │               │──────────────►│              │
 5. │              │               │               │               │ internally:  │
    │              │               │               │               │  • read this session's history│
    │              │               │               │               │  • resolve "those" against prior turns│
    │              │               │               │               │  • rewrite query (typos / expansions) │
    │              │               │               │               │  • extract filter from NL:            │
    │              │               │               │               │      brand:ANY("Gap") AND             │
    │              │               │               │               │      channel:ANY("Mobile Web")        │
    │              │               │               │               │  • hybrid retrieve+rerank under filter│
    │              │               │               │               │  • grounded synth + citations         │
    │              │               │               │               │  • append THIS turn to session        │
 6. │              │               │               │               │ returns {answer, citations, references,│
    │              │               │               │               │          queryUnderstandingInfo}      │
    │              │               │               │◄──────────────│              │
 7. │              │               │               │ S2 format_citations           │              │
    │              │               │               │ S4 log_turn → BQ (includes extracted filter)│
    │              │               │               │────────────────────────────►│
 8. │              │               │◄──────────────│               │              │
 9. │              │◄──────────────│ 200 {answer, citations, refs} │              │
10. │◄─────────────│ append to chat pane                          │               │              │
```

Key point: **we never resend prior turns to VAIS, and we never call our own LLM**. The `session` field is enough for history; `naturalLanguageQueryUnderstandingSpec.filterExtractionCondition=ENABLED` is enough for filter extraction. VAIS handles both server-side. The extracted filter is returned in `queryUnderstandingInfo` so we log it for telemetry and golden-eval drift detection, but we do not author it.

---

## 4. User clicks “+ New chat”

```
 1. Browser POST /api/genai/sessions
 2. Gateway → Agent POST /agent/sessions
 3. Agent → VAIS POST engines/{e}/sessions  body {userPseudoId:<user_id>}
 4. VAIS returns session.name = engines/.../sessions/<new_id>
 5. Agent: optionally INSERT INTO BQ session_titles (session_id, user_id, title=NULL, created_at=now())
 6. Agent → Gateway: {session_id, title:null}
 7. Gateway: sign cookie with session_id
 8. Web App: route /chat/<new_id>, empty pane, focus input
```

Title is filled in **after the first turn**: the agent writes `truncate(first_user_text, 60)` into `session_titles.title`. The sidebar shows “New chat…” until then.

---

## 5. User deletes a chat from the sidebar

```
 1. Browser DELETE /api/genai/sessions/{id}
 2. Gateway → Agent DELETE /agent/sessions/{id}
 3. Agent:
       a. GET engines/{e}/sessions/{id}  → assert userPseudoId == caller user_id
       b. DELETE engines/{e}/sessions/{id}            (VAIS)
       c. DELETE FROM session_titles WHERE session_id=@id AND user_id=@u  (BQ)
 4. 204 No Content → Web App removes the row from the sidebar
```

If the user deletes the currently open chat, the UI routes back to the empty state.

---

## 6. Pruning sessions older than 90 days (background, no user action)

```
Cloud Scheduler  (nightly 03:00 PT)
   │
   ▼
Cloud Run Job 'session-pruner'  [sa-session-pruner]
   │
   ├─► VAIS  sessions.list(pageSize=1000, orderBy=updateTime asc)
   │       loop pages, collect sessions where updateTime < now()-90d
   │
   ├─► (optional, compliance) export each session's turns to BQ session_archive
   │
   ├─► VAIS  sessions.delete(name)  for each expired session
   │
   ├─► BQ    DELETE FROM session_titles WHERE session_id IN (...)
   │
   └─► BQ    INSERT INTO prune_runs (sessions_pruned, sessions_archived, duration)
```

The user never sees these chats again; the sidebar list is naturally bounded.

---

## 7. Why this works without an app-side session store

| Requirement | How VAIS handles it | Why a custom store would be worse |
|---|---|---|
| Persist every turn atomically with the answer | `:answer` writes the turn server-side as part of the same call | Need a 2-phase commit between VAIS and the store |
| Anaphora across turns (“those tests”, “the previous answer”) | `:answer` reads its own session and resolves references | Need to ship prior turns into the prompt; manage token budget |
| List a user's chats | `sessions.list?filter=userPseudoId="…"` | Need a `sessions` table + index by `user_id` |
| Resume a chat | `sessions.get?includeAnswerDetails=true` returns the full turn history with citations intact | Need to denormalise citations into our own table |
| ACL between users | `userPseudoId` is the partition key; we verify on every read | Same gate, but on our own data |
| Idempotency on retry | VAIS appends only on successful `:answer` | Need write-once semantics ourselves |

We keep **only** what VAIS doesn't store: the human-readable `title` for the sidebar (cached in BigQuery), plus `feedback`. Per-turn telemetry (latency, tokens, status, request_id, skill_name) lives in the **Cloud Observability Suite** as OTel log entries + Trace span attributes (AR-5), not BigQuery. Everything joins by `session_id`.

---

## 8. Components actually touched by this flow

| Action | Web App | Gateway | Agent | VAIS | BigQuery | Cloud Scheduler |
|---|---|---|---|---|---|---|
| Show prior chats | ✅ render | ✅ auth + route | ✅ S5 list_sessions | ✅ `sessions.list` | ✅ titles join | — |
| Open a chat | ✅ render history | ✅ route | ✅ ACL + fetch | ✅ `sessions.get` | — | — |
| Send a turn | ✅ append bubble | ✅ route | ✅ S1/S2/S4 | ✅ `:answer` (auto-append) | ✅ logs | — |
| New chat | ✅ blank pane | ✅ mint cookie | ✅ create session | ✅ `sessions.create` | ✅ title row | — |
| Delete chat | ✅ remove row | ✅ route | ✅ ACL + delete via S6 | ✅ `sessions.delete` | ✅ title row | — |
| 90d prune | — | — | — | ✅ `sessions.delete` x N | ✅ cleanup | ✅ trigger |

No service is touched that isn't already on the architecture diagram. The Model Router, Agent Engine Sessions, and Model Garden synthesis path are **not** in any of these flows — that's the whole point of the VAIS-native pivot.

---

## 9. Endpoint summary (BFF)

| Method | Path | Backed by |
|---|---|---|
| `POST` | `/api/genai/sessions` | VAIS `sessions.create` + BQ insert |
| `GET` | `/api/genai/sessions` | VAIS `sessions.list` + BQ titles join |
| `GET` | `/api/genai/sessions/{id}/turns` | VAIS `sessions.get?includeAnswerDetails=true` |
| `DELETE` | `/api/genai/sessions/{id}` | VAIS `sessions.delete` + BQ delete |
| `POST` | `/api/genai/chat` | VAIS `:answer` (with `session` field) |
| `POST` | `/api/genai/feedback` | BQ `feedback` insert |

The Gateway is **a thin pass-through** for the four session endpoints — no business logic, just OAuth verification and rate limiting. All session intelligence lives in VAIS.
