#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

MITMPROXY_PATH="/home/mitmproxy/.mitmproxy"

if [[ "$1" = "mitmdump" || "$1" = "mitmproxy" || "$1" = "mitmweb" ]]; then
  mkdir -p "$MITMPROXY_PATH"
  chown -R mitmproxy:mitmproxy "$MITMPROXY_PATH"
  gosu mitmproxy "$@"
else
  exec "$@"
fi
