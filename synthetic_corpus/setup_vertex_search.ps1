# =====================================================================
# Create Vertex AI Search (Discovery Engine) data store + search app
# for the GAP GenAI Discovery POC.
#
# PREREQ (run these once, in PowerShell, before this script):
#   1. Sign out of Walmart account:
#        gcloud auth revoke --all
#   2. Sign in with your PERSONAL Google account (the one that owns
#      "My First Project"):
#        gcloud auth login
#   3. Confirm the active account:
#        gcloud auth list
#
# If you're on the Walmart corporate network, VPC Service Controls will
# block this. Run from a personal network (home / hotspot / phone tether).
#
# Usage:
#   .\setup_vertex_search.ps1
# =====================================================================

# ----- EDIT THESE TWO IF NEEDED --------------------------------------
# The project ID shown in the console was truncated. Easiest: open
# https://console.cloud.google.com/welcome and copy the FULL ID.
# Project NUMBER is reliable (from your screenshot).
$PROJECT_ID     = ""                                     # <-- PASTE FULL ID HERE
$PROJECT_NUMBER = "10982993176"
$BUCKET         = "test123hkjjghj4123456"                # existing bucket
$LOCATION       = "global"                               # data store location
$DATA_STORE_ID  = "gap-genai-discovery-corpus"
$ENGINE_ID      = "gap-genai-discovery-search"
# ---------------------------------------------------------------------

$ErrorActionPreference = "Stop"

if (-not $PROJECT_ID) {
    $PROJECT_ID = (gcloud projects list --filter="projectNumber=$PROJECT_NUMBER" --format="value(projectId)") | Select-Object -First 1
    if (-not $PROJECT_ID) {
        Write-Error "Could not resolve project ID from number $PROJECT_NUMBER. Edit `$PROJECT_ID at the top of this script."
        exit 1
    }
    Write-Host "Resolved PROJECT_ID = $PROJECT_ID"
}

gcloud config set project $PROJECT_ID | Out-Null

# ----- 1. Enable APIs -------------------------------------------------
Write-Host "`n[1/6] Enabling APIs..."
gcloud services enable `
    discoveryengine.googleapis.com `
    storage.googleapis.com `
    aiplatform.googleapis.com

# ----- 2. Make sure HTML corpus + metadata.jsonl are uploaded ---------
Write-Host "`n[2/6] Uploading HTML corpus + metadata.jsonl to gs://$BUCKET ..."
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$pagesDir   = Join-Path $here "pages"
$manifest   = Join-Path $here "metadata.jsonl"

# Rewrite metadata.jsonl so content.uri points at THIS bucket
Write-Host "  - rewriting metadata.jsonl content.uri -> gs://$BUCKET/pages/..."
$gcsPrefix = "gs://$BUCKET/pages"
$updated = Get-Content $manifest -Raw -Encoding UTF8
$updated = [regex]::Replace($updated, 'gs://[^/"]+/pages', $gcsPrefix)
[System.IO.File]::WriteAllText($manifest, $updated, [System.Text.UTF8Encoding]::new($false))

gsutil -m -q cp -r "$pagesDir" "gs://$BUCKET/"
gsutil -q cp "$manifest" "gs://$BUCKET/metadata.jsonl"

# ----- 3. Get an OAuth access token -----------------------------------
$TOKEN = gcloud auth print-access-token
$AUTH  = @{ Authorization = "Bearer $TOKEN"; "Content-Type" = "application/json" }

# ----- 4. Create the Data Store --------------------------------------
Write-Host "`n[3/6] Creating data store '$DATA_STORE_ID' (location=$LOCATION)..."
$dsBody = @{
    displayName        = "GAP T&L COE Corpus"
    industryVertical   = "GENERIC"
    solutionTypes      = @("SOLUTION_TYPE_SEARCH")
    contentConfig      = "CONTENT_REQUIRED"
} | ConvertTo-Json -Depth 5

$dsUrl = "https://discoveryengine.googleapis.com/v1/projects/$PROJECT_ID/locations/$LOCATION/collections/default_collection/dataStores?dataStoreId=$DATA_STORE_ID"
try {
    Invoke-RestMethod -Method POST -Uri $dsUrl -Headers $AUTH -Body $dsBody | Out-Null
    Write-Host "  data store created."
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 409) {
        Write-Host "  data store already exists, continuing."
    } else { throw }
}

# Wait for the data store to be ready
Start-Sleep -Seconds 10

# ----- 5. Import HTML documents with metadata -------------------------
Write-Host "`n[4/6] Importing documents from gs://$BUCKET/metadata.jsonl ..."
$importBody = @{
    gcsSource = @{
        inputUris  = @("gs://$BUCKET/metadata.jsonl")
        dataSchema = "document"
    }
    reconciliationMode = "INCREMENTAL"
} | ConvertTo-Json -Depth 5

$importUrl = "https://discoveryengine.googleapis.com/v1/projects/$PROJECT_ID/locations/$LOCATION/collections/default_collection/dataStores/$DATA_STORE_ID/branches/default_branch/documents:import"
$op = Invoke-RestMethod -Method POST -Uri $importUrl -Headers $AUTH -Body $importBody
$opName = $op.name
Write-Host "  import operation: $opName"

# Poll until done
Write-Host "  polling import (this typically takes 5-15 min for 500 docs)..."
$opUrl = "https://discoveryengine.googleapis.com/v1/$opName"
while ($true) {
    Start-Sleep -Seconds 20
    $status = Invoke-RestMethod -Method GET -Uri $opUrl -Headers $AUTH
    if ($status.done) {
        if ($status.error) {
            Write-Error "Import failed: $($status.error | ConvertTo-Json -Depth 10)"
            exit 1
        }
        Write-Host "  import complete: success=$($status.response.successCount) failure=$($status.response.failureCount)"
        break
    }
    Write-Host -NoNewline "."
}

# ----- 6. Create the Search engine (app) ------------------------------
Write-Host "`n[5/6] Creating search engine '$ENGINE_ID'..."
$engineBody = @{
    displayName        = "GAP GenAI Discovery Search"
    solutionType       = "SOLUTION_TYPE_SEARCH"
    industryVertical   = "GENERIC"
    dataStoreIds       = @($DATA_STORE_ID)
    searchEngineConfig = @{
        searchTier    = "SEARCH_TIER_ENTERPRISE"
        searchAddOns  = @("SEARCH_ADD_ON_LLM")
    }
} | ConvertTo-Json -Depth 5

$engineUrl = "https://discoveryengine.googleapis.com/v1/projects/$PROJECT_ID/locations/$LOCATION/collections/default_collection/engines?engineId=$ENGINE_ID"
try {
    Invoke-RestMethod -Method POST -Uri $engineUrl -Headers $AUTH -Body $engineBody | Out-Null
    Write-Host "  engine created."
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 409) {
        Write-Host "  engine already exists, continuing."
    } else { throw }
}

# ----- 7. Smoke test --------------------------------------------------
Write-Host "`n[6/6] Smoke-test query..."
Start-Sleep -Seconds 15
$serving = "projects/$PROJECT_ID/locations/$LOCATION/collections/default_collection/engines/$ENGINE_ID/servingConfigs/default_search"
$queryBody = @{
    query    = "sticky add to bag PDP test results"
    pageSize = 3
} | ConvertTo-Json
$queryUrl = "https://discoveryengine.googleapis.com/v1/" + $serving + ":search"
$resp = Invoke-RestMethod -Method POST -Uri $queryUrl -Headers $AUTH -Body $queryBody
Write-Host "`nTop hits:"
$resp.results | ForEach-Object {
    $title = $_.document.structData.title
    "  - $($_.document.id)  $title"
}

Write-Host @"

============================================================
DONE.

Console links:
  Data store : https://console.cloud.google.com/gen-app-builder/data-stores/$DATA_STORE_ID/documents?project=$PROJECT_ID
  Search app : https://console.cloud.google.com/gen-app-builder/engines/$ENGINE_ID/preview?project=$PROJECT_ID

Use these IDs in the agent code (skill S3 retrieve_passages):
  PROJECT_ID    = $PROJECT_ID
  LOCATION      = $LOCATION
  DATA_STORE_ID = $DATA_STORE_ID
  ENGINE_ID     = $ENGINE_ID
============================================================
"@
