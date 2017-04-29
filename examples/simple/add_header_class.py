from mitmproxy import http


class AddHeader:
    def response(self, flow: http.HTTPFlow) -> None:
        flow.response.headers["newheader"] = "foo"


addons = [AddHeader()]
