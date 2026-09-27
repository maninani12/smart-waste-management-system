$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Run Setup.ps1 first.' }
if (-not (Test-Path -LiteralPath 'frontend\dist\index.html')) { throw 'Run Setup.ps1 first to build the interface.' }
& $pythonPath -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Database migration failed.' }
Write-Host 'Open http://127.0.0.1:8000. Press Ctrl+C here to stop.'
& $pythonPath -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
