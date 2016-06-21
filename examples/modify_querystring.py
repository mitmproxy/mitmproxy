from mitmproxy import ctx


def request():
    ctx.flow.request.query["mitmproxy"] = "rocks"
