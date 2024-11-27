#!/bin/bash

set -euxo pipefail

script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

for file in "$script_dir"/*.py; do
  "$file"
done
