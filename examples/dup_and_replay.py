from mitmproxy import ctx


def request(flow):
    f = ctx.master.state.duplicate_flow(flow)
    f.request.path = "/changed"
    ctx.master.replay_request(f, block=True, run_scripthooks=False)
