#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# This is only needed once to provision a new fresh empty S3 bucket.

aws configure set preview.cloudfront true
aws --profile mitmproxy \
    s3 cp --acl public-read ./bucketassets/error.html s3://docs.mitmproxy.org/error.html
aws --profile mitmproxy \
    s3 cp --acl public-read ./bucketassets/robots.txt s3://docs.mitmproxy.org/robots.txt
