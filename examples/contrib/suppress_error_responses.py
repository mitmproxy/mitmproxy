"""
This script suppresses the 502 Bad Gateway messages, mitmproxy sends if the server is not responsing correctly.
For example, this functionality can be helpful if mitmproxy is used in between a web scanner and a web application.
Without this script, if the web application under test crashes, mitmproxy will send 502 Bad Gateway responses.
These responses are irritating the web application scanner since they obfuscate the actual problem.
"""
from mitmproxy import http
from mitmproxy.exceptions import HttpSyntaxException


def error(self, flow: http.HTTPFlow):
    """Kills the flow if it has an error different to HTTPSyntaxException.
            Sometimes, web scanners generate malformed HTTP syntax on purpose and we do not want to kill these requests.
    """
    if flow.error is not None and not isinstance(flow.error, HttpSyntaxException):
        flow.kill()
