# build.ps1
# Builds OximyWindows application

param(
    [switch]$Release,
    [switch]$Clean,
    [switch]$CreateInstaller
)

$ErrorActionPreference = "Stop"

$Configuration = if ($Release) { "Release" } else { "Debug" }
$ProjectDir = Join-Path $PSScriptRoot "..\src\OximyWindows"
$OutputDir = Join-Path $PSScriptRoot "..\publish\win-x64"
$InstallerDir = Join-Path $PSScriptRoot "..\installer"

Write-Host "=== Oximy Windows Build ===" -ForegroundColor Cyan
Write-Host "Configuration: $Configuration"
Write-Host ""

# Step 1: Clean if requested
if ($Clean) {
    Write-Host "Cleaning previous builds..." -ForegroundColor Yellow
    if (Test-Path $OutputDir) {
        Remove-Item $OutputDir -Recurse -Force
    }
    dotnet clean (Join-Path $ProjectDir "OximyWindows.csproj") -c $Configuration 2>&1 | Out-Null
    Write-Host "  Clean complete" -ForegroundColor Green
}

# Step 2: Check for Python embed
$PythonDir = Join-Path $ProjectDir "Resources\python-embed"
if (-not (Test-Path (Join-Path $PythonDir "python.exe"))) {
    Write-Host "Python embed not found. Running package-python.ps1..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot "package-python.ps1")
}

# Step 3: Copy oximy-addon from mitmproxy source (single source of truth)
$AddonSrc = Join-Path $PSScriptRoot "..\..\mitmproxy\addons\oximy"
$AddonDst = Join-Path $ProjectDir "Resources\oximy-addon"

if (-not (Test-Path (Join-Path $AddonSrc "addon.py"))) {
    Write-Error "Addon source not found at $AddonSrc"
    exit 1
}

Write-Host "Copying oximy-addon from source..." -ForegroundColor Yellow
if (Test-Path $AddonDst) {
    Remove-Item $AddonDst -Recurse -Force
}
Copy-Item $AddonSrc -Destination $AddonDst -Recurse
Write-Host "  Copied addon from: $AddonSrc" -ForegroundColor Green

# Step 4: Restore packages
Write-Host "Restoring NuGet packages..." -ForegroundColor Yellow
dotnet restore (Join-Path $ProjectDir "OximyWindows.csproj")
Write-Host "  Restore complete" -ForegroundColor Green

# Step 5: Build
Write-Host "Building OximyWindows ($Configuration)..." -ForegroundColor Yellow
dotnet publish (Join-Path $ProjectDir "OximyWindows.csproj") `
    -c $Configuration `
    -r win-x64 `
    --self-contained true `
    -o $OutputDir `
    -p:PublishSingleFile=false `
    -p:IncludeNativeLibrariesForSelfExtract=true

if ($LASTEXITCODE -ne 0) {
    Write-Error "Build failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "  Build complete: $OutputDir" -ForegroundColor Green

# Step 6: Create installer if requested
if ($CreateInstaller) {
    Write-Host ""
    Write-Host "Creating installer..." -ForegroundColor Yellow

    $InnoSetup = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $InnoSetup)) {
        Write-Warning "Inno Setup not found at $InnoSetup"
        Write-Warning "Please install Inno Setup 6 from https://jrsoftware.org/isdl.php"
        exit 1
    }

    $IssFile = Join-Path $InstallerDir "OximySetup.iss"
    if (-not (Test-Path $IssFile)) {
        Write-Error "Installer script not found at $IssFile"
        exit 1
    }

    & $InnoSetup $IssFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Installer creation failed"
        exit $LASTEXITCODE
    }

    Write-Host "  Installer created in: $(Join-Path $InstallerDir 'Output')" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Cyan

# Print summary
$ExePath = Join-Path $OutputDir "OximyWindows.exe"
if (Test-Path $ExePath) {
    $FileInfo = Get-Item $ExePath
    Write-Host "Executable: $ExePath"
    Write-Host "Size: $([math]::Round($FileInfo.Length / 1MB, 2)) MB"

    # Total output size
    $TotalSize = (Get-ChildItem $OutputDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "Total Output Size: $([math]::Round($TotalSize, 2)) MB"
}
