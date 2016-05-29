
def request(ctx, f):
    f = ctx.duplicate_flow(f)
    ctx.replay_request(f)
