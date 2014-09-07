# This scripts demonstrates how mitmproxy can switch to a different upstream proxy
# in upstream proxy mode.
#
# Usage: mitmdump -s "change_upstream_proxy.py host"
from libmproxy.protocol.http import send_connect_request

def should_redirect(flow):
	return (flow.request.host == "example.com")
alternative_upstream_proxy = ("localhost",8082)

def request(ctx, flow):
	if flow.live and should_redirect(flow):

		server_changed = flow.live.change_server(alternative_upstream_proxy, persistent_change=True)
		if flow.request.scheme == "https" and server_changed:
			send_connect_request(flow.live.c.server_conn, flow.request.host, flow.request.port)
			flow.live.c.establish_ssl(server=True)
