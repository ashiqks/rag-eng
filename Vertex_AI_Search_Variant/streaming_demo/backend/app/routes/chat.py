"""Non-streaming :answer fallback (parity with :streamAnswer)."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.gcp_auth import get_access_token

log = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    text: str
    session_id: str
    user_pseudo_id: str | None = None


@router.post("/api/genai/chat")
async def chat(req: ChatRequest) -> dict:
    token = await get_access_token()
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

    async with httpx.AsyncClient(timeout=120, trust_env=True) as client:
        r = await client.post(
            f"{settings.base_url}/servingConfigs/{settings.serving_config}:answer",
            headers={
                "Authorization": f"Bearer {token}",
                "X-Goog-User-Project": settings.project_id,
                "Content-Type": "application/json",
            },
            json=body,
        )
    if r.status_code != 200:
        log.error("answer %s: %s", r.status_code, r.text[:500])
        raise HTTPException(status_code=r.status_code, detail=r.text[:500])
    return r.json()
