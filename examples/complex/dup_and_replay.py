from mitmproxy import ctx


def request(flow):
    f = flow.copy()
    ctx.master.view.add(f)
    f.request.path = "/changed"
    ctx.master.replay_request(f, block=True)
