#!/bin/sh
set -e
set -x

echo "Creating dev environment in ./venv..."

python3 -m venv venv
. venv/bin/activate
pip3 install -U pip setuptools
pip3 install -r requirements.txt

echo ""
echo "  * Created virtualenv environment in ./venv."
echo "  * Installed all dependencies into the virtualenv."
echo "  * You can now activate the $(python3 --version) virtualenv with this command: \`. venv/bin/activate\`"