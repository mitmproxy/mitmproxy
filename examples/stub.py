"""
    This is a script stub, with definitions for all events.
"""
def start(context, argv):
    """
        Called once on script startup, before any other events.
    """
    context.log("start")

def clientconnect(context, conn_handler):
    """
        Called when a client initiates a connection to the proxy. Note that a
        connection can correspond to multiple HTTP requests
    """
    context.log("clientconnect")

def serverconnect(context, conn_handler):
    """
        Called when the proxy initiates a connection to the target server. Note that a
        connection can correspond to multiple HTTP requests
    """
    context.log("serverconnect")

def request(context, flow):
    """
        Called when a client request has been received.
    """
    context.log("request")


def responseheaders(context, flow):
    """
        Called when the response headers for a server response have been received,
        but the response body has not been processed yet. Can be used to tell mitmproxy
        to stream the response.
    """
    context.log("responseheaders")

def response(context, flow):
    """
       Called when a server response has been received.
    """
    context.log("response")

def error(context, flow):
    """
        Called when a flow error has occured, e.g. invalid server responses, or
        interrupted connections. This is distinct from a valid server HTTP error
        response, which is simply a response with an HTTP error code.
    """
    context.log("error")

def clientdisconnect(context, conn_handler):
    """
        Called when a client disconnects from the proxy.
    """
    context.log("clientdisconnect")

def done(context):
    """
        Called once on script shutdown, after any other events.
    """
    context.log("done")
