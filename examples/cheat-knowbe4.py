import re

from mitmproxy import http


def response(flow: http.HTTPFlow) -> None:
    if (
        flow.response
        and flow.response.content
        and flow.request.pretty_url.endswith(".js")
    ):
        flow.response.content = re.sub(
            rb"this[.]answers[.]push[(]([a-z]+)[)],",
            b"(this.answers.push(i),this.selectedOptions.push(\\1)),",
            flow.response.content,
        )
