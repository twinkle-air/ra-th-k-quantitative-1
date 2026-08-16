$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path -LiteralPath $VenvPython) {
    $PythonExe = $VenvPython
} else {
    $PythonExe = (Get-Command python -ErrorAction Stop).Source
}

& $PythonExe -c "import fastapi, uvicorn, xlrd" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Missing dependencies. Run: python -m pip install -r requirements.txt"
}

& $PythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
