from mitmproxy import http
from mitmproxy.connection import Server
from mitmproxy.net.server_spec import ServerSpec

# This scripts demonstrates how mitmproxy can switch to a second/different upstream proxy
# in upstream proxy mode.
#
# Usage: mitmdump
#   -s change_upstream_proxy.py
#   --mode upstream:http://default-upstream-proxy:8080/
#   --set connection_strategy=lazy
#   --set upstream_cert=false
#
# If you want to change the target server, you should modify flow.request.host and flow.request.port


def proxy_address(flow: http.HTTPFlow) -> tuple[str, int]:
    # Poor man's loadbalancing: route every second domain through the alternative proxy.
    if hash(flow.request.host) % 2 == 1:
        return ("localhost", 8082)
    else:
        return ("localhost", 8081)


def request(flow: http.HTTPFlow) -> None:
    address = proxy_address(flow)

    is_proxy_change = address != flow.server_conn.via.address
    server_connection_already_open = flow.server_conn.timestamp_start is not None
    if is_proxy_change and server_connection_already_open:
        # server_conn already refers to an existing connection (which cannot be modified),
        # so we need to replace it with a new server connection object.
        flow.server_conn = Server(address=flow.server_conn.address)
    flow.server_conn.via = ServerSpec(("http", address))
