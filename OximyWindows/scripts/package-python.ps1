# package-python.ps1
# Downloads and bundles Python embeddable package with mitmproxy

param(
    [string]$PythonVersion = "3.12.0",
    [string]$OutputDir = "..\src\OximyWindows\Resources\python-embed"
)

# Note: Don't use "Stop" for ErrorActionPreference as pip outputs to stderr even on success
$ErrorActionPreference = "Continue"

# Helper function to download with retry logic
function Invoke-DownloadWithRetry {
    param(
        [string]$Uri,
        [string]$OutFile,
        [int]$MaxRetries = 3,
        [int]$RetryDelaySeconds = 5
    )

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        try {
            Write-Host "  Attempt $attempt of $MaxRetries..." -ForegroundColor Gray

            # Use .NET WebClient for more reliable downloads
            $webClient = New-Object System.Net.WebClient
            $webClient.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PowerShell")
            $webClient.DownloadFile($Uri, $OutFile)

            if (Test-Path $OutFile) {
                $fileSize = (Get-Item $OutFile).Length
                if ($fileSize -gt 0) {
                    Write-Host "  Download successful ($([math]::Round($fileSize / 1MB, 2)) MB)" -ForegroundColor Green
                    return $true
                }
            }
            throw "Downloaded file is empty or missing"
        }
        catch {
            Write-Host "  Attempt $attempt failed: $($_.Exception.Message)" -ForegroundColor Yellow
            if ($attempt -lt $MaxRetries) {
                Write-Host "  Retrying in $RetryDelaySeconds seconds..." -ForegroundColor Yellow
                Start-Sleep -Seconds $RetryDelaySeconds
                # Increase delay for next attempt
                $RetryDelaySeconds = $RetryDelaySeconds * 2
            }
            else {
                throw "Failed to download after $MaxRetries attempts: $Uri"
            }
        }
        finally {
            if ($webClient) {
                $webClient.Dispose()
            }
        }
    }
}

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
    Write-Host "Step 1/7: Downloading Python $PythonVersion embeddable..." -ForegroundColor Yellow
    Invoke-DownloadWithRetry -Uri $PythonUrl -OutFile $ZipPath

    # Step 2: Extract Python
    Write-Host "Step 2/7: Extracting Python..." -ForegroundColor Yellow
    if (Test-Path $OutputDir) {
        Remove-Item $OutputDir -Recurse -Force
    }
    Expand-Archive -Path $ZipPath -DestinationPath $OutputDir
    Write-Host "  Extracted to: $OutputDir" -ForegroundColor Green

    # Step 3: Enable pip and configure paths in python*._pth file
    # IMPORTANT: The ._pth file overrides PYTHONPATH, so we must add paths here
    Write-Host "Step 3/7: Enabling pip support and configuring paths..." -ForegroundColor Yellow
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

    # Step 4: Install pip and build tools
    Write-Host "Step 4/7: Installing pip and build tools..." -ForegroundColor Yellow
    Invoke-DownloadWithRetry -Uri $GetPipUrl -OutFile $GetPipPath
    $PythonExe = Join-Path $OutputDir "python.exe"
    & $PythonExe $GetPipPath --no-warn-script-location 2>&1 | Out-Null
    Write-Host "  Pip installed" -ForegroundColor Green

    # Install setuptools and wheel (required for building packages)
    & $PythonExe -m pip install setuptools wheel --no-warn-script-location 2>&1 | Out-Null
    Write-Host "  Setuptools and wheel installed" -ForegroundColor Green

    # Step 5: Pre-install ruamel.yaml without C extension
    # The C extension (ruamel.yaml.clibz) requires Python.h headers which aren't in embeddable Python
    Write-Host "Step 5/7: Installing ruamel.yaml (pure Python)..." -ForegroundColor Yellow
    & $PythonExe -m pip install "ruamel.yaml>=0.18.10,<=0.19.0" --no-deps --no-warn-script-location 2>&1 | Out-Null
    Write-Host "  ruamel.yaml installed (pure Python, no C extension)" -ForegroundColor Green

    # Step 6: Build and install mitmproxy from LOCAL source
    # IMPORTANT: We use the local mitmproxy source to include Oximy customizations:
    # - CONF_BASENAME = "oximy" in mitmproxy/options.py for certificate naming (oximy-ca*.pem)
    # - Certificates are generated with CN=oximy, O=oximy in ~/.mitmproxy/
    # - Fixed keepserving.py for Oximy fork compatibility
    # - ScriptLoader addon for -s flag support
    Write-Host "Step 6/7: Installing mitmproxy from local source..." -ForegroundColor Yellow
    # Path: scripts/ -> OximyWindows/ -> repo root (mitmproxy)
    $MitmproxySource = Resolve-Path (Join-Path $PSScriptRoot "..\..") # Root of mitmproxy repo
    Write-Host "  Source: $MitmproxySource" -ForegroundColor Cyan

    # First, build the wheel without deps
    $WheelDir = Join-Path $TempDir "wheels"
    New-Item -ItemType Directory -Path $WheelDir -Force | Out-Null
    $output = & $PythonExe -m pip wheel $MitmproxySource --no-deps -w $WheelDir 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host $output -ForegroundColor Red
        throw "Failed to build mitmproxy wheel"
    }
    Write-Host "  Built mitmproxy wheel" -ForegroundColor Green

    # Install the wheel without deps
    $MitmproxyWheel = Get-ChildItem $WheelDir -Filter "mitmproxy-*.whl" | Select-Object -First 1
    if (-not $MitmproxyWheel) {
        throw "mitmproxy wheel not found in $WheelDir"
    }
    $output = & $PythonExe -m pip install $MitmproxyWheel.FullName --no-deps --no-warn-script-location 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host $output -ForegroundColor Red
        throw "Failed to install mitmproxy wheel"
    }
    Write-Host "  Installed mitmproxy from wheel" -ForegroundColor Green

    # Install remaining dependencies (excluding ruamel.yaml which is already installed)
    Write-Host "  Installing mitmproxy dependencies..." -ForegroundColor Yellow
    $deps = @(
        "aioquic", "argon2-cffi", "asgiref", "bcrypt", "Brotli", "certifi",
        "cryptography", "flask", "h11", "h2", "hyperframe", "kaitaistruct",
        "ldap3", "mitmproxy_rs", "msgpack", "pydivert", "pyOpenSSL",
        "pyparsing", "pyperclip", "sortedcontainers", "tornado",
        "typing-extensions<=4.14", "urwid", "wsproto", "publicsuffix2", "zstandard"
    )
    # Install dependencies - pass as array, not as joined string
    $output = & $PythonExe -m pip install @deps --no-warn-script-location 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Warning: Some dependencies may have failed. Retrying..." -ForegroundColor Yellow
        # Retry with explicit list
        foreach ($dep in $deps) {
            & $PythonExe -m pip install $dep --no-warn-script-location 2>&1 | Out-Null
        }
    }
    $output | ForEach-Object {
        if ($_ -match "Successfully installed") {
            Write-Host "  $_" -ForegroundColor Green
        }
    }

    # Step 7: Install jsonata-python for configurable parsers
    Write-Host "Step 7/9: Installing jsonata-python..." -ForegroundColor Yellow
    & $PythonExe -m pip install jsonata-python --no-warn-script-location 2>&1 | ForEach-Object {
        if ($_ -match "Successfully installed") {
            Write-Host "  $_" -ForegroundColor Green
        }
    }

    # Step 8: Install watchfiles for local data collection file watching
    Write-Host "Step 8/9: Installing watchfiles..." -ForegroundColor Yellow
    & $PythonExe -m pip install watchfiles --no-warn-script-location 2>&1 | ForEach-Object {
        if ($_ -match "Successfully installed") {
            Write-Host "  $_" -ForegroundColor Green
        }
    }

    # Step 9: Install sentry-sdk for addon error tracking and event reporting
    Write-Host "Step 9/9: Installing sentry-sdk..." -ForegroundColor Yellow
    & $PythonExe -m pip install sentry-sdk --no-warn-script-location 2>&1 | ForEach-Object {
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
