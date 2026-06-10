#!/bin/bash

sudo=""
if [[ $EUID -ne 0 ]]; then
	sudo="sudo"
fi

# ------------------------------------------------------------
# Put arch-specific install commands in these functions:
# ------------------------------------------------------------
install_ubuntu_deps() {
    # nothing for now
    true
}

install_osx_deps() {
    # nothing for now
    true
}
# ------------------------------------------------------------

realpath() {
    [[ $1 = /* ]] && echo "$1" || echo "$PWD/${1#./}"
}

arch=$(uname)
CURR_DIR=$(dirname "$(realpath "$0")")

if [ "$arch" = "Linux" ]; then
    install_ubuntu_deps
elif [ "$arch" = "Darwin" ]; then
    install_osx_deps
fi

pip install -q -e "${CURR_DIR}"
