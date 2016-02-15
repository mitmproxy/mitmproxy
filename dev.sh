#!/bin/bash
set -e
VENV=./venv

python -m virtualenv $VENV --always-copy
. $VENV/bin/activate
pip install -e ./netlib[dev]
pip install -e ./pathod[dev]
pip install -e ./mitmproxy[dev,examples,contentviews]

echo ""
echo "* Created virtualenv environment in $VENV."
echo "* Installed all dependencies into the virtualenv."
echo "* You can now activate the virtualenv: \`. $VENV/bin/activate\`"
