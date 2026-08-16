[CmdletBinding()]
param([switch]$SkipSetup)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$runtimeDir = Join-Path $projectRoot '.sentinel'
. (Join-Path $PSScriptRoot 'Import-SentinelEnv.ps1')
Import-SentinelEnv -Path (Join-Path $projectRoot '.env')

if (-not $SkipSetup) { & (Join-Path $PSScriptRoot 'setup.ps1') }
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null

$backendPython = Join-Path $projectRoot 'backend\.venv-win\Scripts\python.exe'
$backendDirectory = Join-Path $projectRoot 'backend'
Push-Location $backendDirectory
try {
    & $backendPython -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
} finally { Pop-Location }
$backendLog = Join-Path $runtimeDir 'backend.log'
$frontendLog = Join-Path $runtimeDir 'frontend.log'
$backendProcess = Start-Process -FilePath $backendPython -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' -WorkingDirectory $backendDirectory -RedirectStandardOutput $backendLog -RedirectStandardError (Join-Path $runtimeDir 'backend-error.log') -WindowStyle Hidden -PassThru
$frontendProcess = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run','dev' -WorkingDirectory (Join-Path $projectRoot 'frontend') -RedirectStandardOutput $frontendLog -RedirectStandardError (Join-Path $runtimeDir 'frontend-error.log') -WindowStyle Hidden -PassThru

Set-Content -LiteralPath (Join-Path $runtimeDir 'backend.pid') -Value $backendProcess.Id
Set-Content -LiteralPath (Join-Path $runtimeDir 'frontend.pid') -Value $frontendProcess.Id

$backendReady = $false
for ($attempt = 1; $attempt -le 15; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri 'http://localhost:8000/health' -TimeoutSec 5
        if ($health.status -eq 'ok') { $backendReady = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $backendReady) {
    & (Join-Path $PSScriptRoot 'stop.ps1')
    throw "Backend failed to start. Review $runtimeDir\backend-error.log"
}

$frontendReady = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    if ($frontendProcess.HasExited) { break }
    try {
        $response = Invoke-WebRequest -Uri 'http://localhost:3000/login' -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) { $frontendReady = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $frontendReady) {
    & (Join-Path $PSScriptRoot 'stop.ps1')
    throw "Frontend failed to start. Review $runtimeDir\frontend-error.log"
}

Write-Host 'Sentinel AI is running at http://localhost:3000' -ForegroundColor Green
Write-Host "Logs are stored in $runtimeDir"
