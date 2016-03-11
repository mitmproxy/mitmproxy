def request(context, flow):
    q = flow.request.query
    if q:
        q["mitmproxy"] = ["rocks"]
        flow.request.query = q
