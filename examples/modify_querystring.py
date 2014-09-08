
def request(context, flow):
    q = flow.request.get_query()
    if q:
        q["mitmproxy"] = ["rocks"]
        flow.request.set_query(q)