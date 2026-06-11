<#
.SYNOPSIS
    Activate the venv and run the Vertex AI Search evaluation harness.

.DESCRIPTION
    Forwards all arguments verbatim to run_eval.py. Examples:
      .\run.ps1
      .\run.ps1 --dry-run
      .\run.ps1 --search-engine-id my-other-engine --concurrency 4

.NOTES
    HTTPS_PROXY etc. are loaded from .env automatically by run_eval.py
    (python-dotenv). No manual proxy export needed.
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ForwardedArgs
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$VenvPy = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPy)) {
    throw "Virtual environment not found at $VenvPy. Run .\setup.ps1 first."
}

if (-not (Test-Path (Join-Path $ScriptDir ".env"))) {
    Write-Warning ".env not found - copy .env.example to .env and edit it."
}

& $VenvPy (Join-Path $ScriptDir "run_eval.py") @ForwardedArgs
exit $LASTEXITCODE
