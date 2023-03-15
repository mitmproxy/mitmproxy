import logging

from mitmproxy import http


class ServerSideEvents:
    """
    Server-Side Events are currently swallowed if there's no streaming,
    see https://github.com/mitmproxy/mitmproxy/issues/4469.

    Until this bug is fixed, this addon warns the user about this.
    """

    def response(self, flow: http.HTTPFlow):
        assert flow.response
        is_sse = flow.response.headers.get("content-type", "").startswith(
            "text/event-stream"
        )
        if is_sse and not flow.response.stream:
            logging.warning(
                "mitmproxy currently does not support server side events. As a workaround, you can enable response "
                "streaming for such flows: https://github.com/mitmproxy/mitmproxy/issues/4469"
            )
