# This script makes mitmproxy switch to passthrough mode for all HTTP
# responses with "Connection: Upgrade" header. This is useful to make
# WebSockets work in untrusted environments.
#
# Note: Chrome (and possibly other browsers), when explicitly configured
# to use a proxy (i.e. mitmproxy's regular mode), send a CONNECT request
# to the proxy before they initiate the websocket connection.
# To make WebSockets work in these cases, supply
# `--ignore :80$` as an additional parameter.
# (see http://mitmproxy.org/doc/features/passthrough.html)

from libmproxy.protocol.http import HTTPRequest
from libmproxy.protocol.tcp import TCPHandler
from libmproxy.protocol import KILL
from libmproxy.script import concurrent


def start(context, argv):
    HTTPRequest._headers_to_strip_off.remove("Connection")
    HTTPRequest._headers_to_strip_off.remove("Upgrade")


def done(context):
    HTTPRequest._headers_to_strip_off.append("Connection")
    HTTPRequest._headers_to_strip_off.append("Upgrade")

@concurrent
def response(context, flow):
    if flow.response.headers.get_first("Connection", None) == "Upgrade":
        # We need to send the response manually now...
        flow.client_conn.send(flow.response.assemble())
        # ...and then delegate to tcp passthrough.
        TCPHandler(flow.live.c, log=False).handle_messages()
        flow.reply(KILL)