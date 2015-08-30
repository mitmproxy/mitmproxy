# This scripts demonstrates how mitmproxy can switch to a second/different upstream proxy
# in upstream proxy mode.
#
# Usage: mitmdump -U http://default-upstream-proxy.local:8080/ -s change_upstream_proxy.py
#
# If you want to change the target server, you should modify flow.request.host and flow.request.port
# flow.live.set_server should only be used by inline scripts to change the upstream proxy.


def proxy_address(flow):
    # Poor man's loadbalancing: route every second domain through the alternative proxy.
    if hash(flow.request.host) % 2 == 1:
        return ("localhost", 8082)
    else:
        return ("localhost", 8081)


def request(context, flow):
    if flow.request.method == "CONNECT":
        # If the decision is done by domain, one could also modify the server address here.
        # We do it after CONNECT here to have the request data available as well.
        return
    address = proxy_address(flow)
    if flow.live:
        if flow.request.scheme == "http":
            # For a normal HTTP request, we just change the proxy server and we're done!
            if address != flow.live.server_conn.address:
                flow.live.set_server(address, depth=1)
        else:
            # If we have CONNECTed (and thereby established "destination state"), the story is
            # a bit more complex. Now we don't want to change the top level address (which is
            # the connect destination) but the address below that. (Notice the `.via` and depth=2).
            if address != flow.live.server_conn.via.address:
                flow.live.set_server(address, depth=2)
