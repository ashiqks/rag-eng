# Auth & FastAPI Setup — Cloud Run (prod) + Local Laptop (dev)

> **Scope:** how to authenticate a FastAPI backend that calls the Vertex AI Search (Discovery Engine) Sessions / Answer / Search APIs, both when running on **Cloud Run** and when running **locally on a developer laptop** using user Application Default Credentials (ADC).
>

---

## Table of contents

1. [Concepts in 60 seconds](#1-concepts-in-60-seconds)
2. [Prerequisites](#2-prerequisites)
3. [One-time GCP project setup](#3-one-time-gcp-project-setup)
4. [Production setup — Cloud Run + Service Account](#4-production-setup--cloud-run--service-account)
5. [Local setup — Option A (user ADC)](#5-local-setup--option-a-user-adc)
6. [Token lifetime FAQ](#6-token-lifetime-faq)
7. [FastAPI code — works identically in both environments](#7-fastapi-code--works-identically-in-both-environments)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Concepts in 60 seconds

| Term | Meaning |
|---|---|
| **ADC** (Application Default Credentials) | A search order the `google-auth` library uses to find credentials. You don't pass keys in code; the library finds them automatically. |
| **Access token** | Short-lived (1 hour) `Bearer` token sent on every API call. Always auto-refreshed by the client library. |
| **Refresh token / SA key / Metadata token** | The long-lived credential that *mints* access tokens. Source differs per environment. |
| **Service account (SA)** | A non-human Google identity. Cloud Run runs **as** an SA. |
| **Quota project** | The project billed for API usage (`X-Goog-User-Project` header). |

**ADC search order** (first match wins):

1. `GOOGLE_APPLICATION_CREDENTIALS` env var pointing to a key/config JSON
2. `gcloud auth application-default login` file (`%APPDATA%\gcloud\application_default_credentials.json` on Windows)
3. Attached service account on the GCP runtime (Cloud Run, GKE, GCE) via the metadata server

In **prod (Cloud Run)** → step 3 wins. On the **laptop** → step 2 wins. Code is identical.

---

## 2. Prerequisites

- A Google Cloud project with billing enabled. POC values used below:
  - `PROJECT_ID = project-e0b1cc14-0956-4be7-b03`
  - `LOCATION  = global`
  - `ENGINE_ID = gap-genai-discovery-search`
- `gcloud` CLI installed and on `PATH`. Verify:
  ```powershell
  gcloud --version
  ```
- Python 3.11+ with `pip`.
- An admin (or yourself with `roles/owner` / `roles/iam.admin`) for the IAM-binding steps in §3 and §4.

---

## 3. One-time GCP project setup

These steps are run **once per project** by an admin. Skip whatever is already done.

### 3.1 Set the active project

```powershell
gcloud config set project project-e0b1cc14-0956-4be7-b03
```

### 3.2 Enable required APIs

```powershell
gcloud services enable `
  discoveryengine.googleapis.com `
  iamcredentials.googleapis.com `
  run.googleapis.com `
  artifactregistry.googleapis.com `
  cloudbuild.googleapis.com `
  secretmanager.googleapis.com
```

`iamcredentials` is needed for impersonation; `run`, `artifactregistry`, `cloudbuild` for deployment; the rest are application-level.

### 3.3 Verify the Discovery Engine app exists

```powershell
gcloud alpha discovery-engine engines list `
  --location=global `
  --collection=default_collection
```

You should see `gap-genai-discovery-search`. If not, create it via the Vertex AI Search console (out of scope of this doc).

---

## 4. Production setup — Cloud Run + Service Account

### 4.1 Create the runtime service account

```powershell
gcloud iam service-accounts create gap-genai-backend-sa `
  --display-name="GAP GenAI Backend (Cloud Run runtime)" `
  --description="Identity used by the FastAPI backend on Cloud Run to call Discovery Engine"
```

Full email becomes:

```
gap-genai-backend-sa@project-e0b1cc14-0956-4be7-b03.iam.gserviceaccount.com
```

Tip: store it in a PowerShell variable for the rest of the session:

```powershell
$SA = "gap-genai-backend-sa@project-e0b1cc14-0956-4be7-b03.iam.gserviceaccount.com"
$PROJECT = "project-e0b1cc14-0956-4be7-b03"
```

### 4.2 Grant the SA the minimum roles it needs

| Role | Why | Scope |
|---|---|---|
| `roles/discoveryengine.editor` | Create sessions, call `:answer`, `:search`. Use `discoveryengine.viewer` for read-only backends. | Project |
| `roles/serviceusage.serviceUsageConsumer` | Required when the SA sets `X-Goog-User-Project` to a quota project. | Project |
| `roles/logging.logWriter` | Write structured logs from FastAPI. | Project |
| `roles/monitoring.metricWriter` | Emit custom metrics (optional). | Project |
| `roles/cloudtrace.agent` | Cloud Trace export (optional). | Project |

```powershell
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role="roles/discoveryengine.editor"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role="roles/serviceusage.serviceUsageConsumer"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role="roles/monitoring.metricWriter"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role="roles/cloudtrace.agent"
```

> **Do not** create or download a JSON key for this SA. Cloud Run mints tokens via the metadata server.

### 4.3 Build and push the container

Assuming a standard `Dockerfile` at the repo root:

```powershell
gcloud builds submit `
  --tag "us-central1-docker.pkg.dev/$PROJECT/backend/gap-genai-backend:latest"
```

(Adjust region and Artifact Registry repo to your environment.)

### 4.4 Deploy to Cloud Run with the SA attached

```powershell
gcloud run deploy gap-genai-backend `
  --image "us-central1-docker.pkg.dev/$PROJECT/backend/gap-genai-backend:latest" `
  --region us-central1 `
  --service-account $SA `
  --no-allow-unauthenticated `
  --set-env-vars "GCP_PROJECT_ID=$PROJECT,DE_LOCATION=global,DE_ENGINE_ID=gap-genai-discovery-search,DE_SERVING_CONFIG=default_search" `
  --memory 1Gi --cpu 1 --concurrency 40 --max-instances 10
```

Key flags:

- `--service-account $SA` — what makes ADC work without keys.
- `--no-allow-unauthenticated` — backend is private; the Web App invokes it via `roles/run.invoker`.

### 4.5 Allow the Web App service to invoke the backend (only if you have a separate frontend SA)

```powershell
$WEB_SA = "gap-genai-web-sa@$PROJECT.iam.gserviceaccount.com"

gcloud run services add-iam-policy-binding gap-genai-backend `
  --region us-central1 `
  --member="serviceAccount:$WEB_SA" `
  --role="roles/run.invoker"
```

### 4.6 Smoke test

```powershell
$URL   = (gcloud run services describe gap-genai-backend --region us-central1 --format="value(status.url)")
$TOKEN = gcloud auth print-identity-token

curl -H "Authorization: Bearer $TOKEN" "$URL/healthz"
```

---

## 5. Local setup — Option A (user ADC)

You authenticate as **yourself**, no service account, no JSON key. Run these on your laptop.

### 5.1 Log in

```powershell
gcloud auth login                                # browser opens, sign in with your @gap.com user
gcloud auth application-default login            # second browser flow — this is what FastAPI uses
gcloud config set project project-e0b1cc14-0956-4be7-b03
gcloud auth application-default set-quota-project project-e0b1cc14-0956-4be7-b03
```

The credential file is written to:

```
%APPDATA%\gcloud\application_default_credentials.json
```

### 5.2 Grant your user IAM (one-time, by an admin)

```powershell
$ME = "user:you@gap.com"

gcloud projects add-iam-policy-binding project-e0b1cc14-0956-4be7-b03 `
  --member=$ME --role="roles/discoveryengine.editor"

gcloud projects add-iam-policy-binding project-e0b1cc14-0956-4be7-b03 `
  --member=$ME --role="roles/serviceusage.serviceUsageConsumer"
```

### 5.3 Verify ADC works

```powershell
gcloud auth application-default print-access-token
```

You should see a long opaque string. If not, re-run §5.1.

### 5.4 Run FastAPI locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn google-auth google-auth-httplib2 requests pydantic

$env:GCP_PROJECT_ID="project-e0b1cc14-0956-4be7-b03"
$env:DE_LOCATION="global"
$env:DE_ENGINE_ID="gap-genai-discovery-search"
$env:DE_SERVING_CONFIG="default_search"

uvicorn app.main:app --reload --port 8080
```

### 5.5 What you do **not** need

- ❌ A service account
- ❌ A JSON key file
- ❌ `GOOGLE_APPLICATION_CREDENTIALS` env var
- ❌ Manual token refresh logic

---

## 6. Token lifetime FAQ

| Question | Answer |
|---|---|
| How long does the access token last? | 1 hour. Auto-refreshed by `google-auth`; you never see it. |
| How often do I run `gcloud auth application-default login`? | **Once.** Refresh token persists for months. |
| When would I need to re-login? | After `... revoke`, after 6 months idle, after org-policy forced re-auth, after Google account password/MFA reset, after wiping the laptop. |
| On Cloud Run, is anything stored on disk? | No. Tokens come from the metadata server in-memory. |
| Can I extend tokens to a year like AWS access keys? | No. GCP access tokens are 1h max (12h via impersonation with org policy). The *refresh* mechanism is what makes it transparent. |

---

## 7. FastAPI code — works identically in both environments

The same code works on Cloud Run (uses metadata server) and on your laptop (uses user ADC). Only the credential **source** changes; `google.auth.default()` abstracts it.

### 7.1 Project layout

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # env-driven settings
│   ├── deps.py              # AuthorizedSession dependency
│   └── discovery_client.py  # thin wrapper over Discovery Engine REST
├── Dockerfile
└── requirements.txt
```

### 7.2 `requirements.txt`

```text
fastapi==0.115.*
uvicorn[standard]==0.30.*
gunicorn==22.*
google-auth==2.*
requests==2.32.*
pydantic==2.*
pydantic-settings==2.*
```

### 7.3 `app/config.py` — env-driven settings

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gcp_project_id: str
    de_location: str = "global"
    de_collection: str = "default_collection"
    de_engine_id: str = "gap-genai-discovery-search"
    de_serving_config: str = "default_search"
    de_host: str = "https://discoveryengine.googleapis.com"
    de_api_version: str = "v1"

    @property
    def base_url(self) -> str:
        return (
            f"{self.de_host}/{self.de_api_version}"
            f"/projects/{self.gcp_project_id}"
            f"/locations/{self.de_location}"
            f"/collections/{self.de_collection}"
            f"/engines/{self.de_engine_id}"
        )

    def session_path(self, session_id: str) -> str:
        return (
            f"projects/{self.gcp_project_id}"
            f"/locations/{self.de_location}"
            f"/collections/{self.de_collection}"
            f"/engines/{self.de_engine_id}"
            f"/sessions/{session_id}"
        )


settings = Settings()
```

### 7.4 `app/deps.py` — one `AuthorizedSession`, auto-refreshing

```python
from functools import lru_cache

from google.auth import default
from google.auth.transport.requests import AuthorizedSession

from .config import settings

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


@lru_cache(maxsize=1)
def get_session() -> AuthorizedSession:
    """
    Returns a process-wide AuthorizedSession.

    - On Cloud Run: credentials come from the attached service account
      via the metadata server.
    - On a laptop: credentials come from
      `gcloud auth application-default login`.

    The same object is reused; google-auth refreshes the 1h access token
    in the background.
    """
    creds, _ = default(scopes=SCOPES)
    session = AuthorizedSession(creds)
    session.headers.update({"X-Goog-User-Project": settings.gcp_project_id})
    return session
```

### 7.5 `app/discovery_client.py` — thin REST wrapper

```python
from typing import Any

from fastapi import HTTPException

from .config import settings
from .deps import get_session


def _raise_for_status(resp) -> dict[str, Any]:
    if not resp.ok:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json() if resp.content else {}


# ---------- Sessions ----------

def list_sessions(page_size: int = 50, page_token: str | None = None,
                  user_pseudo_id: str | None = None,
                  order_by: str = "update_time desc") -> dict[str, Any]:
    params: dict[str, Any] = {"pageSize": page_size, "orderBy": order_by}
    if page_token:
        params["pageToken"] = page_token
    if user_pseudo_id:
        params["filter"] = f'userPseudoId="{user_pseudo_id}"'
    resp = get_session().get(f"{settings.base_url}/sessions", params=params)
    return _raise_for_status(resp)


def create_session(user_pseudo_id: str, display_name: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"userPseudoId": user_pseudo_id}
    if display_name:
        body["displayName"] = display_name
    resp = get_session().post(f"{settings.base_url}/sessions", json=body)
    return _raise_for_status(resp)


def get_session_detail(session_id: str, include_answers: bool = True) -> dict[str, Any]:
    params = {"includeAnswerDetails": "true"} if include_answers else {}
    resp = get_session().get(
        f"{settings.base_url}/sessions/{session_id}", params=params
    )
    return _raise_for_status(resp)


def patch_session(session_id: str, update_mask: str, body: dict[str, Any]) -> dict[str, Any]:
    resp = get_session().patch(
        f"{settings.base_url}/sessions/{session_id}",
        params={"updateMask": update_mask},
        json=body,
    )
    return _raise_for_status(resp)


def delete_session(session_id: str) -> dict[str, Any]:
    resp = get_session().delete(f"{settings.base_url}/sessions/{session_id}")
    return _raise_for_status(resp)


# ---------- Answer / Search ----------

def answer(question: str, session_id: str | None = None,
           include_citations: bool = True,
           model_version: str = "gemini-2.0-flash-001/answer_gen/v1") -> dict[str, Any]:
    body: dict[str, Any] = {
        "query": {"text": question},
        "answerGenerationSpec": {
            "ignoreAdversarialQuery": True,
            "includeCitations": include_citations,
            "modelSpec": {"modelVersion": model_version},
        },
    }
    if session_id:
        body["session"] = settings.session_path(session_id)

    resp = get_session().post(
        f"{settings.base_url}/servingConfigs/{settings.de_serving_config}:answer",
        json=body,
    )
    return _raise_for_status(resp)


def search(query: str, session_id: str | None = None, page_size: int = 10) -> dict[str, Any]:
    body: dict[str, Any] = {"query": query, "pageSize": page_size}
    if session_id:
        body["session"] = settings.session_path(session_id)
    resp = get_session().post(
        f"{settings.base_url}/servingConfigs/{settings.de_serving_config}:search",
        json=body,
    )
    return _raise_for_status(resp)


def stream_answer(question: str, session_id: str | None = None):
    """Yields raw SSE byte chunks from the streamAnswer endpoint."""
    body: dict[str, Any] = {
        "query": {"text": question},
        "answerGenerationSpec": {"includeCitations": True},
    }
    if session_id:
        body["session"] = settings.session_path(session_id)

    with get_session().post(
        f"{settings.base_url}/servingConfigs/{settings.de_serving_config}:streamAnswer",
        json=body,
        stream=True,
    ) as resp:
        if not resp.ok:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        for chunk in resp.iter_content(chunk_size=None):
            if chunk:
                yield chunk
```

### 7.6 `app/main.py` — FastAPI routes

```python
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import discovery_client as dc

app = FastAPI(title="GAP GenAI Backend")


# ---------- Models ----------

class CreateSessionIn(BaseModel):
    user_pseudo_id: str
    display_name: str | None = None


class AskIn(BaseModel):
    question: str
    session_id: str | None = None
    include_citations: bool = True


class SearchIn(BaseModel):
    query: str
    session_id: str | None = None
    page_size: int = 10


class PatchSessionIn(BaseModel):
    state: str | None = None          # "IN_PROGRESS" | "COMPLETED"
    display_name: str | None = None
    is_pinned: bool | None = None


# ---------- Health ----------

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


# ---------- Sessions ----------

@app.get("/sessions")
def list_sessions(
    page_size: int = 50,
    page_token: str | None = None,
    user_pseudo_id: str | None = None,
):
    return dc.list_sessions(page_size, page_token, user_pseudo_id)


@app.post("/sessions", status_code=201)
def create_session(body: CreateSessionIn):
    return dc.create_session(body.user_pseudo_id, body.display_name)


@app.get("/sessions/{session_id}")
def get_session(session_id: str, include_answers: bool = Query(True)):
    return dc.get_session_detail(session_id, include_answers)


@app.patch("/sessions/{session_id}")
def patch_session(session_id: str, body: PatchSessionIn):
    update = body.model_dump(exclude_none=True)
    if not update:
        return {"updated": False}
    # Translate snake_case to the camelCase fields Discovery Engine expects.
    payload: dict = {}
    mask: list[str] = []
    if "state" in update:
        payload["state"] = update["state"]; mask.append("state")
    if "display_name" in update:
        payload["displayName"] = update["display_name"]; mask.append("displayName")
    if "is_pinned" in update:
        payload["isPinned"] = update["is_pinned"]; mask.append("isPinned")
    return dc.patch_session(session_id, ",".join(mask), payload)


@app.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    dc.delete_session(session_id)


# ---------- Q&A ----------

@app.post("/ask")
def ask(body: AskIn):
    return dc.answer(body.question, body.session_id, body.include_citations)


@app.post("/ask/stream")
def ask_stream(body: AskIn):
    return StreamingResponse(
        dc.stream_answer(body.question, body.session_id),
        media_type="text/event-stream",
    )


@app.post("/search")
def search(body: SearchIn):
    return dc.search(body.query, body.session_id, body.page_size)
```

### 7.7 `Dockerfile`

```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Cloud Run injects PORT; default to 8080 for local
ENV PORT=8080
CMD exec gunicorn -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:${PORT} -w 2 --timeout 60 app.main:app
```

### 7.8 Try it locally

```powershell
# 1. Create a session
$body = @{ user_pseudo_id = "3B766523-069F-4E19-8A55-710D6A1608BF" } | ConvertTo-Json
$s = Invoke-RestMethod -Uri http://localhost:8080/sessions -Method POST -ContentType application/json -Body $body
$sid = ($s.name -split "/")[-1]

# 2. Ask a question
$ask = @{ question = "What experiments ran in Q1 2026?"; session_id = $sid } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8080/ask -Method POST -ContentType application/json -Body $ask

# 3. Inspect the session
Invoke-RestMethod -Uri "http://localhost:8080/sessions/$sid"
```

---

## 8. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `google.auth.exceptions.DefaultCredentialsError` locally | ADC not configured | `gcloud auth application-default login` |
| `403 IAM_PERMISSION_DENIED` calling `:answer` | User/SA missing `discoveryengine.editor` | Grant the role (§4.2 or §5.2) |
| `403 SERVICE_DISABLED` | Discovery Engine API not enabled | `gcloud services enable discoveryengine.googleapis.com` |
| `403 ... user is not allowed to set the consumer project` | Missing `serviceUsageConsumer` | Grant `roles/serviceusage.serviceUsageConsumer` |
| Cloud Run returns 500 but logs show `DefaultCredentialsError` | Forgot `--service-account` flag on deploy | Redeploy with `--service-account $SA` |
| Local works, Cloud Run 403s the same call | Your user has roles your SA doesn't | Mirror the IAM bindings on the SA |
| Token expires mid-request | Almost never happens; if it does, the library retries automatically. If you're using raw `requests` instead of `AuthorizedSession`, switch to `AuthorizedSession`. |
| `PERMISSION_DENIED` on `:streamAnswer` only | Engine SKU may not include streaming | Use `:answer` non-streaming |
