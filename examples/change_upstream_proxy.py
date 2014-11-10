# This scripts demonstrates how mitmproxy can switch to a second/different upstream proxy
# in upstream proxy mode.
#
# Usage: mitmdump -U http://default-upstream-proxy.local:8080/ -s "change_upstream_proxy.py host"
from libmproxy.protocol.http import send_connect_request

alternative_upstream_proxy = ("localhost", 8082)
def should_redirect(flow):
    return flow.request.host == "example.com"


def request(context, flow):
    if flow.live and should_redirect(flow):

        # If you want to change the target server, you should modify flow.request.host and flow.request.port
        # flow.live.change_server should only be used by inline scripts to change the upstream proxy,
        # unless you are sure that you know what you are doing.
        server_changed = flow.live.change_server(alternative_upstream_proxy, persistent_change=True)
        if flow.request.scheme == "https" and server_changed:
            send_connect_request(flow.live.c.server_conn, flow.request.host, flow.request.port)
            flow.live.c.establish_ssl(server=True)
