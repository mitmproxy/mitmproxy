#!/bin/sh
set -e
set -x

PYVERSION=$1
VENV="venv$1"

echo "Creating dev environment in $VENV using Python $PYVERSION"
virtualenv "$VENV" --no-setuptools
. "$VENV/bin/activate"
pip$PYVERSION install -U pip setuptools
pip$PYVERSION install -r requirements.txt

echo ""
echo "* Virtualenv created in $VENV and all dependencies installed."
echo "* You can now activate the $(python --version) virtualenv with this command: \`. $VENV/bin/activate\`"
