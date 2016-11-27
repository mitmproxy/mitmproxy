$ErrorActionPreference = "Stop"
$VENV = ".\venv"

python3 -m venv $VENV --copies
& $VENV\Scripts\activate.ps1

python -m pip install --disable-pip-version-check -U pip
cmd /c "pip install -r requirements.txt 2>&1"

echo @"

  * Created virtualenv environment in $VENV.
  * Installed all dependencies into the virtualenv.
  * Activated virtualenv environment.

"@