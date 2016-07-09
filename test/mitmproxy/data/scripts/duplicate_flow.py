import mitmproxy


def request(f):
    f = mitmproxy.ctx.master.duplicate_flow(f)
    mitmproxy.ctx.master.replay_request(f, block=True, run_scripthooks=False)
