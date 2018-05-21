#!/bin/sh
set -e

MITMPROXY_PATH="/home/mitmproxy/.mitmproxy"

if [[ "$1" = "mitmdump" || "$1" = "mitmproxy" || "$1" = "mitmweb" ]]; then
        mkdir -p "$MITMPROXY_PATH"
        chown -R mitmproxy:mitmproxy "$MITMPROXY_PATH"

        su-exec mitmproxy "$@"
else
        exec "$@"
fi
