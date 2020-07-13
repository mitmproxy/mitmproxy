#!/bin/sh
# WARNING: do not change the shebang - the Docker base image might not have what you want!

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

MITMPROXY_PATH="/home/mitmproxy/.mitmproxy"

if [[ "$1" = "mitmdump" || "$1" = "mitmproxy" || "$1" = "mitmweb" ]]; then
  mkdir -p "$MITMPROXY_PATH"
  chown -R mitmproxy:mitmproxy "$MITMPROXY_PATH"
  su-exec mitmproxy "$@"
else
  exec "$@"
fi
