from mitmproxy import ctx


def request(flow):
    f = ctx.master.state.duplicate_flow(flow)
    ctx.master.replay_request(f, block=True)
