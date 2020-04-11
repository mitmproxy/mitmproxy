#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

SCRIPTPATH="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
pushd ${SCRIPTPATH}

for script in scripts/* ; do
  output="${script##*/}"
  output="src/generated/${output%.*}.html"
  echo "Generating output for ${script} into ${output} ..."
  "${script}" > "${output}"
done

output="src/content/addons-examples.md"
echo "Generating examples content page into ${output} ..."
./render_examples.py > "${output}"

cd src
hugo
