#!/bin/bash
set -e
VENV=./venv

python -m virtualenv $VENV --always-copy
. $VENV/bin/activate
pip_version=$(pip -V | cut -d' ' -f 2 | cut -d'.' -f 1)
if [ "$pip_version" -lt 6 ];
then
	echo "Error. Outdated pip"
	echo "To upgrade pip run: \`pip install -U pip\`r"
	exit 1
fi
pip install -r requirements.txt

echo ""
echo "* Created virtualenv environment in $VENV."
echo "* Installed all dependencies into the virtualenv."
echo "* You can now activate the virtualenv: \`. $VENV/bin/activate\`"
