from mitmproxy import http
import re


def response(flow: http.HTTPFlow) -> None:
    if flow.response and flow.response.content and flow.request.pretty_url.endswith(".js"):
        flow.response.content = re.sub(br"this[.]answers[.]push[(]([a-z]+)[)],", b"(this.answers.push(i),this.selectedOptions.push(\\1)),", flow.response.content)
