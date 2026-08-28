$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "Python environment was not found. Please finish installation first." -ForegroundColor Red
    exit 1
}

# Keep the Windows entry point, while the lifecycle logic is shared by
# Windows, WSL/Linux and macOS.
& $python (Join-Path $root "start-webapp.py")
exit $LASTEXITCODE
