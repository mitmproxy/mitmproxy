from mitmproxy import ctx


def response():
    ctx.flow.response.headers["newheader"] = "foo"
