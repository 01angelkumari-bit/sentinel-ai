[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $PSScriptRoot 'Import-SentinelEnv.ps1')

function Require-Command {
    param([string]$Name, [string]$InstallHint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required. $InstallHint"
    }
}

Require-Command 'py' 'Install Python 3.12 from python.org with the Python Launcher enabled.'
Require-Command 'node' 'Install Node.js 22 LTS from nodejs.org.'
Require-Command 'npm.cmd' 'Reinstall Node.js 22 LTS and enable PATH integration.'

$envFile = Join-Path $projectRoot '.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot '.env.windows.example') -Destination $envFile
    throw "Created .env. Set POSTGRES_PASSWORD, DATABASE_URL, and JWT_SECRET_KEY, then run this script again."
}

Import-SentinelEnv -Path $envFile
if ($env:JWT_SECRET_KEY.StartsWith('replace-with-')) {
    throw 'Replace the default JWT_SECRET_KEY value in .env before continuing.'
}

$backend = Join-Path $projectRoot 'backend'
$venvPython = Join-Path $backend '.venv-win\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & py -3.12 -m venv (Join-Path $backend '.venv-win')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 virtual environment creation failed.' }
}
& $venvPython -m pip install --disable-pip-version-check --timeout 1000 --retries 10 -r (Join-Path $backend 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Backend dependency installation failed.' }

Push-Location $backend
try {
    & $venvPython -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
} finally { Pop-Location }

Push-Location (Join-Path $projectRoot 'frontend')
try {
    & npm.cmd install --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
} finally { Pop-Location }

Write-Host 'Sentinel AI Windows setup completed successfully.' -ForegroundColor Green
