[CmdletBinding()]
param()

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$runtimeDir = Join-Path $projectRoot '.sentinel'
foreach ($name in @('backend', 'frontend')) {
    $pidFile = Join-Path $runtimeDir "$name.pid"
    if (-not (Test-Path -LiteralPath $pidFile)) { continue }
    $processId = [int](Get-Content -LiteralPath $pidFile)
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) { & taskkill.exe /PID $processId /T /F | Out-Null }
    Remove-Item -LiteralPath $pidFile -Force
}
Write-Host 'Sentinel AI services stopped.'
