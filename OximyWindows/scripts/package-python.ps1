# package-python.ps1
# Downloads and bundles Python embeddable package with mitmproxy

param(
    [string]$PythonVersion = "3.12.0",
    [string]$OutputDir = "..\src\OximyWindows\Resources\python-embed"
)

$ErrorActionPreference = "Stop"

# Resolve output directory
$OutputDir = Resolve-Path -Path (Join-Path $PSScriptRoot $OutputDir) -ErrorAction SilentlyContinue
if (-not $OutputDir) {
    $OutputDir = Join-Path $PSScriptRoot "..\src\OximyWindows\Resources\python-embed"
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
    $OutputDir = Resolve-Path $OutputDir
}

Write-Host "=== Oximy Python Bundler ===" -ForegroundColor Cyan
Write-Host "Python Version: $PythonVersion"
Write-Host "Output Directory: $OutputDir"
Write-Host ""

# Download URLs
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

# Temp paths
$TempDir = Join-Path $env:TEMP "oximy-python-bundle"
$ZipPath = Join-Path $TempDir "python-embed.zip"
$GetPipPath = Join-Path $TempDir "get-pip.py"

# Create temp directory
if (Test-Path $TempDir) {
    Remove-Item $TempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

try {
    # Step 1: Download Python embeddable package
    Write-Host "Step 1/5: Downloading Python $PythonVersion embeddable..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $PythonUrl -OutFile $ZipPath -UseBasicParsing
    Write-Host "  Downloaded: $ZipPath" -ForegroundColor Green

    # Step 2: Extract Python
    Write-Host "Step 2/5: Extracting Python..." -ForegroundColor Yellow
    if (Test-Path $OutputDir) {
        Remove-Item $OutputDir -Recurse -Force
    }
    Expand-Archive -Path $ZipPath -DestinationPath $OutputDir
    Write-Host "  Extracted to: $OutputDir" -ForegroundColor Green

    # Step 3: Enable pip and configure paths in python*._pth file
    # IMPORTANT: The ._pth file overrides PYTHONPATH, so we must add paths here
    Write-Host "Step 3/5: Enabling pip support and configuring paths..." -ForegroundColor Yellow
    $PthFile = Get-ChildItem $OutputDir -Filter "python*._pth" | Select-Object -First 1
    if ($PthFile) {
        # Build new ._pth content with all required paths
        # Note: Paths are relative to python.exe location (python-embed/)
        # IMPORTANT: The ..\oximy-addon path is required for mitmproxy to load the addon
        $NewPthContent = @(
            "python312.zip",
            ".",
            "Lib\site-packages",
            "..\oximy-addon",
            "",
            "# Enable site module for pip to work",
            "import site"
        )
        Set-Content $PthFile.FullName ($NewPthContent -join "`n")
        Write-Host "  Modified: $($PthFile.Name)" -ForegroundColor Green
        Write-Host "  Added Lib\site-packages to Python path" -ForegroundColor Green
    } else {
        Write-Warning "Could not find ._pth file to enable pip"
    }

    # Step 4: Install pip
    Write-Host "Step 4/5: Installing pip..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPipPath -UseBasicParsing
    $PythonExe = Join-Path $OutputDir "python.exe"
    & $PythonExe $GetPipPath --no-warn-script-location 2>&1 | Out-Null
    Write-Host "  Pip installed successfully" -ForegroundColor Green

    # Step 5: Install mitmproxy from LOCAL source (not PyPI)
    # IMPORTANT: We use the local mitmproxy source to include Oximy customizations:
    # - CONF_BASENAME = "oximy" for certificate naming (oximy-ca*.pem)
    # - Fixed keepserving.py for Oximy fork compatibility
    # - ScriptLoader addon for -s flag support
    Write-Host "Step 5/6: Installing mitmproxy from local source..." -ForegroundColor Yellow
    $MitmproxySource = Resolve-Path (Join-Path $PSScriptRoot "..\..\..") # Root of mitmproxy repo
    Write-Host "  Source: $MitmproxySource" -ForegroundColor Cyan
    & $PythonExe -m pip install $MitmproxySource --no-warn-script-location 2>&1 | ForEach-Object {
        if ($_ -match "Successfully installed") {
            Write-Host "  $_" -ForegroundColor Green
        }
    }

    # Step 6: Install jsonata-python for configurable parsers
    Write-Host "Step 6/6: Installing jsonata-python..." -ForegroundColor Yellow
    & $PythonExe -m pip install jsonata-python --no-warn-script-location 2>&1 | ForEach-Object {
        if ($_ -match "Successfully installed") {
            Write-Host "  $_" -ForegroundColor Green
        }
    }

    # Verify installation
    $MitmdumpExe = Join-Path $OutputDir "Scripts\mitmdump.exe"
    if (Test-Path $MitmdumpExe) {
        Write-Host ""
        Write-Host "=== Installation Complete ===" -ForegroundColor Cyan
        Write-Host "Python: $PythonExe"
        Write-Host "Mitmdump: $MitmdumpExe"

        # Get total size
        $TotalSize = (Get-ChildItem $OutputDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host "Total Size: $([math]::Round($TotalSize, 2)) MB"
    } else {
        throw "mitmdump.exe not found after installation"
    }

} finally {
    # Cleanup
    if (Test-Path $TempDir) {
        Remove-Item $TempDir -Recurse -Force
    }
}

Write-Host ""
Write-Host "Python embedding complete!" -ForegroundColor Green
