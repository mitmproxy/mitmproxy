#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

MITMPROXY_PATH="/home/mitmproxy/.mitmproxy"

if [[ "$1" = "mitmdump" || "$1" = "mitmproxy" || "$1" = "mitmweb" ]]; then
  mkdir -p "$MITMPROXY_PATH"
  if [ -f "$MITMPROXY_PATH/mitmproxy-ca.pem" ]; then
    usermod -o \
        -u $(stat -c "%u" "$MITMPROXY_PATH/mitmproxy-ca.pem") \
        -g $(stat -c "%g" "$MITMPROXY_PATH/mitmproxy-ca.pem") \
        mitmproxy
  fi
  gosu mitmproxy "$@"
else
  exec "$@"
fi
