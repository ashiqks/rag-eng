# Streaming Answer Guide — Discovery Engine `:streamAnswer`

> End-to-end recipe for wiring Vertex AI Search streaming answers through the Backend (FastAPI) to the Web App (React). All upstream behaviour below was verified end-to-end on 2026-06-09 against the live engine `gap-erd-discovery_1779708094567` in project `prj-0n-dta-pt-ai-sandbox` — see [`tests/stream_smoke.py`](../tests/stream_smoke.py) for the test harness used to produce the measurements quoted here.

---

## 1. Why streaming

Measured numbers (4 445-character answer, 30 citations, 10 references):

| Metric | `:answer` | `:streamAnswer` |
|---|---|---|
| First byte from Google | 7.26 s | **1.48 s** |
| First user-visible text | 7.26 s | **2.09 s** |
| All references available | 7.26 s | **1.48 s** (chunk #2) |
| Complete answer + citations | 7.26 s | 6.93 s |
| Number of upstream chunks | 1 | 84 |
| Cost | identical | identical |

**Use `:streamAnswer` for the chat surface.** ~5 s faster perceived latency. Keep `:answer` for the eval harness, agents, and any non-interactive consumer.

---

## 2. What Google actually returns

> **Important:** Discovery Engine `:streamAnswer` does **NOT** return Server-Sent Events. It returns a **streaming JSON array** over a chunked HTTP response. Several public examples and earlier drafts of this doc were wrong about this — confirmed by direct testing.

Response headers:

```
HTTP/1.1 200 OK
Content-Type: application/json; charset=UTF-8
Transfer-Encoding: chunked
```

Response body:

```
[
  { "answer": { "state": "STREAMING", "answerText": "" } },
  { "answer": { "state": "STREAMING", "references": [...10 items...] } },
  { "answer": { "state": "STREAMING", "answerText": "Old" } },
  { "answer": { "state": "STREAMING", "answerText": " Navy has conducted" } },
  ...
  { "answer": { "state": "STREAMING", "citations": [ {...one citation...} ] } },
  { "answer": { "state": "STREAMING", "answerText": " several experiments" } },
  ...
  { "answer": {
      "state": "SUCCEEDED",
      "name": ".../sessions/.../answers/...",
      "answerText": "<the full 4445-character answer>",
      "citations": [ ...all 30... ],
      "references": [ ...all 10... ]
  } }
]
```

Three kinds of chunks appear during streaming:

1. **Text deltas** — `answer.answerText` contains the **next fragment** (typically 3–200 chars). **NOT cumulative.** Concatenate them in order to rebuild the answer.
2. **Citation markers** — `answer.citations` contains a single citation object, no text. Emitted in line with the text it cites.
3. **References block** — `answer.references` is emitted **once, in the second chunk**, with all source documents. Lets the UI render the "Sources" panel almost immediately.

The **final** chunk has `state: "SUCCEEDED"` and re-emits the full `answerText`, all citations, and all references. Use it for persistence/verification, not for re-rendering.

Error chunks set `answer.state` to `FAILED` (with the partial text up to the failure).

---

## 3. Architecture at a glance

```
Browser (React)              Backend (FastAPI / Cloud Run)         Vertex AI Search
────────────────              ────────────────────────────         ─────────────────
fetch('/api/genai/chat/stream')
   ──── POST {text,session_id} ──▶
                                  POST :streamAnswer  ──────────────▶
                                                                       (streaming JSON array)
                                  ◀────── application/json (chunked) ─
                                  parse incrementally, re-emit as SSE
   ◀──── text/event-stream ──────
   (delta / references / citation / done events)
   render tokens as they arrive
```

The backend **translates** the upstream JSON-array stream into SSE for the browser. Reasons:

- Browsers can stream `text/event-stream` natively; parsing a streamed JSON array in JS requires custom buffering and a brace-depth scanner (exactly what the backend does in Python).
- We can drop fields the UI doesn't need (`relatedQuestions`, query-classification, etc.) and shrink payloads on the wire.
- We unify the event shape: one event type per UI concern.

Browser-side event types:

| Event | Payload | When |
|---|---|---|
| `references` | `{ references: [...] }` | once, ~1.5 s in |
| `delta` | `{ text: "<fragment>" }` | each text chunk |
| `citation` | `{ citation: {...} }` | each citation chunk (often empty mid-stream; final list is in `done`) |
| `done` | `{ session_id, answer_id, state, citations, references }` | terminal |
| `error` | `{ code, message }` | terminal on failure |

---

## 4. Backend — FastAPI streaming endpoint

### 4.1 REST surface

```
POST /api/genai/chat/stream
Content-Type: application/json
Accept: text/event-stream

{ "text": "...", "session_id": "..." }

→ 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

### 4.2 Implementation — `app/routes/chat_stream.py`

The critical piece is the **incremental JSON-array parser**. We can't `json.loads()` the upstream body because it only closes the outer `]` at the very end — we'd buffer the entire response and defeat the point of streaming. Instead we track brace/string state and emit each top-level object as soon as its closing `}` arrives.

```python
import json
import logging
from typing import AsyncIterator

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import current_user
from app.config import settings
from app.gcp_auth import get_access_token

log = logging.getLogger(__name__)
router = APIRouter()

VAIS_BASE = (
    f"https://discoveryengine.googleapis.com/v1"
    f"/projects/{settings.PROJECT_ID}"
    f"/locations/{settings.LOCATION}"
    f"/collections/default_collection"
    f"/engines/{settings.ENGINE_ID}"
)


class ChatRequest(BaseModel):
    text: str
    session_id: str


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


class JsonArrayParser:
    """Stateful incremental parser for a streamed top-level JSON array.

    Feed it chunks of text via .feed(chunk); it yields each fully-formed
    top-level object as soon as its closing brace arrives.
    """

    def __init__(self) -> None:
        self.buf = ""
        self.depth = 0
        self.in_str = False
        self.esc = False
        self.start = -1

    def feed(self, chunk: str):
        if not chunk:
            return
        scan_from = len(self.buf)
        self.buf += chunk
        i = scan_from
        while i < len(self.buf):
            c = self.buf[i]
            if self.in_str:
                if self.esc:
                    self.esc = False
                elif c == "\\":
                    self.esc = True
                elif c == '"':
                    self.in_str = False
            elif c == '"':
                self.in_str = True
            elif c == "{":
                if self.depth == 0:
                    self.start = i
                self.depth += 1
            elif c == "}":
                self.depth -= 1
                if self.depth == 0 and self.start >= 0:
                    raw = self.buf[self.start : i + 1]
                    self.start = -1
                    try:
                        yield json.loads(raw)
                    except json.JSONDecodeError:
                        log.warning("malformed JSON object in stream, skipped")
            i += 1
        # Trim buffer between objects to keep memory bounded
        if self.depth == 0 and self.start == -1 and len(self.buf) > 65536:
            self.buf = ""


async def _proxy_stream(req: ChatRequest, user_id: str) -> AsyncIterator[bytes]:
    token = await get_access_token()
    url = f"{VAIS_BASE}/servingConfigs/default_search:streamAnswer"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Goog-User-Project": settings.PROJECT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = {
        "query": {"text": req.text},
        "session": (
            f"projects/{settings.PROJECT_ID}/locations/{settings.LOCATION}"
            f"/collections/default_collection/engines/{settings.ENGINE_ID}"
            f"/sessions/{req.session_id}"
        ),
        "userPseudoId": user_id,
        "answerGenerationSpec": {
            "includeCitations": True,
            "ignoreAdversarialQuery": True,
        },
    }

    parser = JsonArrayParser()
    refs_sent = False
    final_obj: dict | None = None
    timeout = httpx.Timeout(connect=5.0, read=120.0, write=10.0, pool=5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream("POST", url, headers=headers, json=body) as up:
                if up.status_code != 200:
                    err = (await up.aread()).decode(errors="replace")[:500]
                    log.error("streamAnswer %s: %s", up.status_code, err)
                    yield _sse("error", {"code": f"upstream_{up.status_code}", "message": err})
                    return

                async for piece in up.aiter_text():
                    for obj in parser.feed(piece):
                        final_obj = obj
                        ans = obj.get("answer") or obj
                        state = ans.get("state")

                        refs = ans.get("references")
                        if refs and not refs_sent:
                            yield _sse("references", {"references": refs})
                            refs_sent = True

                        txt = ans.get("answerText")
                        if txt and state != "SUCCEEDED":
                            yield _sse("delta", {"text": txt})

                        cites = ans.get("citations")
                        if cites and state != "SUCCEEDED":
                            yield _sse("citation", {"citation": cites[0] if len(cites) == 1 else cites})

                        if state == "SUCCEEDED":
                            yield _sse("done", {
                                "session_id": req.session_id,
                                "answer_id": ans.get("name", "").split("/")[-1] or None,
                                "state": "SUCCEEDED",
                                "citations": ans.get("citations", []),
                                "references": ans.get("references", []),
                            })
                            return

        except httpx.ReadTimeout:
            yield _sse("error", {"code": "upstream_timeout", "message": "Vertex AI Search timed out"})
            return
        except Exception as e:
            log.exception("streamAnswer proxy failed")
            yield _sse("error", {"code": "proxy_error", "message": str(e)})
            return

    # Defensive: stream ended without SUCCEEDED frame.
    ans = (final_obj or {}).get("answer") or final_obj or {}
    yield _sse("done", {
        "session_id": req.session_id,
        "answer_id": ans.get("name", "").split("/")[-1] or None,
        "state": ans.get("state", "UNKNOWN"),
        "citations": ans.get("citations", []),
        "references": ans.get("references", []),
    })


@router.post("/api/genai/chat/stream")
async def chat_stream(req: ChatRequest, user=Depends(current_user)):
    return StreamingResponse(
        _proxy_stream(req, user_id=user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

> **Tip — simpler alternative using the official SDK.** If you already use `google-cloud-discoveryengine`, the SDK exposes `client.stream_answer_query(request=...)` (sync) or its async counterpart, which returns an iterator of `AnswerQueryResponse` protos. Same chunk semantics (references-then-deltas-then-final), no JSON parsing required. Prefer the SDK in new code; the raw-HTTP version above is shown so you understand the wire format.

### 4.3 Token / auth handling

- The Backend authenticates the **caller** (Web App SA via `run.invoker`) with the existing FastAPI dependency.
- The Backend authenticates **itself** to Vertex AI Search via ADC. In Cloud Run that's the runtime SA — grant it `roles/discoveryengine.editor`.
- Do **not** forward the user's id-token to Vertex AI Search.

### 4.4 Cloud Run gotchas

- Request timeout: **300 s** (default 60 s will cut long answers).
- CPU allocation: **always-on**; otherwise CPU is throttled between chunks and the SSE stalls.
- Header: `X-Accel-Buffering: no` defeats L7 load-balancer buffering.
- Streaming consumes one in-flight request per concurrent user. Size `maxInstances` × concurrency accordingly.

---

## 5. Frontend — React consumer

### 5.1 Why `fetch` + `ReadableStream` instead of `EventSource`

`EventSource` only supports GET and can't send a JSON body. Our stream endpoint is a POST, so we use `fetch` with a streaming reader. Same pattern as ChatGPT, Gemini, Claude.

### 5.2 Hook — `useStreamingChat.ts`

```ts
import { useCallback, useRef, useState } from "react";

export type ChatStreamState = {
  text: string;
  references: unknown[];
  citations: unknown[];
  isStreaming: boolean;
  error: string | null;
  answerId: string | null;
};

const initial: ChatStreamState = {
  text: "",
  references: [],
  citations: [],
  isStreaming: false,
  error: null,
  answerId: null,
};

export function useStreamingChat() {
  const [state, setState] = useState<ChatStreamState>(initial);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(async (sessionId: string, text: string) => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setState({ ...initial, isStreaming: true });

    let resp: Response;
    try {
      resp = await fetch("/api/genai/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
        },
        body: JSON.stringify({ session_id: sessionId, text }),
        signal: ac.signal,
        credentials: "include",
      });
    } catch (e: any) {
      setState((s) => ({ ...s, isStreaming: false, error: e.message ?? "network error" }));
      return;
    }
    if (!resp.ok || !resp.body) {
      setState((s) => ({ ...s, isStreaming: false, error: `HTTP ${resp.status}` }));
      return;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    try {
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
          handleFrame(buf.slice(0, idx), setState);
          buf = buf.slice(idx + 2);
        }
      }
    } catch (e: any) {
      if (e.name !== "AbortError") {
        setState((s) => ({ ...s, isStreaming: false, error: e.message }));
      }
    } finally {
      setState((s) => ({ ...s, isStreaming: false }));
    }
  }, []);

  const cancel = useCallback(() => abortRef.current?.abort(), []);
  return { ...state, send, cancel };
}

function handleFrame(
  frame: string,
  setState: React.Dispatch<React.SetStateAction<ChatStreamState>>,
) {
  let event = "message";
  let dataLine = "";
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLine += line.slice(5).trim();
  }
  if (!dataLine) return;
  let data: any;
  try { data = JSON.parse(dataLine); } catch { return; }

  switch (event) {
    case "references":
      // Arrives early (~1.5 s) — render the Sources panel immediately
      setState((s) => ({ ...s, references: data.references ?? [] }));
      break;
    case "delta":
      // Pure delta — append, do NOT replace
      setState((s) => ({ ...s, text: s.text + (data.text ?? "") }));
      break;
    case "citation":
      setState((s) => ({ ...s, citations: [...s.citations, data.citation] }));
      break;
    case "done":
      // Authoritative final state — overwrite citations/references
      setState((s) => ({
        ...s,
        isStreaming: false,
        answerId: data.answer_id ?? null,
        citations: data.citations ?? s.citations,
        references: data.references ?? s.references,
      }));
      break;
    case "error":
      setState((s) => ({ ...s, isStreaming: false, error: data.message ?? "stream error" }));
      break;
  }
}
```

### 5.3 Component usage

```tsx
import { useStreamingChat } from "./useStreamingChat";

export function ChatBubble({ sessionId }: { sessionId: string }) {
  const { text, citations, references, isStreaming, error, send, cancel } = useStreamingChat();
  const [input, setInput] = useState("");

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    send(sessionId, input);
    setInput("");
  };

  return (
    <div className="chat">
      {references.length > 0 && <SourcesPanel items={references} />}
      <div className="answer">
        {text}
        {isStreaming && <span className="cursor blink">▍</span>}
      </div>
      {!isStreaming && citations.length > 0 && <CitationList items={citations} />}
      {error && <div className="err">{error}</div>}

      <form onSubmit={onSubmit}>
        <input value={input} onChange={(e) => setInput(e.target.value)} disabled={isStreaming} />
        <button type="submit" disabled={isStreaming || !input.trim()}>Send</button>
        {isStreaming && <button type="button" onClick={cancel}>Stop</button>}
      </form>
    </div>
  );
}
```

The Stop button aborts the fetch, which closes the SSE socket. The backend sees the closed connection and tears down its upstream request to Discovery Engine — real cost savings, not just UI.

---

## 6. End-to-end smoke test

A working harness lives at [`tests/stream_smoke.py`](../tests/stream_smoke.py). It:

1. Loads project/engine config from `tests/eval/.env`.
2. Creates two fresh sessions (one for stream, one for non-stream).
3. Calls `:streamAnswer`, parses the streaming JSON array, prints per-chunk timing.
4. Calls `:answer` with the same query.
5. Compares the resulting text and reports whether they're identical.

Run it from the repo root:

```powershell
& .\tests\eval\.venv\Scripts\python.exe tests\stream_smoke.py
```

Expected (abridged) output from the last verified run on 2026-06-09:

```
<<< HTTP 200  Content-Type: application/json; charset=UTF-8  Transfer-Encoding: chunked
  obj # 1  +   0ch  total=   0  cites=0  refs=0   state=STREAMING  @t+1.48s
  obj # 2  +   0ch  total=   0  cites=0  refs=10  state=STREAMING  @t+1.48s
  obj # 3  +   3ch  total=   3  cites=0  refs=0   state=STREAMING  @t+2.09s
  obj # 4  +  19ch  total=  19  cites=0  refs=0   state=STREAMING  @t+2.20s
  ... 80 more chunks ...
  obj #84  +4445ch  total=4445  cites=30 refs=10  state=SUCCEEDED  @t+6.93s
<<< stream complete: 84 objects  first-byte=1.48s  total=6.93s  final_len=4445
[non-stream] HTTP 200  total=7.26s  text_len=4445  citations=30  state=SUCCEEDED
=== Comparison ===
text identical: True
```

### Direct curl against the upstream

If you want to see the raw upstream behaviour without the proxy:

```powershell
$token = gcloud auth print-access-token
$proj = "prj-0n-dta-pt-ai-sandbox"
$eng  = "gap-erd-discovery_1779708094567"
$sid  = "<EXISTING_SESSION_ID>"
$body = @{
  query = @{ text = "What experiments ran in Q1 2026?" }
  session = "projects/$proj/locations/global/collections/default_collection/engines/$eng/sessions/$sid"
  answerGenerationSpec = @{ includeCitations = $true }
} | ConvertTo-Json -Depth 4

curl.exe -N -X POST `
  "https://discoveryengine.googleapis.com/v1/projects/$proj/locations/global/collections/default_collection/engines/$eng/servingConfigs/default_search:streamAnswer" `
  -H "Authorization: Bearer $token" `
  -H "X-Goog-User-Project: $proj" `
  -H "Content-Type: application/json" `
  -d $body
```

You'll see the raw JSON array printed progressively as chunks land.

---

## 7. Operational notes

1. **Persistence happens upstream.** The turn is written to the session by Discovery Engine when the `SUCCEEDED` chunk is emitted. If the client aborts before that, the turn may not be persisted. After every stream, the frontend should refresh the session view by calling `GET /api/genai/sessions/{id}` (which proxies `GET sessions/{id}?includeAnswerDetails=true`).
2. **Don't trust mid-stream citations as final.** Use the `done` event's `citations` / `references` as the canonical lists.
3. **Concatenate deltas, never replace.** Each `delta.text` is a fresh fragment — `setText(s => s + delta.text)`. Replacing wipes out previously rendered text.
4. **Render the Sources panel on `references`** (arrives ~1.5 s after request). This is the single biggest UX win — users see a credible source list while the answer is still being typed.
5. **Logging.** Log one structured record on `done` with `session_id`, `answer_id`, `latency_ms`, `text_len`. Don't log every delta — noisy and expensive.
6. **Heartbeat.** If your L7 load balancer has an idle timeout < 60 s, emit an SSE comment (`: keepalive\n\n`) every 15 s during long generations. Discovery Engine itself produces chunks faster than that, so this is rarely needed.
7. **Fallback.** Keep the non-streaming `POST /api/genai/chat` endpoint available. If a corporate proxy strips chunked transfer (some do), the frontend can detect the failure and silently fall back.

---

## 8. Quick checklist

Backend:

- [ ] `httpx.AsyncClient` with `read=120 s` timeout
- [ ] **Incremental JSON-array parser** (brace-depth scanner) — not an SSE parser, not a single `json.loads`
- [ ] `StreamingResponse` with `text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`
- [ ] Five event types: `references`, `delta`, `citation`, `done`, `error`
- [ ] Cloud Run service: timeout 300 s, CPU always-on
- [ ] Runtime SA has `roles/discoveryengine.editor`

Frontend:

- [ ] `fetch` + `ReadableStream` (not `EventSource` — POST body required)
- [ ] `AbortController` wired to a Stop button
- [ ] **Append-only** delta rendering — `s.text + delta.text`
- [ ] Render `references` on arrival, not only on `done`
- [ ] Refresh session view from REST after `done`

---

## 9. Reference

- [Session_API_Reference.md](Session_API_Reference.md) — full REST surface, including the non-streaming `:answer` variant.
- [Conversation_Context_Injection.md](Conversation_Context_Injection.md) — how to pass deterministic frontend-only turns (guided intake, quick actions) into the RAG call without polluting the Discovery Engine session.
- [Backend_Developer_Guide.md](Backend_Developer_Guide.md) — overall service shape and existing endpoints.
- [Frontend_Developer_Guide.md](Frontend_Developer_Guide.md) — page layout, auth, citation rendering.
- [`tests/stream_smoke.py`](../tests/stream_smoke.py) — runnable verification harness.
- Google REST docs: `discoveryengine.googleapis.com/v1`, method `projects.locations.collections.engines.servingConfigs.streamAnswer`.
