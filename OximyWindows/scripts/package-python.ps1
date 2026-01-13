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

    # Step 3: Enable pip by modifying python*._pth file
    Write-Host "Step 3/5: Enabling pip support..." -ForegroundColor Yellow
    $PthFile = Get-ChildItem $OutputDir -Filter "python*._pth" | Select-Object -First 1
    if ($PthFile) {
        $PthContent = Get-Content $PthFile.FullName
        $PthContent = $PthContent -replace "#import site", "import site"
        Set-Content $PthFile.FullName $PthContent
        Write-Host "  Modified: $($PthFile.Name)" -ForegroundColor Green
    } else {
        Write-Warning "Could not find ._pth file to enable pip"
    }

    # Step 4: Install pip
    Write-Host "Step 4/5: Installing pip..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPipPath -UseBasicParsing
    $PythonExe = Join-Path $OutputDir "python.exe"
    & $PythonExe $GetPipPath --no-warn-script-location 2>&1 | Out-Null
    Write-Host "  Pip installed successfully" -ForegroundColor Green

    # Step 5: Install mitmproxy and dependencies
    Write-Host "Step 5/6: Installing mitmproxy..." -ForegroundColor Yellow
    & $PythonExe -m pip install mitmproxy --no-warn-script-location 2>&1 | ForEach-Object {
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
