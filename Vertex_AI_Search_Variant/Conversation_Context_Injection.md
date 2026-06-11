# Carrying Frontend-Only Context Into the RAG Call

> **Scenario.** The first N turns of a conversation are handled deterministically by the frontend — no LLM, no retrieval. Examples: a guided intake ("Which brand?" → "Old Navy") or a quick-action menu ("What's a TLCOE?" → static card). When the user finally asks an open question, the backend must call Discovery Engine `:answer` / `:streamAnswer` **with the context of those deterministic turns**, even though Vertex AI Search has no record of them.
>
> This doc answers "how do we get that context in?" Companion to [Session_API_Reference.md](Session_API_Reference.md), [Streaming_Answer_Guide.md](Streaming_Answer_Guide.md), [Multi_Session_Flow.md](Multi_Session_Flow.md).

---

## 1. What you can and cannot do with Discovery Engine sessions

| Operation | Supported? |
|---|---|
| Create an empty session (`POST /sessions`) | ✅ |
| Append a turn by calling `:answer` / `:streamAnswer` with `session=...` | ✅ |
| **Manually inject a `{query, answer}` turn without invoking the model** | ❌ — `sessions.patch` `updateMask` only accepts `state`, `displayName`, `isPinned`, `labels`, `userPseudoId`. **There is no way to write a turn directly.** |
| Override the generator's system prompt per request | ✅ via `answerGenerationSpec.promptSpec.preamble` |
| Constrain retrieval per request | ✅ via `searchSpec.searchParams.filter` |
| Influence the next answer with arbitrary text | ✅ — embed it in `query.text` |

**Implication:** the deterministic turns will **never** live inside the Discovery Engine session. They live in the **frontend** (and optionally the BFF's own datastore). The backend's job is to *re-inject* the relevant pieces on every LLM-bound call.

---

## 2. Three injection levers (use them together)

| Lever | Best for | Goes into | Persisted in DE session? |
|---|---|---|---|
| `query.text` prefix | One-shot context for the first LLM-bound turn | The user-visible question | ✅ (stored as the turn's query) |
| `answerGenerationSpec.promptSpec.preamble` | Stable conversational state (persona, tone, framing) | A system-prompt prefix sent to the generator only | ❌ (request-scoped) |
| `searchSpec.searchParams.filter` | Structured scoping (brand, region, date range) | The retrieval query, not the generator | ❌ (request-scoped, but shapes which chunks are seen) |

**Use all three together** when each piece of deterministic state has a natural home. Examples:

- "User selected brand = Old Navy" → **filter** `brand="Old Navy"` (retrieval is now scoped — much higher answer quality than putting it in the prompt).
- "User chose persona = Executive (TL;DR style)" → **preamble** `"Reply in 3 sentences max, no bullet lists."`
- "User typed: 'experiments from Q1 2026'" → **query text** (it's already a question; pass it through).

---

## 3. Recommended end-to-end pattern

### 3.1 Frontend state

The frontend keeps its own conversation log. Each entry is one of:

```ts
type ChatEntry =
  | { kind: "deterministic"; role: "user" | "system"; text: string;
      facets?: Record<string, string> }    // structured selections, e.g. { brand: "Old Navy" }
  | { kind: "llm"; role: "user" | "assistant"; text: string;
      session_id?: string; answer_id?: string };
```

While `kind === "deterministic"`, the frontend renders bubbles locally. **No HTTP call to the backend.** Nothing is sent to Discovery Engine.

### 3.2 Lazy session creation

Do **not** create the Discovery Engine session for deterministic turns. Wait until the first `kind === "llm"` turn:

```
deterministic-only conversation → no DE session, no /chat/stream call
first LLM-bound user message    → BFF creates DE session, then calls :streamAnswer
subsequent messages             → reuse the same session
```

Benefits: no wasted session rows in Discovery Engine, no synthetic data in your eval pipeline, no "phantom" entries in the sidebar.

### 3.3 Request shape from frontend → BFF

When the frontend posts the first LLM-bound turn, it sends both the question and the deterministic context it gathered:

```http
POST /api/genai/chat/stream
Content-Type: application/json

{
  "text": "What experiments have we run recently?",
  "session_id": null,                              // null → BFF creates one
  "context": {
    "facets": { "brand": "Old Navy", "region": "US" },
    "persona": "analyst",
    "preface_turns": [
      { "role": "system",    "text": "Guided intake started." },
      { "role": "user",      "text": "I want help finding experiments." },
      { "role": "assistant", "text": "Sure — for which brand?" },
      { "role": "user",      "text": "Old Navy" },
      { "role": "assistant", "text": "And which region?" },
      { "role": "user",      "text": "US" }
    ]
  }
}
```

On subsequent turns the frontend still sends `context` (so persona/facets stay in effect) but **omits** `preface_turns` — those are only useful on the **first** call.

### 3.4 BFF translation — FastAPI

Add a small builder that translates the frontend `context` into the three Discovery Engine levers.

```python
# app/services/context_injection.py
from typing import Optional, Sequence
from pydantic import BaseModel

class PrefaceTurn(BaseModel):
    role: str            # "user" | "assistant" | "system"
    text: str

class FrontendContext(BaseModel):
    facets: dict[str, str] = {}
    persona: Optional[str] = None
    preface_turns: list[PrefaceTurn] = []

PERSONA_PREAMBLES = {
    "executive": "Reply in 3 sentences max. Lead with the headline number. No bullet lists.",
    "analyst":   "Be precise and quantitative. Cite every claim. Prefer tables when comparing items.",
    "engineer":  "Include exact field names and IDs. Show short code or query snippets where relevant.",
}

def build_preamble(ctx: FrontendContext) -> str:
    parts: list[str] = []
    if ctx.persona and ctx.persona in PERSONA_PREAMBLES:
        parts.append(PERSONA_PREAMBLES[ctx.persona])
    if ctx.facets:
        facet_str = ", ".join(f"{k}={v}" for k, v in ctx.facets.items())
        parts.append(
            f"The user has already constrained the conversation to: {facet_str}. "
            "Honour these constraints and do not ask the user to repeat them."
        )
    if ctx.preface_turns:
        # Render the guided-intake turns as transcript-style context.
        # Keep it short — preamble counts against the prompt budget.
        rendered = "\n".join(f"{t.role}: {t.text}" for t in ctx.preface_turns)
        parts.append(
            "Earlier in this conversation (handled outside the search system) "
            "the following was exchanged:\n" + rendered
        )
    return "\n\n".join(parts).strip()

def build_filter(ctx: FrontendContext) -> Optional[str]:
    """Convert facets to a Discovery Engine filter expression.

    Only call this for facets that are indexed as structData fields on your
    corpus. Unknown facets are ignored (left for preamble injection instead).
    """
    FILTERABLE = {"brand", "region", "year", "experiment_type"}
    clauses = [
        f'{k}: ANY("{v}")' for k, v in ctx.facets.items() if k in FILTERABLE
    ]
    return " AND ".join(clauses) or None

def build_query_text(user_text: str, ctx: FrontendContext, first_llm_turn: bool) -> str:
    """For the very first LLM-bound turn ONLY, prepend a one-line context cue
    so the model sees the constraint inside the user's message too. From turn 2
    onwards the DE session carries the history, so we don't repeat."""
    if not first_llm_turn or not ctx.facets:
        return user_text
    facet_str = ", ".join(f"{k}={v}" for k, v in ctx.facets.items())
    return f"[Scope: {facet_str}]\n{user_text}"
```

Wire it into the streaming endpoint from [Streaming_Answer_Guide.md](Streaming_Answer_Guide.md):

```python
# app/routes/chat_stream.py  (additions)

class ChatRequest(BaseModel):
    text: str
    session_id: str | None = None      # None → create on first turn
    context: FrontendContext = FrontendContext()

async def _proxy_stream(req: ChatRequest, user_id: str) -> AsyncIterator[bytes]:
    token = await get_access_token()

    # 1) Lazy session creation
    session_id = req.session_id
    if not session_id:
        session_id = await create_session(token, user_id)   # POST /sessions
        # Tell the frontend the new session ID up front so it can update its URL
        yield _sse("session", {"session_id": session_id})

    # 2) Build the three injections
    is_first_llm_turn = req.session_id is None
    preamble = build_preamble(req.context)
    filt     = build_filter(req.context)
    query    = build_query_text(req.text, req.context, is_first_llm_turn)

    body = {
        "query": {"text": query},
        "session": (
            f"projects/{settings.PROJECT_ID}/locations/{settings.LOCATION}"
            f"/collections/default_collection/engines/{settings.ENGINE_ID}"
            f"/sessions/{session_id}"
        ),
        "userPseudoId": user_id,
        "answerGenerationSpec": {
            "includeCitations": True,
            "ignoreAdversarialQuery": True,
            **({"promptSpec": {"preamble": preamble}} if preamble else {}),
        },
        **({"searchSpec": {"searchParams": {"filter": filt}}} if filt else {}),
    }

    # ... (rest of the streaming proxy is unchanged — see Streaming_Answer_Guide.md §4.2)
```

The first-turn `session` event lets the frontend write `/chat/{new_session_id}` into its URL before the answer starts streaming.

---

## 4. Worked example

### Frontend log after guided intake (no HTTP traffic yet)

```
[deterministic] system     "Guided intake started."
[deterministic] assistant  "Hi — what are you investigating?"
[deterministic] user       "Experiments"
[deterministic] assistant  "For which brand?"
[deterministic] user       "Old Navy"
[deterministic] assistant  "And which region?"
[deterministic] user       "US"
[deterministic] assistant  "Got it. Ask me anything about Old Navy US experiments."
```

The frontend has facets `{brand: "Old Navy", region: "US"}` and persona `"analyst"`.

### First LLM-bound user message

> User types: **"What experiments did we run on the PDP?"**

The frontend posts:

```json
{
  "text": "What experiments did we run on the PDP?",
  "session_id": null,
  "context": {
    "facets":  { "brand": "Old Navy", "region": "US" },
    "persona": "analyst",
    "preface_turns": [
      {"role":"assistant","text":"Hi — what are you investigating?"},
      {"role":"user","text":"Experiments"},
      {"role":"assistant","text":"For which brand?"},
      {"role":"user","text":"Old Navy"},
      {"role":"assistant","text":"And which region?"},
      {"role":"user","text":"US"}
    ]
  }
}
```

### BFF translates and calls Discovery Engine

```jsonc
POST /servingConfigs/default_search:streamAnswer
{
  "query": {
    "text": "[Scope: brand=Old Navy, region=US]\nWhat experiments did we run on the PDP?"
  },
  "session": "projects/.../sessions/<new-id>",
  "userPseudoId": "<oauth-sub>",
  "answerGenerationSpec": {
    "includeCitations": true,
    "ignoreAdversarialQuery": true,
    "promptSpec": {
      "preamble":
        "Be precise and quantitative. Cite every claim. Prefer tables when comparing items.\n\n"
        "The user has already constrained the conversation to: brand=Old Navy, region=US. "
        "Honour these constraints and do not ask the user to repeat them.\n\n"
        "Earlier in this conversation (handled outside the search system) the following was exchanged:\n"
        "assistant: Hi — what are you investigating?\nuser: Experiments\n"
        "assistant: For which brand?\nuser: Old Navy\n"
        "assistant: And which region?\nuser: US"
    }
  },
  "searchSpec": {
    "searchParams": { "filter": "brand: ANY(\"Old Navy\") AND region: ANY(\"US\")" }
  }
}
```

### Second LLM-bound message (same session)

> User types: **"Just the wins, please."**

Frontend posts:

```json
{
  "text": "Just the wins, please.",
  "session_id": "<id-from-the-session-event>",
  "context": { "facets": {"brand": "Old Navy", "region": "US"}, "persona": "analyst" }
}
```

No `preface_turns` this time — the Discovery Engine session now contains the previous LLM turn, so the model already knows we were discussing PDP experiments on Old Navy US. The BFF still passes `preamble` (persona + facets) and `filter` because those are request-scoped on Discovery Engine.

The DE session's turn list after this call:
```
turns[0].query: "[Scope: brand=Old Navy, region=US] What experiments did we run on the PDP?"
turns[0].answer: "..."
turns[1].query: "Just the wins, please."
turns[1].answer: "..."
```

---

## 5. Anti-patterns to avoid

1. **Creating the DE session at page load.** It will sit empty until the user finishes guided intake, and may never be used. Create lazily.
2. **Calling `:answer` with a canned answer just to "seed" the session.** This wastes an LLM call, burns money, and pollutes the session with synthetic content. Use `preamble` instead.
3. **Putting structured facets in `preamble` only.** The model may forget them mid-conversation. If a facet maps to an indexed field, put it in `filter` — it scopes *retrieval*, which is far stronger than a soft hint to the generator.
4. **Re-sending `preface_turns` on every call.** After the first LLM turn the DE session already carries the conversation forward. Sending the intake transcript again only burns prompt tokens. Send it once, on the first LLM-bound turn.
5. **Storing the deterministic turns in BigQuery as if they were real turns.** They didn't go through Discovery Engine and have no `queryId` / `answer` resource name — they'll confuse downstream eval, telemetry, and the sidebar's `turn_count`. Either skip them in the analytics schema, or tag them `kind: "deterministic"` so reports can filter them out.

---

## 6. Token-budget guardrails

`promptSpec.preamble` counts against the model's input window. Today's Discovery Engine generator (`gemini-2.5-flash` / `gemini-2.5-pro` under the hood) has a large context, but the **answer-quality cliff** kicks in well before the hard limit. Recommend:

| Field | Soft cap | Hard cap |
|---|---|---|
| `preamble` total | 1 200 chars | 4 000 chars |
| `preface_turns` (count) | 6 turns | 20 turns |
| Single `preface_turn.text` | 200 chars | 1 000 chars |

If your intake legitimately exceeds these, summarise on the BFF before injecting (a 5-line bullet list of selections is fine; a verbatim 20-turn transcript is not).

---

## 7. Quick checklist

Frontend:

- [ ] Render deterministic turns locally; no `/api/genai/chat/*` call during intake
- [ ] Track `facets`, `persona`, `preface_turns` in component state
- [ ] On first LLM-bound message: POST without `session_id`, include full `context`
- [ ] On subsequent messages: POST with `session_id` returned in the `session` event, include `facets` + `persona` but **omit** `preface_turns`
- [ ] Listen for the `session` SSE event and update the route to `/chat/{id}`

Backend (BFF):

- [ ] Accept `context: { facets, persona, preface_turns }` on `POST /chat/stream`
- [ ] Lazy-create the Discovery Engine session when `session_id is None`
- [ ] Emit a `session` SSE event with the new ID before the first `delta`
- [ ] Compose `answerGenerationSpec.promptSpec.preamble` from persona + facets + first-turn preface
- [ ] Compose `searchSpec.searchParams.filter` from facets that map to indexed fields
- [ ] Prepend `[Scope: ...]` to `query.text` **only** on the first LLM-bound turn
- [ ] Enforce token-budget caps before sending

---

## 8. Reference

- [Session_API_Reference.md](Session_API_Reference.md) — base REST surface, what `sessions.patch` does and does not let you mutate.
- [Streaming_Answer_Guide.md](Streaming_Answer_Guide.md) — the streaming endpoint this pattern plugs into.
- [Multi_Session_Flow.md](Multi_Session_Flow.md) — end-to-end conversation flow (sidebar, resume, etc.).
- Google REST docs: `discoveryengine.googleapis.com/v1`, message `AnswerGenerationSpec.PromptSpec`, message `SearchSpec.SearchParams.filter`.
