#!/bin/bash
set -e
VENV=./venv

python -m virtualenv $VENV --always-copy
. $VENV/bin/activate
pip install -U pip setuptools
pip install -r requirements.txt

echo ""
echo "* Created virtualenv environment in $VENV."
echo "* Installed all dependencies into the virtualenv."
echo "* You can now activate the virtualenv: \`. $VENV/bin/activate\`"
