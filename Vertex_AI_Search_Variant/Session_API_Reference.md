# Vertex AI Search — Session REST API Reference

> **Tested:** 2026-06-01. All endpoints below return 200 OK against the POC project.

## Connection details

| Parameter | Placeholder | Current POC value |
|-----------|-------------|-------------------|
| Service host | `{HOST}` | `https://discoveryengine.googleapis.com` |
| API version | `{API_VERSION}` | `v1` |
| Project ID | `{PROJECT_ID}` | `project-e0b1cc14-0956-4be7-b03` |
| Project number | `{PROJECT_NUMBER}` | `10982993176` |
| Location | `{LOCATION}` | `global` |
| Collection | `{COLLECTION}` | `default_collection` |
| Engine (App) ID | `{ENGINE_ID}` | `gap-genai-discovery-search` |
| Data Store ID | `{DATA_STORE_ID}` | `gap-genai-discovery-corpus` |
| Serving Config ID | `{SERVING_CONFIG}` | `default_search` |

## Base URL

```
{HOST}/{API_VERSION}/projects/{PROJECT_ID}/locations/{LOCATION}/collections/{COLLECTION}/engines/{ENGINE_ID}
```

**Current POC value:**

```
https://discoveryengine.googleapis.com/v1/projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/engines/gap-genai-discovery-search
```

## Authentication

All requests require:

```
Authorization: Bearer <ACCESS_TOKEN>
X-Goog-User-Project: {PROJECT_ID}
```

Get a token via:

```powershell
$token = gcloud auth print-access-token
```

Required IAM role: `roles/discoveryengine.editor` (or `roles/discoveryengine.viewer` for read-only).

---

## Session endpoints

### List sessions

```
GET {BASE}/sessions?pageSize={PAGE_SIZE}&pageToken={PAGE_TOKEN}&filter={FILTER}&orderBy={ORDER_BY}
```

| Query param | Description | Example |
|-------------|-------------|---------|
| `pageSize` | Max results per page (default 50) | `10` |
| `pageToken` | Token from previous response `nextPageToken` | — |
| `filter` | Filter by `userPseudoId` and/or `state` | `userPseudoId="3B766523-069F-4E19-8A55-710D6A1608BF"` |
| `orderBy` | Sort order | `update_time desc` |

**Example (list latest 5):**

```
GET https://discoveryengine.googleapis.com/v1/projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/engines/gap-genai-discovery-search/sessions?pageSize=5
```

---

### Create session

```
POST {BASE}/sessions
Content-Type: application/json

{
  "userPseudoId": "{USER_PSEUDO_ID}",
  "displayName": "optional display name"
}
```

**Example:**

```
POST https://discoveryengine.googleapis.com/v1/projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/engines/gap-genai-discovery-search/sessions

{
  "userPseudoId": "3B766523-069F-4E19-8A55-710D6A1608BF"
}
```

---

### Get session (with full answer details)

```
GET {BASE}/sessions/{SESSION_ID}?includeAnswerDetails=true
```

> Set `includeAnswerDetails=true` to inline the full `Answer` object (text, citations, references) for each turn.

**Example:**

```
GET https://discoveryengine.googleapis.com/v1/projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/engines/gap-genai-discovery-search/sessions/10702571533343575662?includeAnswerDetails=true
```

---

### Patch (update) session

```
PATCH {BASE}/sessions/{SESSION_ID}?updateMask={FIELDS}
Content-Type: application/json

{
  "state": "COMPLETED",
  "isPinned": true
}
```

| `updateMask` values | Description |
|---------------------|-------------|
| `state` | `IN_PROGRESS` or `COMPLETED` |
| `displayName` | Change display name |
| `isPinned` | Pin session to top of list |
| `labels` | Filter labels |
| `userPseudoId` | Reassign to a different user |

**Example (mark completed):**

```
PATCH https://discoveryengine.googleapis.com/v1/projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/engines/gap-genai-discovery-search/sessions/10702571533343575662?updateMask=state

{ "state": "COMPLETED" }
```

---

### Delete session

```
DELETE {BASE}/sessions/{SESSION_ID}
```

**Example:**

```
DELETE https://discoveryengine.googleapis.com/v1/projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/engines/gap-genai-discovery-search/sessions/10702571533343575662
```

---

## Answer / query endpoints (append turns to a session)

### Answer (non-streaming)

```
POST {BASE}/servingConfigs/{SERVING_CONFIG}:answer
Content-Type: application/json

{
  "query": { "text": "{USER_QUESTION}" },
  "session": "projects/{PROJECT_ID}/locations/{LOCATION}/collections/{COLLECTION}/engines/{ENGINE_ID}/sessions/{SESSION_ID}",
  "answerGenerationSpec": {
    "ignoreAdversarialQuery": true,
    "ignoreNonSummarySeekingQuery": false,
    "includeCitations": true,
    "modelSpec": { "modelVersion": "gemini-2.0-flash-001/answer_gen/v1" }
  }
}
```

**Example:**

```
POST https://discoveryengine.googleapis.com/v1/projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/engines/gap-genai-discovery-search/servingConfigs/default_search:answer

{
  "query": { "text": "What experiments ran in Q1 2026?" },
  "session": "projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/engines/gap-genai-discovery-search/sessions/10702571533343575662",
  "answerGenerationSpec": {
    "includeCitations": true
  }
}
```

---

### Stream answer (Server-Sent Events)

```
POST {BASE}/servingConfigs/{SERVING_CONFIG}:streamAnswer
Content-Type: application/json

(same body as :answer)
```

Returns `text/event-stream` with incremental answer chunks.

---

### Search (with session context)

```
POST {BASE}/servingConfigs/{SERVING_CONFIG}:search
Content-Type: application/json

{
  "query": "{USER_QUESTION}",
  "session": "projects/{PROJECT_ID}/locations/{LOCATION}/collections/{COLLECTION}/engines/{ENGINE_ID}/sessions/{SESSION_ID}",
  "pageSize": 10
}
```

---

## Get individual answer

```
GET {BASE}/sessions/{SESSION_ID}/answers/{ANSWER_ID}
```

> **Note:** As of 2026-06-01 this endpoint returns 500 intermittently on our engine. Use `GET session?includeAnswerDetails=true` instead to retrieve all answers in a session reliably.

**Example:**

```
GET https://discoveryengine.googleapis.com/v1/projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/engines/gap-genai-discovery-search/sessions/10702571533343575662/answers/13331619203862617550
```

---

## Data Store scoped variant

If you need data-store-scoped sessions (no engine/app), replace:

```
engines/{ENGINE_ID}  →  dataStores/{DATA_STORE_ID}
```

**Example base:**

```
https://discoveryengine.googleapis.com/v1/projects/project-e0b1cc14-0956-4be7-b03/locations/global/collections/default_collection/dataStores/gap-genai-discovery-corpus
```

All session endpoints (`/sessions`, `/sessions/{ID}`, etc.) work identically.

---

## Quick-start (PowerShell)

```powershell
$token = gcloud auth print-access-token
$proj  = "project-e0b1cc14-0956-4be7-b03"
$H     = @{ Authorization = "Bearer $token"; "X-Goog-User-Project" = $proj }
$base  = "https://discoveryengine.googleapis.com/v1/projects/$proj/locations/global/collections/default_collection/engines/gap-genai-discovery-search"

# List sessions
Invoke-RestMethod -Uri "$base/sessions?pageSize=5" -Headers $H

# Get session with answers
Invoke-RestMethod -Uri "$base/sessions/10702571533343575662?includeAnswerDetails=true" -Headers $H

# Ask a question (append to existing session)
$body = @{
  query = @{ text = "What experiments ran in Q1 2026?" }
  session = "projects/$proj/locations/global/collections/default_collection/engines/gap-genai-discovery-search/sessions/10702571533343575662"
  answerGenerationSpec = @{ includeCitations = $true }
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "$base/servingConfigs/default_search:answer" -Headers $H -Method POST -ContentType 'application/json' -Body $body
```

---

## Reference links

- [Engine sessions REST](https://cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1/projects.locations.collections.engines.sessions)
- [DataStore sessions REST](https://cloud.google.com/generative-ai-app-builder/docs/reference/rest/v1/projects.locations.collections.dataStores.sessions)
- [Answer method guide](https://cloud.google.com/generative-ai-app-builder/docs/answer)
- [Multi-turn search guide](https://cloud.google.com/generative-ai-app-builder/docs/multi-turn-search)
- [Discovery doc](https://discoveryengine.googleapis.com/$discovery/rest?version=v1)
