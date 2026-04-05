param(
    [switch]$SkipPlaywright
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ("[install] " + $Message) -ForegroundColor Cyan
}

function Resolve-PythonCommand {
    $candidates = @(
        @{ Name = "py"; Args = @("-3.11") },
        @{ Name = "py"; Args = @("-3") },
        @{ Name = "python"; Args = @() },
        @{ Name = "python3"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        $cmd = Get-Command $candidate.Name -ErrorAction SilentlyContinue
        if ($null -eq $cmd) {
            continue
        }
        try {
            & $candidate.Name @($candidate.Args + @("-c", "import sys; print(sys.version_info[0], sys.version_info[1])")) | Out-Null
            return $candidate
        }
        catch {
            continue
        }
    }

    throw "Python not found. Please install Python 3.11+ from https://www.python.org/downloads/windows/"
}

function Assert-PythonVersion {
    param(
        [hashtable]$PythonCommand
    )

    $versionRaw = & $PythonCommand.Name @($PythonCommand.Args + @("-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}')"))
    $versionText = ($versionRaw | Select-Object -First 1).ToString().Trim()
    if (-not $versionText) {
        throw "Unable to detect Python version."
    }

    $parts = $versionText.Split(".")
    $major = [int]$parts[0]
    $minor = [int]$parts[1]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        throw "Detected Python $versionText, but this project requires Python 3.11+."
    }

    return $versionText
}

function Run-PythonModule {
    param(
        [hashtable]$PythonCommand,
        [string[]]$ModuleArgs
    )
    & $PythonCommand.Name @($PythonCommand.Args + @("-m") + $ModuleArgs)
}

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $repoRoot = Resolve-Path (Join-Path $scriptDir "..")
    Set-Location $repoRoot

    Write-Step "Repository: $repoRoot"
    Write-Step "Resolving Python command..."
    $pythonCommand = Resolve-PythonCommand

    $version = Assert-PythonVersion -PythonCommand $pythonCommand
    Write-Step "Using Python $version via '$($pythonCommand.Name) $($pythonCommand.Args -join ' ')'"

    Write-Step "Upgrading pip..."
    Run-PythonModule -PythonCommand $pythonCommand -ModuleArgs @("pip", "install", "--upgrade", "pip")

    Write-Step "Installing project package in editable mode..."
    Run-PythonModule -PythonCommand $pythonCommand -ModuleArgs @("pip", "install", "-e", ".")

    Write-Step "Installing Playwright Python package..."
    Run-PythonModule -PythonCommand $pythonCommand -ModuleArgs @("pip", "install", "playwright")

    if (-not $SkipPlaywright) {
        Write-Step "Installing Playwright Chromium runtime..."
        Run-PythonModule -PythonCommand $pythonCommand -ModuleArgs @("playwright", "install", "chromium")
    }
    else {
        Write-Step "Skipping Playwright browser install because -SkipPlaywright is set."
    }

    Write-Host ""
    Write-Host "Install finished." -ForegroundColor Green
    Write-Host "Next steps:" -ForegroundColor Green
    Write-Host "1) Login check:" -ForegroundColor Green
    Write-Host "   python examples/run_real_site_once.py --login-only --require-login --login-timeout 180 --profile-dir .playwright_profile_main"
    Write-Host "2) Start GUI:" -ForegroundColor Green
    Write-Host "   python tools/run_scan_gui.py"
}
catch {
    Write-Host ""
    Write-Host ("Install failed: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
