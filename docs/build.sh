#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
pushd ${SCRIPTPATH}

for script in scripts/*.py ; do
  output="${script##*/}"
  output="src/generated/${output%.*}.html"
  echo "Generating output for ${script} into ${output} ..."
  "${script}" > "${output}"
done

cd src
hugo
