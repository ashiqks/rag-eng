"""Google Cloud auth via Application Default Credentials.

Caches the credential object across requests; google-auth handles refresh
internally when the token nears expiry.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Optional

import google.auth
import google.auth.transport.requests
from google.auth.credentials import Credentials

log = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
_lock = asyncio.Lock()
_creds: Optional[Credentials] = None


def _load_adc() -> Credentials:
    creds, project = google.auth.default(scopes=_SCOPES)
    log.info("loaded ADC for project=%s type=%s", project, type(creds).__name__)
    return creds


def _refresh_sync(creds: Credentials) -> None:
    creds.refresh(google.auth.transport.requests.Request())


async def get_access_token() -> str:
    global _creds
    async with _lock:
        if _creds is None:
            try:
                _creds = await asyncio.to_thread(_load_adc)
            except Exception as e:
                log.warning(
                    "ADC unavailable (%s). Falling back to `gcloud auth print-access-token`. "
                    "For production, run `gcloud auth application-default login`.",
                    e,
                )
                return await asyncio.to_thread(_gcloud_token_fallback)

        if not _creds.valid:
            await asyncio.to_thread(_refresh_sync, _creds)
        token = _creds.token
        if not token:
            raise RuntimeError("ADC returned no token after refresh")
        return token


def _gcloud_token_fallback() -> str:
    out = subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True, shell=True
    )
    return out.strip()
