<#
.SYNOPSIS
    One-shot setup for the Vertex AI Search evaluation harness on Windows.

.DESCRIPTION
    1. Verifies Python 3.10+ is on PATH.
    2. Creates a local virtual environment at tests/eval/.venv (idempotent).
    3. Installs / upgrades requirements.txt.
    4. Bootstraps .env from .env.example if it does not exist yet.
    5. Reports gcloud / ADC status (does NOT log you in - that's interactive).

.EXAMPLE
    cd tests\eval
    .\setup.ps1
#>
[CmdletBinding()]
param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn2($msg) { Write-Host "    $msg" -ForegroundColor Yellow }

# --- 1. Python ---------------------------------------------------------------
Write-Step "Checking Python"
$pyCmd = Get-Command $PythonExe -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    throw "Python executable '$PythonExe' not found on PATH. Install Python 3.10+ from https://www.python.org/downloads/ and re-run."
}
$pyVer = & $PythonExe -c "import sys; print('{}.{}.{}'.format(*sys.version_info[:3]))"
$pyMajorMinor = & $PythonExe -c "import sys; print('{}.{}'.format(*sys.version_info[:2]))"
$pyMajMin = [version]$pyMajorMinor
if ($pyMajMin -lt [version]"3.10") {
    throw "Python $pyVer is too old. Need 3.10+."
}
Write-Ok "Python $pyVer at $($pyCmd.Source)"

# --- 2. Virtual environment --------------------------------------------------
$VenvDir = Join-Path $ScriptDir ".venv"
$VenvPy  = Join-Path $VenvDir "Scripts\python.exe"

# Detect a corrupted venv (Windows pip self-upgrade can leave ~ip stubs).
$venvCorrupted = $false
if (Test-Path $VenvDir) {
    $stale = Get-ChildItem -Path (Join-Path $VenvDir "Lib\site-packages") -Filter "~*" -ErrorAction SilentlyContinue
    if ($stale) { $venvCorrupted = $true }
    if (-not (Test-Path $VenvPy)) { $venvCorrupted = $true }
}
if ($venvCorrupted) {
    Write-Warn2 "Existing venv is corrupted - recreating."
    Remove-Item -Recurse -Force $VenvDir
}

if (-not (Test-Path $VenvPy)) {
    Write-Step "Creating virtual environment at $VenvDir"
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { throw "venv creation failed (exit $LASTEXITCODE)" }
    Write-Ok "venv created"
} else {
    Write-Step "Using existing virtual environment at $VenvDir"
}

# --- 3. Dependencies ---------------------------------------------------------
Write-Step "Installing requirements"
# Note: we deliberately skip `pip install --upgrade pip` here. On Windows
# (especially Python 3.14) pip's self-upgrade can hit a file-lock on its
# own _vendor dir mid-replace. The pip bundled with venv is fine for
# installing the requirements below.
& $VenvPy -m pip install -r (Join-Path $ScriptDir "requirements.txt") --quiet
if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
Write-Ok "Dependencies installed"

# --- 4. .env -----------------------------------------------------------------
$EnvFile    = Join-Path $ScriptDir ".env"
$EnvExample = Join-Path $ScriptDir ".env.example"
Write-Step "Checking .env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item $EnvExample $EnvFile
    Write-Warn2 ".env created from .env.example - EDIT IT before running:"
    Write-Warn2 "  notepad $EnvFile"
} else {
    Write-Ok ".env already exists"
}

# --- 5. gcloud / ADC ---------------------------------------------------------
Write-Step "Checking gcloud + ADC"
$gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloud) {
    Write-Warn2 "gcloud CLI not found. Install: https://cloud.google.com/sdk/docs/install"
} else {
    $activeAcct = (& gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null) -join ""
    if ([string]::IsNullOrWhiteSpace($activeAcct)) {
        Write-Warn2 "No active gcloud account. Run:  gcloud auth login <your-email>"
    } else {
        Write-Ok "Active account: $activeAcct"
    }
    $tok = & gcloud auth application-default print-access-token 2>$null
    if ([string]::IsNullOrWhiteSpace($tok)) {
        Write-Warn2 "Application Default Credentials not set. Run:"
        Write-Warn2 "  gcloud auth application-default login"
        Write-Warn2 "  gcloud auth application-default set-quota-project <your-project-id>"
    } else {
        Write-Ok "ADC token available ($($tok.Length) chars)"
    }
}

Write-Host ""
Write-Step "Setup complete."
Write-Host "Next:" -ForegroundColor White
Write-Host "  1. Edit .env (project id, search engine id, proxy if needed)"
Write-Host "  2. Run the eval:    .\run.ps1"
Write-Host "  3. Or dry-run:      .\run.ps1 --dry-run"
