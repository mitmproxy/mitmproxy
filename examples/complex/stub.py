import mitmproxy
"""
    This is a script stub, with definitions for all events.
"""


def start():
    """
        Called once on script startup before any other events
    """
    mitmproxy.ctx.log("start")


def configure(options, updated):
    """
        Called once on script startup before any other events, and whenever options changes.
    """
    mitmproxy.ctx.log("configure")


def clientconnect(root_layer):
    """
        Called when a client initiates a connection to the proxy. Note that a
        connection can correspond to multiple HTTP requests
    """
    mitmproxy.ctx.log("clientconnect")


def request(flow):
    """
        Called when a client request has been received.
    """
    mitmproxy.ctx.log("request")


def serverconnect(server_conn):
    """
        Called when the proxy initiates a connection to the target server. Note that a
        connection can correspond to multiple HTTP requests
    """
    mitmproxy.ctx.log("serverconnect")


def responseheaders(flow):
    """
        Called when the response headers for a server response have been received,
        but the response body has not been processed yet. Can be used to tell mitmproxy
        to stream the response.
    """
    mitmproxy.ctx.log("responseheaders")


def response(flow):
    """
       Called when a server response has been received.
    """
    mitmproxy.ctx.log("response")


def error(flow):
    """
        Called when a flow error has occured, e.g. invalid server responses, or
        interrupted connections. This is distinct from a valid server HTTP error
        response, which is simply a response with an HTTP error code.
    """
    mitmproxy.ctx.log("error")


def serverdisconnect(server_conn):
    """
        Called when the proxy closes the connection to the target server.
    """
    mitmproxy.ctx.log("serverdisconnect")


def clientdisconnect(root_layer):
    """
        Called when a client disconnects from the proxy.
    """
    mitmproxy.ctx.log("clientdisconnect")


def done():
    """
        Called once on script shutdown, after any other events.
    """
    mitmproxy.ctx.log("done")
