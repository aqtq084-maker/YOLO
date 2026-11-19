$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$appPython = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $appPython)) {
    Write-Host 'venv not found. Follow the setup steps in README.md.'
    exit 1
}
& $appPython -c "import sys" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'The venv Python is unavailable. Recreate venv using the steps in README.md.'
    exit 1
}
& $appPython -m streamlit run (Join-Path $PSScriptRoot 'app.py') --server.address 127.0.0.1 --server.maxUploadSize 20
exit $LASTEXITCODE
