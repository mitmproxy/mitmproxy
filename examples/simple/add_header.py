from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    flow.response.headers["newheader"] = "foo"
