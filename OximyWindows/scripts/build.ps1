# build.ps1
# Builds OximyWindows application

param(
    [switch]$Release,
    [switch]$Clean,
    [switch]$CreateInstaller,
    [switch]$Install,
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

$Configuration = if ($Release) { "Release" } else { "Debug" }
$ProjectDir = Join-Path $PSScriptRoot "..\src\OximyWindows"
$OutputDir = Join-Path $PSScriptRoot "..\publish\win-x64"
$InstallerDir = Join-Path $PSScriptRoot "..\installer"

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

# Step 7: Install to user's local app data if requested
if ($Install) {
    Write-Host ""
    Write-Host "Installing to local app data..." -ForegroundColor Yellow

    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\Oximy"

    # Stop any running instance
    $RunningProcess = Get-Process -Name "Oximy" -ErrorAction SilentlyContinue
    if ($RunningProcess) {
        Write-Host "  Stopping running instance..." -ForegroundColor Yellow
        $RunningProcess | Stop-Process -Force
        Start-Sleep -Seconds 1
    }

    # Remove old installation
    if (Test-Path $InstallDir) {
        Write-Host "  Removing old installation..." -ForegroundColor Yellow
        Remove-Item $InstallDir -Recurse -Force
    }

    # Copy published files
    Copy-Item $OutputDir -Destination $InstallDir -Recurse
    Write-Host "  Installed to: $InstallDir" -ForegroundColor Green

    # Register URL scheme
    $ExePath = Join-Path $InstallDir "Oximy.exe"
    $RegPath = "HKCU:\Software\Classes\oximy"

    Write-Host "  Registering oximy:// URL scheme..." -ForegroundColor Yellow
    if (Test-Path $RegPath) {
        Remove-Item $RegPath -Recurse -Force
    }

    New-Item -Path $RegPath -Force | Out-Null
    Set-ItemProperty -Path $RegPath -Name "(Default)" -Value "URL:Oximy Protocol"
    Set-ItemProperty -Path $RegPath -Name "URL Protocol" -Value ""

    New-Item -Path "$RegPath\shell\open\command" -Force | Out-Null
    Set-ItemProperty -Path "$RegPath\shell\open\command" -Name "(Default)" -Value "`"$ExePath`" `"%1`""

    Write-Host "  Registered oximy:// URL scheme" -ForegroundColor Green

    # Create Start Menu shortcut
    $StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
    $ShortcutPath = Join-Path $StartMenuDir "Oximy.lnk"

    Write-Host "  Creating Start Menu shortcut..." -ForegroundColor Yellow
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)
    $Shortcut.TargetPath = $ExePath
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.Description = "Oximy Sensor"
    $Shortcut.Save()

    Write-Host "  Created Start Menu shortcut" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installation complete!" -ForegroundColor Cyan
    Write-Host "Run 'Oximy' from Start Menu or: $ExePath" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Cyan

# Print summary
$ExePath = Join-Path $OutputDir "Oximy.exe"
if (Test-Path $ExePath) {
    $FileInfo = Get-Item $ExePath
    Write-Host "Executable: $ExePath"
    Write-Host "Size: $([math]::Round($FileInfo.Length / 1MB, 2)) MB"

    # Total output size
    $TotalSize = (Get-ChildItem $OutputDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "Total Output Size: $([math]::Round($TotalSize, 2)) MB"
}
