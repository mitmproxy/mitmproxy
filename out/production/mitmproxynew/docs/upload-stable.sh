#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

aws configure set preview.cloudfront true
aws --profile mitmproxy \
    s3 sync --delete --acl public-read ./public s3://docs.mitmproxy.org/stable
aws --profile mitmproxy \
    cloudfront create-invalidation --distribution-id E1TH3USJHFQZ5Q \
    --paths "/stable/*"
