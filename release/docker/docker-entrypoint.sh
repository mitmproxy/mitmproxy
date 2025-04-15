#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

MITMPROXY_PATH="/home/mitmproxy/.mitmproxy"

if [ -f "$MITMPROXY_PATH/mitmproxy-ca.pem" ]; then
  f="$MITMPROXY_PATH/mitmproxy-ca.pem"
else
  f="$MITMPROXY_PATH"
fi
usermod -o \
    -u $(stat -c "%u" "$f") \
    -g $(stat -c "%g" "$f") \
    mitmproxy \
    >/dev/null  # hide "usermod: no changes"

if [[ "$1" = "mitmdump" || "$1" = "mitmproxy" || "$1" = "mitmweb" ]]; then
  # Drop privileges if we are starting one of the mitmproxy tools.
  exec gosu mitmproxy "$@"
else
  exec "$@"
fi
