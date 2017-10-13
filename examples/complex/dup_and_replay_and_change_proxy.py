from mitmproxy import ctx


def request(flow):
    """
    Change the upstream proxy and then replay a request using that specific proxy.
    """
    f = flow.copy()
    ctx.master.view.add(f)
    f.request.path = "/changed"
    ctx.master.replay_request(f, block=True, upstream_proxy="localhost:5599")
