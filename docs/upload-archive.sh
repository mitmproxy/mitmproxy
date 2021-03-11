#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

if [[ $# -eq 0 ]] ; then
    echo "Please supply a version, e.g. 'v3'"
    exit 1
fi

# This script uploads docs to a specified archive version.

SPATH="/archive/$1"

aws configure set preview.cloudfront true
aws --profile mitmproxy \
    s3 sync --acl public-read ./public "s3://docs.mitmproxy.org$SPATH"
aws --profile mitmproxy \
    cloudfront create-invalidation --distribution-id E1TH3USJHFQZ5Q \
    --paths "$SPATH/*"
