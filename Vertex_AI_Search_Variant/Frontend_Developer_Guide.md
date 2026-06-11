# Frontend Developer Guide - GAP GenAI Knowledge Discovery (Web App)

## 1. Project context (one-minute version)

- **What we are building.** A single-page chat application that lets internal Gap users ask natural-language questions over the Test & Learn COE Confluence space and get grounded answers with inline citations back to the original pages.
- **Backend in one sentence.** A single ADK Discovery Agent on Cloud Run that makes **one** call to Vertex AI Search `:answer` per turn. The Search engine owns retrieval, synthesis, citations, and conversation history.
- **What the Web App owns.** Auth landing, persona-aware routing (Executive dashboard vs Analyst chat), the chat-list sidebar, the chat surface, the citation pane, the thumbs feedback widget.
- **What the Web App does NOT own.** No LLM call, no vector store, no session state in the browser beyond a signed cookie. Conversation memory lives entirely in Vertex AI Search.

---

## 2. Recommended stack (not locked - confirm with the team)

| Concern | Recommendation | Why |
|---|---|---|
| Framework | **React 18 + Vite + TypeScript** | Matches the "Web App on Cloud Run" mention in the architecture; lightest path to static-served SPA behind Cloud Run |
| Routing | **React Router v6** | `/`, `/chat/:sessionId?`, `/dashboard` |
| Server state | **TanStack Query v5** | Fits the REST-only backend; built-in optimistic updates for the sidebar |
| Client state | React `useState` / `useReducer` for local UI; no Redux | The only durable state lives server-side (VAIS) |
| Styling | **Tailwind CSS** | Fast iteration, matches the design-component CSV under `PPT/` |
| Markdown / citations | `react-markdown` + `remark-gfm` | Render `[n]` markers and Confluence links |
| HTTP client | `fetch` wrapped in a typed `api.ts` module | Avoids axios footprint |
| Auth helper | None client-side - cookie-based OAuth is handled by the backend gateway | See section 5 |
| Test | **Vitest + React Testing Library** + Playwright for the smoke flow | Aligns with the Powershell smoke test for the backend |

Alternatives if the team prefers: **Next.js 14** (App Router) is a drop-in alternative and makes IAP-based OIDC easier; **Angular** is acceptable if it is the GAP enterprise standard.

---

## 3. Pages and routes

| Route | Purpose | Persona |
|---|---|---|
| `/` | Persona-aware landing. Executives see the Dashboard view; PDM/Analyst see the chatbot. | All |
| `/chat` | Empty chat state: "Pick a chat or start a new one" with a `+ New chat` button. | PDM/Analyst |
| `/chat/:sessionId` | Active conversation view. Hydrates from `GET /api/genai/sessions/{id}/turns`. | PDM/Analyst |
| `/dashboard` | Metrics tiles, result breakdown, filter pane (replaces the current Power BI stopgap). | Executive |
| `/auth/callback` | OAuth callback handled by the backend gateway; the SPA only handles the success redirect. | All |

### Layout

```
+-------------------------------------------------------------------+
| Top bar: GAP GenAI - Discovery        user@gap.com  [logout]      |
+--------------------+----------------------------------------------+
| Sidebar (chats)    | Active chat surface                          |
|  + New chat        |  - turn bubbles (user / assistant)           |
|  Old Navy ATB  6t  |  - inline [n] citation markers               |
|  Gap PLP 2025  4t  |  - citation panel on the right              |
|  ...               |  - input box at the bottom                   |
|                    |  - thumbs up/down per assistant turn         |
+--------------------+----------------------------------------------+
```

---

## 4. REST API contract the frontend calls

All endpoints are served by the backend at `/api/genai/*`. Request/response shapes are quoted verbatim from [Multi_Session_Flow.md](Multi_Session_Flow.md).

### 4.1 `POST /api/genai/chat` - submit one turn

**Request**
```json
{
  "text": "Now compare those to the Gap mobile-web tests",
  "session_id": "18411582449178203485"
}
```

Headers: cookie `id_token=...` (set by OAuth flow). Backend extracts `user_id` from the `sub` claim.

**Response (200)**
```json
{
  "answer": "The strongest evidence comes from ... [1] [2]",
  "citations": [
    { "sources": [ { "referenceId": "chunk_id_abc" } ] }
  ],
  "references": [
    {
      "chunkInfo": {
        "documentMetadata": {
          "structData": {
            "confluence_url": "https://confluence.gap.com/display/TLCOE/Old+Navy+...",
            "page_id": "2010225",
            "title": "Old Navy Android App - Sticky ATB"
          }
        }
      }
    }
  ],
  "dashboard_payload": null
}
```

The backend collapses VAIS `citations[].sources[].referenceId` into `[n]` markers in `answer` and lines up the `references[]` index with `n`.

**Optional `dashboard_payload`** is populated when the backend agent routed the turn to the `query_experiment_kpis` skill (intent = list/show/how-many/which). Shape:

```json
"dashboard_payload": {
  "tiles": {
    "total_run": 142, "completed": 136, "successful": 78, "active": 6,
    "avg_conversion_lift": 3.8, "total_revenue_impact": 9400000,
    "avg_aov_lift": 4.2, "upt_lift": 5.1, "total_category_sales_impact": 4600000
  },
  "card_clusters": [
    {
      "cluster_id": "DEP-001",
      "name": "Denim Entrance Placement",
      "category": "Product Placement",
      "stores": 45,
      "region": "North America",
      "duration": "2025-08-01..2025-11-15",
      "conversion_lift": 3.6,
      "revenue_lift": 2100000,
      "aov_lift": 4.0,
      "confidence": 96,
      "success": true
    }
  ]
}
```

Render rules:
- When `dashboard_payload` is `null` / omitted -> chat narrative only (today's behaviour).
- When present -> render the KPI tile row above the narrative + a `card_cluster` list below it. Each card mirrors the Figma layout (`Recent Experiments` / `Experiment Performance Overview`): name, category badge, stores / region / duration, three lift KPIs, confidence%, green Success pill iff `success === true`.
- Tiles + cards are part of the SAME `/api/genai/chat` response - the dashboard view and the chat widget share one endpoint; the frontend just chooses what to render based on payload shape. See [`Architecture.md`](Architecture.md) §7.

### 4.2 `GET /api/genai/sessions` - sidebar chat list

**Response (200)**
```json
{
  "sessions": [
    {
      "session_id": "18411582449178203485",
      "title": "Old Navy sticky add-to-bag wins",
      "last_active": "2026-05-14T09:18:41Z",
      "turn_count": 6,
      "preview_snippet": "The strongest evidence comes from..."
    },
    {
      "session_id": "18411582449178203412",
      "title": "Gap 2025 PLP testing rollups",
      "last_active": "2026-05-13T16:02:11Z",
      "turn_count": 4,
      "preview_snippet": "Across the Gap PLP variants ..."
    }
  ]
}
```

Sorted server-side by `updateTime desc`. Backend filters by the caller's `user_id` (client-side filter on VAIS - see Backend Guide section 6).

### 4.3 `POST /api/genai/sessions` - new chat

**Request:** empty body.

**Response (201)**
```json
{ "session_id": "18411582449178203501", "title": null }
```

The sidebar shows "New chat..." until the first turn lands; the backend then derives a 60-char title from the first user message and persists it to BigQuery.

### 4.4 `GET /api/genai/sessions/{id}/turns` - resume a chat

**Response (200)**
```json
{
  "turns": [
    { "role": "user",      "text": "What were the strongest Old Navy sticky ATB tests?" },
    {
      "role": "assistant",
      "text": "The strongest evidence comes from ... [1] [2]",
      "citations": [ { "sources": [ { "referenceId": "chunk_id_abc" } ] } ],
      "references": [ { "chunkInfo": { "documentMetadata": { "structData": { "confluence_url": "..." } } } } ]
    }
  ]
}
```

The backend verifies `session.userPseudoId == caller.user_id`; cross-user access returns `403`.

### 4.5 `DELETE /api/genai/sessions/{id}` - remove a chat

Response: `204 No Content`. The backend performs an ACL check then deletes both the VAIS session and the BigQuery title row.

### 4.6 `POST /api/genai/feedback` - thumbs widget

**Request**
```json
{
  "session_id": "18411582449178203485",
  "turn_id": "q3",
  "rating": 1,
  "comment": "Great answer, links worked"
}
```
`rating` is `1` (thumbs up) or `-1` (thumbs down). `comment` is optional.

**Response:** `204 No Content`.

---

## 5. Auth

- **Provider:** Google Workspace OAuth, restricted to `gap.com` domain accounts.
- **Flow:** the backend gateway implements the full OAuth dance. The SPA only needs to:
  1. On `401`, redirect the browser to `/auth/login` (server-side endpoint).
  2. On callback success, the gateway sets an **httpOnly signed cookie** carrying the ID token.
  3. Every subsequent `/api/genai/*` call sends the cookie automatically (`credentials: 'include'`).
- **`user_id` derivation:** the gateway pulls the OAuth `sub` claim and passes it as `X-User-Id` to the agent. The SPA never sees the raw `sub`.
- **`session_id` persistence:** stored both in the URL (`/chat/:sessionId`) and in a signed cookie so a hard refresh keeps the same chat open.
- **Local dev:** the backend supports a `X-Dev-User-Id` header in non-prod environments; set it via a Vite proxy:
  ```ts
  // vite.config.ts
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
        headers: { 'X-Dev-User-Id': 'dev-user-001' }
      }
    }
  }
  ```

---

## 6. State management

The minimum state the SPA tracks itself:

| State | Source | Lifetime | Notes |
|---|---|---|---|
| `userId` | Set by gateway on first 200 response (header echo or `/me` endpoint) | Until logout | Display name only - never used for auth decisions |
| `sessionId` | URL param + signed cookie | Until cleared | Used as the path arg for `/sessions/{id}/turns` |
| Sessions list | TanStack Query `['sessions']` | `staleTime: 30_000` | Optimistically updated on new/delete |
| Turns of active session | TanStack Query `['sessions', id, 'turns']` | `staleTime: Infinity` (only invalidate on new turn) | Appended in-place after each `/chat` mutation |
| Draft input text | local `useState` | Until submit | Not persisted |
| Pending feedback | local `useState` | Until submit | Not persisted |

Everything else (the actual conversation, the citation map, ownership) is canonical in Vertex AI Search + BigQuery.

---

## 7. Recommended custom hooks

These names line up 1:1 with the REST endpoints in section 4 so a new dev can grep for either.

```ts
// hooks/useSessions.ts
function useSessions() {
  return useQuery({
    queryKey: ['sessions'],
    queryFn: () => api.get<{ sessions: Session[] }>('/api/genai/sessions'),
    staleTime: 30_000,
  });
}

// hooks/useSessionTurns.ts
function useSessionTurns(sessionId: string | undefined) {
  return useQuery({
    queryKey: ['sessions', sessionId, 'turns'],
    queryFn: () => api.get<{ turns: Turn[] }>(`/api/genai/sessions/${sessionId}/turns`),
    enabled: !!sessionId,
    staleTime: Infinity,
  });
}

// hooks/useCreateSession.ts
function useCreateSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<{ session_id: string; title: string | null }>('/api/genai/sessions'),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sessions'] }),
  });
}

// hooks/useChat.ts
function useChat(sessionId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) =>
      api.post<ChatResponse>('/api/genai/chat', { text, session_id: sessionId }),
    onSuccess: (data, text) => {
      // append to the cached turns list and invalidate the sidebar (for last_active + turn_count)
      qc.setQueryData(['sessions', sessionId, 'turns'], (prev: any) => ({
        turns: [
          ...(prev?.turns ?? []),
          { role: 'user', text },
          { role: 'assistant', text: data.answer, citations: data.citations, references: data.references },
        ],
      }));
      qc.invalidateQueries({ queryKey: ['sessions'] });
    },
  });
}

// hooks/useDeleteSession.ts
function useDeleteSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del(`/api/genai/sessions/${id}`),
    onMutate: async (id) => {
      // optimistic remove
      await qc.cancelQueries({ queryKey: ['sessions'] });
      const prev = qc.getQueryData<{ sessions: Session[] }>(['sessions']);
      qc.setQueryData(['sessions'], (old: any) => ({
        sessions: old.sessions.filter((s: Session) => s.session_id !== id),
      }));
      return { prev };
    },
    onError: (_e, _id, ctx) => ctx && qc.setQueryData(['sessions'], ctx.prev),
  });
}

// hooks/useFeedback.ts
function useFeedback() {
  return useMutation({
    mutationFn: (body: { session_id: string; turn_id: string; rating: 1 | -1; comment?: string }) =>
      api.post('/api/genai/feedback', body),
  });
}
```

---

## 8. UX behaviors

| Behavior | How | Source |
|---|---|---|
| **Non-streaming today** | One `POST /chat` per turn, blocking spinner on the input. p95 budget is 8s; cold sessions are 10.2s, warm 4-6s. | [README.md](README.md) R2 risk |
| **Streaming (Phase 2)** | Tracked as a follow-up - move to SSE or chunked transfer once the backend exposes it. The chat hook signature will change to `onChunk` callbacks. | [README.md](README.md) R2 |
| **Inline `[n]` markers** | Backend rewrites `answer` text with bracketed numerals; the SPA renders them as clickable spans that scroll the right-hand citation pane to the matching `references[n-1]`. | [Architecture.md](Architecture.md) S2 |
| **Citation pane** | Lists `references[].chunkInfo.documentMetadata.structData.confluence_url` with the page `title` and a snippet. Each pill is `<a href={confluence_url} target="_blank" rel="noopener">`. | section 4.1 |
| **Thumbs widget** | Renders below each assistant turn; calls `useFeedback()` with `rating: 1 \| -1` and an optional comment field that expands on click. | [Architecture.md](Architecture.md) S3 |
| **New chat optimistic add** | `useCreateSession` returns a new `session_id`; the SPA routes to `/chat/<new_id>` and shows an empty pane with focus on input. The sidebar shows "New chat..." until the first turn. | [Multi_Session_Flow.md](Multi_Session_Flow.md) section 4 |
| **Delete current chat** | If the user deletes the open chat, route back to `/chat` (empty state). | [Multi_Session_Flow.md](Multi_Session_Flow.md) section 5 |
| **Resume restores citations** | `GET /sessions/{id}/turns` returns `citations` + `references` for every assistant turn, so re-opening a chat must render the same citation chips the user saw before. | [Multi_Session_Flow.md](Multi_Session_Flow.md) section 2 |
| **Persona routing** | On first load, GET `/api/genai/me` (returns `{ user_id, persona: 'executive' \| 'analyst' }`) and route accordingly. Default = analyst. | [../Project_Documentation.md](../Project_Documentation.md) §4 |
| **Search-bar prompt chips** | On focus of the empty search bar / chat input, render a row of suggested-prompt chips drawn from `GET /api/genai/prompt-chips`. Examples: *"give me winners from past 5 years"*, *"all Old Navy tests on product page"*, *"category page facets"*. Clicking a chip pre-fills the input but does **not** auto-submit. Hide the row once the user types more than 3 characters. | [Meeting 4/Meeting_Details.md](../Meeting%204/Meeting_Details.md) §6.2 |
| **Per-result Learning / Recommendation snippet** | Every result card (and every citation reference returned by `/chat`) renders a 1-2 line `learning_snippet` between the title and the KPI strip. Source field is `references[].chunkInfo.documentMetadata.structData.learning_snippet`. Truncate at 240 chars with a `Read full page` link to the Confluence URL. | [Meeting 4/Meeting_Details.md](../Meeting%204/Meeting_Details.md) §7 |
| **No aggregate result summary** | Do NOT render a Glean-style summary above the result list. Each card carries its own learning; aggregating across a noisy result set is explicitly rejected. | [Meeting 4/Meeting_Details.md](../Meeting%204/Meeting_Details.md) §7 |

---

## 9. Error handling

| HTTP status | UX |
|---|---|
| `400 Bad Request` | Prompt-filter rejection (length cap, injection patterns, off-topic). Show the message body inline with an "Edit your question" affordance; do NOT retry. |
| `401 Unauthorized` | Cookie expired. Redirect to `/auth/login`. |
| `403 Forbidden` | Cross-user access attempt. Show a generic "You don't have access to this conversation" and route back to `/chat`. |
| `404 Not Found` | Session was deleted in another tab. Invalidate `['sessions']` and route to `/chat`. |
| `429 Too Many Requests` | Rate limit at the gateway. Show "Slow down, try again in a few seconds" with an auto-retry after 5s. |
| `5xx` | Backend or VAIS failure. Show a retry banner; do **not** auto-retry `/chat` (turns are not idempotent on the user side - VAIS may have already appended). |
| `timeout > 30s` | Surface a fallback message "This is taking longer than expected" but keep the request open until the backend deadline (300s server-side). |

---

## 10. Environment variables

| Var | Example | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `https://genai-discovery.gap.com` (prod) / `http://localhost:8080` (dev) | Base for `/api/genai/*` |
| `VITE_AUTH_REDIRECT_URI` | `https://genai-discovery.gap.com/auth/callback` | Round-trip target for OAuth |
| `VITE_LOG_LEVEL` | `info` / `debug` | Client-side log verbosity |
| `VITE_FEATURE_DASHBOARD` | `true` / `false` | Toggle the Executive dashboard route |

All `VITE_*` vars must be set at build time. None of them contain secrets - the OAuth client secret lives only in the backend.

---

## 11. Local dev, build, deploy

### Local dev
```bash
npm install
npm run dev          # vite dev server with hot reload on http://localhost:5173
```
Pair with a locally running backend at `http://localhost:8080` (see Backend Guide section 16). The Vite proxy in section 5 injects `X-Dev-User-Id` so you bypass OAuth in dev.

### Build
```bash
npm run build        # produces dist/
npm run preview      # serves dist/ on http://localhost:4173 for a smoke check
```

### Container (Cloud Build)
```Dockerfile
# Dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```
- **Cloud Build trigger:** on `main` push, builds and pushes to Artifact Registry repo `gap-web` in `us-central1`.
- **Cloud Run service:** `gap-genai-discovery-web` (2 vCPU / 2 GiB, min/max 0/10, concurrency 80, us-central1). Public ingress with IAP enabled on the Cloud Run service (Cloud Run native IAP).
- **CD:** Cloud Build updates the Cloud Run revision; traffic is shifted 100% on green.

### Smoke checklist before merging to `main`
1. `npm run build` is clean.
2. `npm run test` passes (Vitest).
3. A Playwright run against a dev backend completes: load `/`, create chat, send one turn, see citations, thumb up, delete chat.
4. Lighthouse score > 90 on `/chat/:sessionId` (no large images, no client-side LLM).
