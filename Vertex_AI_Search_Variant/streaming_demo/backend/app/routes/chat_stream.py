"""Streaming chat endpoint.

Re-emits Discovery Engine's `:streamAnswer` output (a streamed top-level JSON
array, *not* SSE) as Server-Sent Events that browsers can consume natively.

Event vocabulary (matches Streaming_Answer_Guide.md §3):
- references : { references: [...] }      emitted once, ~1.5s in
- delta      : { text: "<fragment>" }      append-only fragment
- citation   : { citations: [...] }        zero or more, mid-stream (rare in practice)
- done       : { session_id, answer_id, state, citations, references, answerText }
- error      : { code, message }           terminal on failure

Fixes vs. the published guide:
1. Citation event always carries a list (`citations`) instead of a wobbly
   single-vs-array shape that silently dropped items when len > 1.
2. Upstream body is consumed via `aiter_bytes()` + manual UTF-8 decode so we
   don't depend on the response declaring `charset=UTF-8`.
3. The `done` payload includes the assembled `answerText` so smoke tests can
   verify delta concatenation in one round-trip.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.gcp_auth import get_access_token
from app.json_array_parser import JsonArrayParser

log = logging.getLogger(__name__)
router = APIRouter()


class ChatStreamRequest(BaseModel):
    text: str
    session_id: str
    user_pseudo_id: str | None = None


def _sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode(
        "utf-8"
    )


async def _proxy_stream(req: ChatStreamRequest) -> AsyncIterator[bytes]:
    token = await get_access_token()
    url = f"{settings.base_url}/servingConfigs/{settings.serving_config}:streamAnswer"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Goog-User-Project": settings.project_id,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body: dict = {
        "query": {"text": req.text},
        "session": settings.session_path(req.session_id),
        "answerGenerationSpec": {
            "includeCitations": True,
            "ignoreAdversarialQuery": True,
        },
    }
    if req.user_pseudo_id:
        body["userPseudoId"] = req.user_pseudo_id

    parser = JsonArrayParser()
    decoder_errors = "replace"
    refs_sent = False
    accumulated_text = ""
    last_state: str | None = None
    final_ans: dict = {}
    timeout = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=True) as client:
            async with client.stream("POST", url, headers=headers, json=body) as up:
                if up.status_code != 200:
                    err = (await up.aread()).decode("utf-8", errors=decoder_errors)[:500]
                    log.error("streamAnswer %s: %s", up.status_code, err)
                    yield _sse(
                        "error",
                        {"code": f"upstream_{up.status_code}", "message": err},
                    )
                    return

                async for piece in up.aiter_bytes():
                    if not piece:
                        continue
                    text = piece.decode("utf-8", errors=decoder_errors)
                    for obj in parser.feed(text):
                        ans = obj.get("answer") or obj
                        state = ans.get("state")
                        last_state = state or last_state

                        refs = ans.get("references")
                        if refs and not refs_sent:
                            yield _sse("references", {"references": refs})
                            refs_sent = True

                        txt = ans.get("answerText")
                        if txt and state != "SUCCEEDED":
                            accumulated_text += txt
                            yield _sse("delta", {"text": txt})

                        cites = ans.get("citations")
                        if cites and state != "SUCCEEDED":
                            yield _sse("citation", {"citations": cites})

                        if state == "SUCCEEDED":
                            final_ans = ans
                            answer_text = ans.get("answerText") or accumulated_text
                            yield _sse(
                                "done",
                                {
                                    "session_id": req.session_id,
                                    "answer_id": (ans.get("name") or "").rsplit("/", 1)[-1] or None,
                                    "state": "SUCCEEDED",
                                    "answerText": answer_text,
                                    "citations": ans.get("citations", []),
                                    "references": ans.get("references", []),
                                },
                            )
                            return

    except httpx.ReadTimeout:
        log.warning("streamAnswer upstream read timeout")
        yield _sse(
            "error",
            {"code": "upstream_timeout", "message": "Vertex AI Search timed out"},
        )
        return
    except asyncio.CancelledError:
        log.info("client cancelled stream; closing upstream")
        raise
    except Exception as e:
        log.exception("streamAnswer proxy failed")
        yield _sse("error", {"code": "proxy_error", "message": str(e)})
        return

    # Stream ended without SUCCEEDED frame - emit a defensive done with what we
    # have so the frontend always sees a terminal event.
    yield _sse(
        "done",
        {
            "session_id": req.session_id,
            "answer_id": (final_ans.get("name") or "").rsplit("/", 1)[-1] or None,
            "state": last_state or "UNKNOWN",
            "answerText": accumulated_text,
            "citations": final_ans.get("citations", []),
            "references": final_ans.get("references", []),
        },
    )


@router.post("/api/genai/chat/stream")
async def chat_stream(req: ChatStreamRequest) -> StreamingResponse:
    return StreamingResponse(
        _proxy_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
