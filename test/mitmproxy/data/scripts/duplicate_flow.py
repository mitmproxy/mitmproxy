import mitmproxy


def request(f):
    f = mitmproxy.master.duplicate_flow(f)
    mitmproxy.master.replay_request(f, block=True, run_scripthooks=False)
