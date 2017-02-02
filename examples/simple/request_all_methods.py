from mitmproxy import ctx


def request(flow):
    methods = ["GET", "POST", "PUT", "DELETE"]
    methods.remove(flow.request.method)
    f1 = flow.copy()
    f2 = flow.copy()
    f3 = flow.copy()
    if not flow.request.is_replay:
        ctx.master.new_request(methods[0], f1)
        ctx.master.new_request(methods[1], f2)
        ctx.master.new_request(methods[2], f3)
