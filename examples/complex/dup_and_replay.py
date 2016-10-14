from mitmproxy import master


def request(flow):
    f = master.duplicate_flow(flow)
    f.request.path = "/changed"
    master.replay_request(f, block=True, run_scripthooks=False)
