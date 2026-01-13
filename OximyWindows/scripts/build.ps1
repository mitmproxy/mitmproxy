# build.ps1
# Builds OximyWindows application

param(
    [switch]$Release,
    [switch]$Clean,
    [switch]$CreateInstaller,
    [switch]$CreateVelopack,
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$Configuration = if ($Release) { "Release" } else { "Debug" }
$ProjectDir = Join-Path $PSScriptRoot "..\src\OximyWindows"
$OutputDir = Join-Path $PSScriptRoot "..\publish\win-x64"
$InstallerDir = Join-Path $PSScriptRoot "..\installer"
$VelopackDir = Join-Path $PSScriptRoot "..\releases"

Write-Host "=== Oximy Windows Build ===" -ForegroundColor Cyan
Write-Host "Configuration: $Configuration"
Write-Host "Version: $Version"
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

# Step 3b: Fix imports for standalone addon (same as Mac approach)
# Replace "from mitmproxy.addons.oximy.xxx" with "from xxx" for local imports
Write-Host "Fixing addon imports for standalone use..." -ForegroundColor Yellow
Get-ChildItem $AddonDst -Filter "*.py" | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    # Replace "from mitmproxy.addons.oximy.xxx import" with "from xxx import"
    $content = $content -replace 'from mitmproxy\.addons\.oximy\.', 'from '
    # Replace "from mitmproxy.addons.oximy import" with "from " (for direct module imports)
    $content = $content -replace 'from mitmproxy\.addons\.oximy import', 'from . import'
    Set-Content $_.FullName $content -NoNewline
}
Write-Host "  Imports fixed for standalone addon" -ForegroundColor Green

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

# Step 5b: Update python._pth to include addon directory
# CRITICAL: The ._pth file overrides PYTHONPATH, so addon path must be added here
Write-Host "Updating Python path configuration..." -ForegroundColor Yellow
$PublishedPythonDir = Join-Path $OutputDir "Resources\python-embed"
$PthFile = Get-ChildItem $PublishedPythonDir -Filter "python*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($PthFile) {
    # Build new ._pth content with addon directory
    # Paths are relative to python.exe (which is in Resources/python-embed/)
    # The addon is at Resources/oximy-addon/, so relative path is ..\oximy-addon
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
    Write-Host "  Updated: $($PthFile.Name) with addon path" -ForegroundColor Green
} else {
    Write-Warning "Could not find ._pth file in published output"
}

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

# Step 7: Create Velopack release if requested
if ($CreateVelopack) {
    Write-Host ""
    Write-Host "Creating Velopack release..." -ForegroundColor Yellow

    # Ensure releases directory exists
    if (-not (Test-Path $VelopackDir)) {
        New-Item -ItemType Directory -Path $VelopackDir | Out-Null
    }

    # Install vpk tool if not available
    $vpkPath = (Get-Command vpk -ErrorAction SilentlyContinue)
    if (-not $vpkPath) {
        Write-Host "  Installing Velopack CLI tool..." -ForegroundColor Yellow
        dotnet tool install -g vpk
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Failed to install vpk tool. Please install manually: dotnet tool install -g vpk"
            exit 1
        }
    }

    # Get icon path
    $IconPath = Join-Path $ProjectDir "Assets\oximy.ico"

    # Create Velopack release
    Write-Host "  Packaging with Velopack (Version: $Version)..." -ForegroundColor Yellow
    vpk pack `
        --packId "Oximy" `
        --packVersion $Version `
        --packDir $OutputDir `
        --mainExe "OximyWindows.exe" `
        --outputDir $VelopackDir `
        --icon $IconPath

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Velopack packaging failed"
        exit $LASTEXITCODE
    }

    Write-Host "  Velopack release created in: $VelopackDir" -ForegroundColor Green

    # List created files
    Write-Host "  Release files:" -ForegroundColor Green
    Get-ChildItem $VelopackDir | ForEach-Object {
        Write-Host "    - $($_.Name)"
    }
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
