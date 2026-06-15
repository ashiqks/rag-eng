"""Thin proxies for Discovery Engine session create/get."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.gcp_auth import get_access_token

log = logging.getLogger(__name__)
router = APIRouter()


class CreateSessionRequest(BaseModel):
    user_pseudo_id: str
    display_name: str | None = None


class CreateSessionResponse(BaseModel):
    session_id: str
    name: str


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "X-Goog-User-Project": settings.project_id,
        "Content-Type": "application/json",
    }


@router.post("/api/genai/sessions", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    token = await get_access_token()
    body: dict = {"userPseudoId": req.user_pseudo_id}
    if req.display_name:
        body["displayName"] = req.display_name
    async with httpx.AsyncClient(timeout=30, trust_env=True) as client:
        r = await client.post(
            f"{settings.base_url}/sessions",
            headers=_headers(token),
            json=body,
        )
    if r.status_code != 200:
        log.error("create_session %s: %s", r.status_code, r.text[:500])
        raise HTTPException(status_code=r.status_code, detail=r.text[:500])
    name = r.json().get("name", "")
    return CreateSessionResponse(session_id=name.rsplit("/", 1)[-1], name=name)


@router.get("/api/genai/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    token = await get_access_token()
    async with httpx.AsyncClient(timeout=30, trust_env=True) as client:
        r = await client.get(
            f"{settings.base_url}/sessions/{session_id}",
            headers=_headers(token),
            params={"includeAnswerDetails": "true"},
        )
    if r.status_code != 200:
        log.error("get_session %s: %s", r.status_code, r.text[:500])
        raise HTTPException(status_code=r.status_code, detail=r.text[:500])
    return r.json()
