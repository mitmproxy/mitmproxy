#!/bin/sh
set -e
set -x

PYVERSION=3.5
VENV="venv$PYVERSION"

echo "Creating dev environment in $VENV using Python $PYVERSION"

python$PYVERSION -m venv "$VENV"
. "$VENV/bin/activate"
pip$PYVERSION install -U pip setuptools
pip$PYVERSION install -r requirements.txt

echo ""
echo "* Virtualenv created in $VENV and all dependencies installed."
echo "* You can now activate the $(python --version) virtualenv with this command: \`. $VENV/bin/activate\`"
