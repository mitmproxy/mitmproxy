#!/bin/sh
# WARNING: do not change the shebang - the Docker base image might not have what you want!

set -o errexit
# set -o pipefail
# Commented out since the option wasn't working on sh in Debian Buster
set -o nounset
# set -o xtrace

MITMPROXY_PATH="/home/mitmproxy/.mitmproxy"

if [[ "$1" = "mitmdump" || "$1" = "mitmproxy" || "$1" = "mitmweb" ]]; then
  mkdir -p "$MITMPROXY_PATH"
  chown -R mitmproxy:mitmproxy "$MITMPROXY_PATH"
  su - mitmproxy -c "$@" # su-exec didn't have a package for Debian Buster, hence su
else
  exec "$@"
fi
