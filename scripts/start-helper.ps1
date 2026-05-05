$ErrorActionPreference = 'Stop'

# In PowerShell 7+, native stderr can be promoted to errors; Flask prints startup warnings to stderr.
if ($null -ne (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue)) {
    $PSNativeCommandUseErrorActionPreference = $false
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

$logsDir = Join-Path $projectRoot "logs"
if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
}

$stdoutLog = Join-Path $logsDir "helper.out.log"
$stderrLog = Join-Path $logsDir "helper.err.log"

function Get-PythonPath {
    param([string]$root)

    $candidates = @(
        (Join-Path $root "venv\Scripts\python.exe"),
        (Join-Path $root ".venv\Scripts\python.exe")
    )

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return "$($py.Source) -3"
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return $python.Source
    }

    throw "No Python executable found. Create venv at .\\venv or install Python."
}

$pythonCmd = Get-PythonPath -root $projectRoot
$appPath = Join-Path $projectRoot "app.py"

$env:HOST = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$env:PORT = if ($env:PORT) { $env:PORT } else { "5001" }
$env:PYTHONUNBUFFERED = "1"

Set-Location $projectRoot

$prevErrorAction = $ErrorActionPreference
$ErrorActionPreference = 'Continue'

if ($pythonCmd -like "* -3") {
    $parts = $pythonCmd.Split(' ', 2)
    & $parts[0] $parts[1] $appPath 1>> $stdoutLog 2>> $stderrLog
} else {
    & $pythonCmd $appPath 1>> $stdoutLog 2>> $stderrLog
}

$ErrorActionPreference = $prevErrorAction

if ($LASTEXITCODE -ne 0) {
    throw "Helper exited with code $LASTEXITCODE"
}
