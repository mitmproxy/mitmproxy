$ErrorActionPreference = "Stop"

$pyver = python --version
if($pyver -notmatch "3\.[5-9]") {
    Write-Warning "Unexpected Python version, expected Python 3.5 or above: $pyver"
}

python -m venv .\venv --copies
& .\venv\Scripts\activate.ps1

python -m pip install --disable-pip-version-check -U pip
cmd /c "pip install -r requirements.txt 2>&1"

echo @"

  * Created virtualenv environment in .\venv.
  * Installed all dependencies into the virtualenv.
  * Activated virtualenv environment.

"@