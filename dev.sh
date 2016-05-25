#!/bin/sh
set -e

VENV="./venv"
VENV3="${VENV}3"

python -m virtualenv $VENV --always-copy
. $VENV/bin/activate
pip install -q -U pip setuptools
pip install -q -r requirements.txt

echo ""
echo "* Virtualenv created in $VENV and all dependencies installed."
echo "* You can now activate the $(python --version) virtualenv with this command: \`. $VENV/bin/activate\`"

if $(python --version 2>&1 | grep -q "Python 2.") && command -v python3 >/dev/null 2>&1; then
	echo ""
	echo ""
	
  python3 -m virtualenv "$VENV3" --always-copy
	. "$VENV3/bin/activate"
	pip install -q -U pip setuptools
	pip install -q -r requirements.txt

	echo ""
	echo "* Virtualenv created in $VENV3 and all dependencies installed."
  echo "* You can now activate the $(python --version) virtualenv with this command: \`. $VENV3/bin/activate\`"
fi

