# Streaming demo

A runnable, end-to-end exercise of the Discovery Engine `:streamAnswer`
pipeline described in
[../Streaming_Answer_Guide.md](../Streaming_Answer_Guide.md).
FastAPI backend, vanilla HTML/JS frontend, single localhost origin.

## Prerequisites

1. Python 3.10+ (`py -3 --version`).
2. ADC for the demo to authenticate to Vertex AI Search:
   ```powershell
   gcloud auth application-default login
   gcloud config set project prj-0n-dta-pt-ai-sandbox
   ```
   Your account must hold `roles/discoveryengine.editor` on the project.
3. Engine config in [../../tests/eval/.env](../../tests/eval/.env) (already
   populated for the POC).

## Run

```powershell
cd Vertex_AI_Search_Variant\streaming_demo\backend
.\run.ps1
```

Then open http://127.0.0.1:8765/ for the **vanilla** page.

### Optional: React variant

```powershell
cd Vertex_AI_Search_Variant\streaming_demo\frontend-react
npm install
npm run dev
```

Vite serves on http://127.0.0.1:5173 and proxies `/api/*` to the backend on
`:8765`. Both frontends talk to the same backend endpoints; pick whichever
you want to develop against.

## Smoke test (separate terminal, server already running)

```powershell
cd Vertex_AI_Search_Variant\streaming_demo
.\backend\.venv\Scripts\python.exe smoke.py
# or, against the React dev server's proxy:
.\backend\.venv\Scripts\python.exe smoke.py --base http://127.0.0.1:5173
```

The harness asserts:

- `references` event arrives before the first `delta`,
- at least 10 `delta` events,
- terminal `done.state == SUCCEEDED`,
- concatenated `delta.text` equals `done.answerText`,
- mid-stream citation count equals `done.citations` count (catches the
  guide's `cites[0] if len==1 else cites` bug).

## Layout

```
streaming_demo/
  backend/
    app/
      main.py              FastAPI entrypoint, mounts vanilla frontend at /
      config.py            loads tests/eval/.env
      gcp_auth.py          ADC + auto-refresh
      json_array_parser.py incremental top-level JSON-array parser
      routes/
        sessions.py        POST/GET /api/genai/sessions
        chat.py            POST /api/genai/chat (non-streaming fallback)
        chat_stream.py     POST /api/genai/chat/stream (SSE)
    requirements.txt
    run.ps1
  frontend/                          vanilla SSE client (served by FastAPI)
    index.html, app.js, styles.css
  frontend-react/                    React 18 + TypeScript + Vite
    src/
      App.tsx, main.tsx, useStreamingChat.ts, styles.css
    package.json, vite.config.ts, tsconfig.json
  smoke.py                           local smoke harness
  inspect_shapes.py                  one-shot helper that prints upstream
                                     reference/citation JSON shapes
```

## Fixes vs. the published guide

| # | Issue in `Streaming_Answer_Guide.md` | Fix in this demo |
|---|---|---|
| 1 | `chat_stream.py` emits `cites[0] if len(cites)==1 else cites` — silently drops items when a chunk carries multiple. | Always emit `{"citations": cites}` (a list). Frontend spreads. |
| 2 | `JsonArrayParser` only resets the buffer when it crosses 64 KB *between* objects — accumulates emitted bytes. | Trim buffer up to and including the closing `}` on every yield. |
| 3 | `aiter_text()` relies on the response declaring `charset=UTF-8`. | Use `aiter_bytes()` + manual `utf-8` decode. |
| 4 | `done` payload omits `answerText`. | Include `answerText` so smoke tests can assert delta concatenation. |
| 5 | Frontend `data:` line concatenation joins without `\n`. | Join with `\n` to be SSE-spec compliant. |
| 6 | No defensive terminal `done` if the stream ends without `SUCCEEDED`. | Guide had it; preserved here. |
