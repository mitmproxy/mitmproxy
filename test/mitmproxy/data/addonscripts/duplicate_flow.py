from mitmproxy import ctx


def request():
    f = ctx.master.duplicate_flow(ctx.flow)
    ctx.master.replay_request(f, block=True)
