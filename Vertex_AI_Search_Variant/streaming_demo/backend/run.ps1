<#
.SYNOPSIS
  Boots the streaming demo backend on http://127.0.0.1:8765.

.DESCRIPTION
  Creates a venv on first run, installs requirements, and starts uvicorn with
  reload disabled (reload + StreamingResponse on Windows occasionally drops the
  upstream socket on file changes). Run from anywhere.
#>
[CmdletBinding()]
param(
    [int]$Port = 8765,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$venv = Join-Path $here ".venv"
$python = Join-Path $venv "Scripts\python.exe"
$pip = Join-Path $venv "Scripts\pip.exe"

if (-not (Test-Path $python)) {
    Write-Host "==> creating venv at $venv" -ForegroundColor Cyan
    py -3 -m venv $venv
}

Write-Host "==> installing requirements" -ForegroundColor Cyan
& $pip install --quiet --disable-pip-version-check -r (Join-Path $here "requirements.txt")

Write-Host "==> starting uvicorn on http://${BindHost}:${Port}" -ForegroundColor Green
& $python -m uvicorn app.main:app --host $BindHost --port $Port --log-level info
