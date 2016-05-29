#!/bin/sh
set -e

PYVERSION=$1
VENV="venv$1"

echo "Creating dev environment in $VENV using Python $PYVERSION"

python$PYVERSION -m virtualenv "$VENV" --always-copy
. "$VENV/bin/activate"
pip$PYVERSION install -q -U pip setuptools
pip$PYVERSION install -q -r requirements.txt

echo ""
echo "* Virtualenv created in $VENV and all dependencies installed."
echo "* You can now activate the $(python --version) virtualenv with this command: \`. $VENV/bin/activate\`"
