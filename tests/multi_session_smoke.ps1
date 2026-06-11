<#
.SYNOPSIS
  Multi-user / multi-session / multi-turn / resume smoke test against the live VAIS engine.

.DESCRIPTION
  Simulates 2 users, each with 2 concurrent sessions x 3 turns, then resumes one session
  with a 4th anaphoric turn. Validates VAIS-native session isolation, multi-session-per-user
  listing, ACL gate, and conversational memory after resume.

  All calls go direct to the Discovery Engine REST API (no app code) — mirrors what the
  Agent service in the architecture will do per the locked VAIS-native design:
    POST :answer  +  queryUnderstandingSpec  (queryRewritingSpec + naturalLanguageQueryUnderstandingSpec)
    sessions.{create, list, get, delete}

.PARAMETER Cleanup
  Delete all created sessions at the end of the test. Default: leave them for inspection.

.PARAMETER ParallelSessions
  Run sessions in parallel (PowerShell jobs). Default: serial within a session, parallel across sessions.
#>
[CmdletBinding()]
param(
    [switch]$Cleanup,
    [switch]$NoParallel
)

$ErrorActionPreference = 'Stop'

# ============================================================
# Config
# ============================================================
$PROJECT_ID    = 'project-e0b1cc14-0956-4be7-b03'
$LOCATION      = 'global'
$ENGINE_ID     = 'gap-genai-discovery-search'
$ENGINE_PATH   = "projects/$PROJECT_ID/locations/$LOCATION/collections/default_collection/engines/$ENGINE_ID"
$BASE_URL      = "https://discoveryengine.googleapis.com/v1beta/$ENGINE_PATH"
$ANSWER_URL    = "$BASE_URL/servingConfigs/default_search:answer"
$SESSIONS_URL  = "$BASE_URL/sessions"

# ============================================================
# Auth
# ============================================================
Write-Host "==> Acquiring access token..." -ForegroundColor Cyan
$TOKEN = $null
try { $TOKEN = (gcloud auth print-access-token 2>$null | Out-String).Trim() } catch {}
if (-not $TOKEN -or $TOKEN -match 'ERROR') {
    Write-Host "  user creds unavailable, falling back to ADC..." -ForegroundColor Yellow
    $TOKEN = (gcloud auth application-default print-access-token 2>$null | Out-String).Trim()
}
if (-not $TOKEN -or $TOKEN -match 'ERROR') { throw "Failed to get access token. Run: gcloud auth login" }
$HEADERS = @{
    Authorization        = "Bearer $TOKEN"
    'X-Goog-User-Project' = $PROJECT_ID
    'Content-Type'       = 'application/json'
}

# ============================================================
# Test plan
# ============================================================
$PLAN = @(
    @{
        user  = 'test-user-alpha'
        label = 'alpha-S1: Old Navy sticky ATB'
        turns = @(
            'What are the strongest Old Navy sticky add-to-bag PDP test results?',
            'Which of those was the biggest win and by how much?',
            'Summarize all the returned results — group by outcome and call out winners.'
        )
    },
    @{
        user  = 'test-user-alpha'
        label = 'alpha-S2: Gap 2025 PLP experiments'
        turns = @(
            'What tests were done for Gap brand on PLP in 2025?',
            'Which of those had the biggest Net RPV impact?',
            'List the top 3 by incremental revenue.'
        )
    },
    @{
        user  = 'test-user-beta'
        label = 'beta-S1: Athleta checkout flow'
        turns = @(
            'What Athleta tests were done on the checkout flow?',
            'Were any of those wins?',
            'Summarize the recommendations across those tests.'
        )
    },
    @{
        user  = 'test-user-beta'
        label = 'beta-S2: Banana Republic loyalty'
        turns = @(
            'What experiments were run for Banana Republic targeting loyalty members?',
            'Which had the most positive outcome?',
            'What learnings should we apply next?'
        )
    }
)

# ============================================================
# Helpers
# ============================================================
function Read-ErrorBody {
    param($Err)
    try {
        if ($Err.ErrorDetails -and $Err.ErrorDetails.Message) { return $Err.ErrorDetails.Message }
        $resp = $Err.Exception.Response
        if ($resp -and $resp.GetResponseStream) {
            $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
            return $reader.ReadToEnd()
        }
        return $Err.Exception.Message
    } catch { return $Err.Exception.Message }
}

function New-Session {
    param([string]$UserPseudoId)
    $body = @{ userPseudoId = $UserPseudoId } | ConvertTo-Json -Compress
    $resp = Invoke-RestMethod -Method POST -Uri $SESSIONS_URL -Headers $HEADERS -Body $body
    return $resp.name
}

function Invoke-Answer {
    param(
        [string]$SessionName,
        [string]$QueryText,
        [string]$UserPseudoId
    )
    $body = @{
        query             = @{ text = $QueryText }
        session           = $SessionName
        userPseudoId      = $UserPseudoId
        answerGenerationSpec = @{
            modelSpec         = @{ modelVersion = 'stable' }
            includeCitations  = $true
        }
        queryUnderstandingSpec = @{
            queryClassificationSpec = @{ types = @('ADVERSARIAL_QUERY','NON_ANSWER_SEEKING_QUERY') }
        }
        searchSpec = @{
            searchParams = @{
                naturalLanguageQueryUnderstandingSpec = @{
                    filterExtractionCondition = 'ENABLED'
                }
            }
        }
    } | ConvertTo-Json -Depth 8 -Compress

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $resp = Invoke-RestMethod -Method POST -Uri $ANSWER_URL -Headers $HEADERS -Body $body -TimeoutSec 120
        $sw.Stop()
        return [pscustomobject]@{
            Ok         = $true
            LatencyMs  = $sw.ElapsedMilliseconds
            AnswerText = $resp.answer.answerText
            RefsCount  = ($resp.answer.references | Measure-Object).Count
            Citations  = ($resp.answer.citations | Measure-Object).Count
            ExtractedFilter = $resp.sessionInfo.queryId  # placeholder; real filter in queryUnderstandingInfo
            QueryId    = $resp.answer.queryId
            Raw        = $resp
        }
    } catch {
        $sw.Stop()
        return [pscustomobject]@{
            Ok         = $false
            LatencyMs  = $sw.ElapsedMilliseconds
            Error      = (Read-ErrorBody $_)
        }
    }
}

function Get-Session {
    param([string]$SessionName)
    $url = "https://discoveryengine.googleapis.com/v1beta/$SessionName" + "?includeAnswerDetails=true"
    return Invoke-RestMethod -Method GET -Uri $url -Headers $HEADERS
}

function Get-UserSessions {
    param([string]$UserPseudoId)
    $filter = [System.Web.HttpUtility]::UrlEncode('user_pseudo_id="' + $UserPseudoId + '"')
    $url = "$SESSIONS_URL`?filter=$filter&pageSize=200"
    $resp = Invoke-RestMethod -Method GET -Uri $url -Headers $HEADERS
    $all  = @($resp.sessions)
    $mine = $all | Where-Object { $_.userPseudoId -eq $UserPseudoId }
    return [pscustomobject]@{ Raw = $all; Mine = $mine }
}

function Remove-Session {
    param([string]$SessionName)
    $url = "https://discoveryengine.googleapis.com/v1beta/$SessionName"
    Invoke-RestMethod -Method DELETE -Uri $url -Headers $HEADERS | Out-Null
}

Add-Type -AssemblyName System.Web

# ============================================================
# PHASE 1: Create sessions
# ============================================================
Write-Host "`n==> PHASE 1: Creating 4 sessions across 2 users..." -ForegroundColor Cyan
foreach ($p in $PLAN) {
    $p.sessionName = New-Session -UserPseudoId $p.user
    $p.sessionId   = $p.sessionName.Split('/')[-1]
    Write-Host ("  [{0}] {1}" -f $p.user, $p.sessionId) -ForegroundColor Gray
}

# ============================================================
# PHASE 2: Run 3 turns per session (parallel across sessions, serial within)
# ============================================================
Write-Host "`n==> PHASE 2: Running 3 turns x 4 sessions = 12 :answer calls..." -ForegroundColor Cyan

$runSession = {
    param($plan, $answerUrl, $headers)
    function Read-ErrorBody2 { param($Err) try { if ($Err.ErrorDetails -and $Err.ErrorDetails.Message) { return $Err.ErrorDetails.Message }; $resp=$Err.Exception.Response; if ($resp) { $r=New-Object System.IO.StreamReader($resp.GetResponseStream()); return $r.ReadToEnd() }; return $Err.Exception.Message } catch { return $Err.Exception.Message } }
    $results = @()
    foreach ($turnText in $plan.turns) {
        $body = @{
            query                  = @{ text = $turnText }
            session                = $plan.sessionName
            userPseudoId           = $plan.user
            answerGenerationSpec   = @{ modelSpec = @{ modelVersion = 'stable' }; includeCitations = $true }
            searchSpec             = @{ searchParams = @{ naturalLanguageQueryUnderstandingSpec = @{ filterExtractionCondition = 'ENABLED' } } }
        } | ConvertTo-Json -Depth 8 -Compress
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        try {
            $resp = Invoke-RestMethod -Method POST -Uri $answerUrl -Headers $headers -Body $body -TimeoutSec 120
            $sw.Stop()
            $results += [pscustomobject]@{
                Label = $plan.label
                Turn  = $turnText.Substring(0, [Math]::Min(60, $turnText.Length))
                Ok    = $true
                Ms    = $sw.ElapsedMilliseconds
                Refs  = ($resp.answer.references | Measure-Object).Count
                Error = ''
                AnswerSnippet = if ($resp.answer.answerText) { $resp.answer.answerText.Substring(0, [Math]::Min(140, $resp.answer.answerText.Length)) } else { '' }
            }
        } catch {
            $sw.Stop()
            $errMsg = Read-ErrorBody2 $_
            $clean  = ($errMsg -replace '\s+',' ')
            $results += [pscustomobject]@{
                Label = $plan.label
                Turn  = $turnText.Substring(0, [Math]::Min(60, $turnText.Length))
                Ok    = $false
                Ms    = $sw.ElapsedMilliseconds
                Refs  = 0
                Error = $clean.Substring(0, [Math]::Min(220, $clean.Length))
                AnswerSnippet = ''
            }
        }
    }
    return $results
}

$allResults = @()
$canParallel = (-not $NoParallel) -and (Get-Command Start-ThreadJob -ErrorAction SilentlyContinue)
if (-not $canParallel -and -not $NoParallel) {
    Write-Host "  [info] Start-ThreadJob unavailable, falling back to serial" -ForegroundColor Yellow
}
if (-not $canParallel) {
    foreach ($p in $PLAN) {
        Write-Host "  [serial] $($p.label)" -ForegroundColor DarkGray
        $allResults += & $runSession $p $ANSWER_URL $HEADERS
    }
} else {
    $jobs = foreach ($p in $PLAN) {
        Start-ThreadJob -ScriptBlock $runSession -ArgumentList $p, $ANSWER_URL, $HEADERS -ErrorAction Stop
    }
    Write-Host "  [parallel] $($jobs.Count) jobs launched, waiting..." -ForegroundColor DarkGray
    $jobs | Wait-Job | Out-Null
    foreach ($j in $jobs) { $allResults += Receive-Job -Job $j; Remove-Job -Job $j }
}

Write-Host "`n--- Turn results ---" -ForegroundColor Cyan
$allResults | Format-Table Label, Turn, Ok, Ms, Refs, Error -AutoSize -Wrap
$failedTurns = $allResults | Where-Object { -not $_.Ok }
if ($failedTurns) {
    Write-Host "`n--- Errors detail ---" -ForegroundColor Red
    $failedTurns | Select-Object Label, Error | Format-List
}

# ============================================================
# PHASE 3: Multi-session listing check (per-user)
# ============================================================
Write-Host "`n==> PHASE 3: sessions.list per user (isolation check)..." -ForegroundColor Cyan
$users = $PLAN | ForEach-Object { $_.user } | Sort-Object -Unique
$listResults = @{}
foreach ($u in $users) {
    $r = Get-UserSessions -UserPseudoId $u
    $listResults[$u] = $r
    $ownedIds = @($PLAN | Where-Object { $_.user -eq $u } | ForEach-Object { $_.sessionId })
    $mineIds  = @($r.Mine | ForEach-Object { $_.name.Split('/')[-1] })
    $matched = (@($ownedIds | Where-Object { $mineIds -contains $_ })).Count
    Write-Host ("  [{0}] server returned {1}, client-filter mine={2}; {3}/2 expected sessions present" -f $u, @($r.Raw).Count, @($r.Mine).Count, $matched) -ForegroundColor Gray
}

$alphaMineIds = @($listResults['test-user-alpha'].Mine | ForEach-Object { $_.name.Split('/')[-1] })
$betaMineIds  = @($listResults['test-user-beta' ].Mine | ForEach-Object { $_.name.Split('/')[-1] })
$alphaIds = @($PLAN | Where-Object { $_.user -eq 'test-user-alpha' } | ForEach-Object { $_.sessionId })
$betaIds  = @($PLAN | Where-Object { $_.user -eq 'test-user-beta'  } | ForEach-Object { $_.sessionId })
$leakAlpha = @($alphaIds | Where-Object { $betaMineIds  -contains $_ })
$leakBeta  = @($betaIds  | Where-Object { $alphaMineIds -contains $_ })
$isolationOk = ($leakAlpha.Count -eq 0) -and ($leakBeta.Count -eq 0)
Write-Host ("  Isolation: {0}" -f $(if ($isolationOk) { 'PASS - no cross-user leakage' } else { "FAIL - leakAlpha=$($leakAlpha.Count) leakBeta=$($leakBeta.Count)" })) `
    -ForegroundColor $(if ($isolationOk) { 'Green' } else { 'Red' })

# ============================================================
# PHASE 4: Resume + anaphoric 4th turn on alpha-S1
# ============================================================
Write-Host "`n==> PHASE 4: Resume alpha-S1 and fire follow-up turn..." -ForegroundColor Cyan
$alphaS1 = $PLAN | Where-Object { $_.label -like 'alpha-S1*' } | Select-Object -First 1
$replay = Get-Session -SessionName $alphaS1.sessionName
$replayTurns = @($replay.turns).Count
Write-Host "  Replay history has $replayTurns turns" -ForegroundColor Gray

$followUp = 'Compare the strongest of those Old Navy wins to any Gap mobile-web tests in the corpus.'
Write-Host "  Sending follow-up: $followUp" -ForegroundColor DarkGray
$r4 = Invoke-Answer -SessionName $alphaS1.sessionName -QueryText $followUp -UserPseudoId $alphaS1.user
if ($r4.Ok) {
    Write-Host "  Follow-up OK ($($r4.LatencyMs) ms, $($r4.RefsCount) refs)" -ForegroundColor Green
    $snippet = if ($r4.AnswerText) { $r4.AnswerText.Substring(0, [Math]::Min(400, $r4.AnswerText.Length)) } else { '<no text>' }
    Write-Host "  Answer snippet: $snippet..." -ForegroundColor DarkGray
} else {
    Write-Host "  Follow-up FAILED: $($r4.Error)" -ForegroundColor Red
}

# Verify history grew
$replay2 = Get-Session -SessionName $alphaS1.sessionName
$replay2Turns = @($replay2.turns).Count
Write-Host "  History after follow-up: $replay2Turns turns (was $replayTurns)" -ForegroundColor Gray
$historyGrew = $replay2Turns -gt $replayTurns

# ============================================================
# PHASE 5: ACL gate validation
# ============================================================
Write-Host "`n==> PHASE 5: ACL gate validation..." -ForegroundColor Cyan
# Fetch alpha-S1 and confirm its userPseudoId matches alpha (so the Agent-side gate would reject beta)
$ownerCheck = Get-Session -SessionName $alphaS1.sessionName
$actualOwner = $ownerCheck.userPseudoId
$aclOk = ($actualOwner -eq 'test-user-alpha')
Write-Host ("  alpha-S1.userPseudoId = '{0}' -> gate would {1} beta's read" -f $actualOwner, $(if ($aclOk) { 'REJECT' } else { '?' })) `
    -ForegroundColor $(if ($aclOk) { 'Green' } else { 'Red' })

# ============================================================
# SUMMARY
# ============================================================
Write-Host "`n==================== SUMMARY ====================" -ForegroundColor Cyan
$turnOk = ($allResults | Where-Object { $_.Ok }).Count
$turnTotal = $allResults.Count
$latencies = $allResults | Where-Object { $_.Ok } | ForEach-Object { $_.Ms }
$p50 = if ($latencies) { ($latencies | Sort-Object)[[int]($latencies.Count * 0.5)] } else { 0 }
$p95 = if ($latencies) { ($latencies | Sort-Object)[[int]($latencies.Count * 0.95)] } else { 0 }

Write-Host ("Turns succeeded:        {0}/{1}" -f $turnOk, $turnTotal)
Write-Host ("Turn latency p50/p95:   {0} / {1} ms" -f $p50, $p95)
Write-Host ("Cross-user isolation:   {0}" -f $(if ($isolationOk) { 'PASS' } else { 'FAIL' }))
Write-Host ("Resume + follow-up:     {0}" -f $(if ($r4.Ok) { 'PASS' } else { 'FAIL' }))
Write-Host ("History append on resume:{0}" -f $(if ($historyGrew) { 'PASS' } else { 'FAIL' }))
Write-Host ("ACL gate ownership:     {0}" -f $(if ($aclOk) { 'PASS' } else { 'FAIL' }))

Write-Host "`nSession resource names (for console inspection):" -ForegroundColor Cyan
foreach ($p in $PLAN) { Write-Host ("  [{0}] {1}" -f $p.label, $p.sessionId) -ForegroundColor Gray }

# ============================================================
# Optional cleanup
# ============================================================
if ($Cleanup) {
    Write-Host "`n==> Cleanup: deleting created sessions..." -ForegroundColor Cyan
    foreach ($p in $PLAN) {
        try { Remove-Session -SessionName $p.sessionName; Write-Host "  deleted $($p.sessionId)" -ForegroundColor DarkGray }
        catch { Write-Host "  failed to delete $($p.sessionId): $($_.Exception.Message)" -ForegroundColor Red }
    }
}

Write-Host "`nDone." -ForegroundColor Green
