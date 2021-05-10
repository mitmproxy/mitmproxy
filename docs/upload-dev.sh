#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

if [[ $GITHUB_REF != "refs/heads/actions-hardening" ]]; then
  echo "Looks like we are not running on CI."
  exit 1
fi

# This script is run during CI on the main branch and uploads docs to docs.mitmproxy.org/dev.

aws configure set preview.cloudfront true
aws s3 sync --delete --acl public-read ./public s3://docs.mitmproxy.org/dev
aws cloudfront create-invalidation --distribution-id E1TH3USJHFQZ5Q --paths "/dev/*"
