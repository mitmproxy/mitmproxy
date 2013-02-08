"""
    This is a script stub, with definitions for all events.
"""

def start(ctx):
    """
        Called once on script startup, before any other events.
    """
    ctx.log("start")

def clientconnect(ctx, client_connect):
    """
        Called when a client initiates a connection to the proxy. Note that a
        connection can correspond to multiple HTTP requests
    """
    ctx.log("clientconnect")

def request(ctx, flow):
    """
        Called when a client request has been received.
    """
    ctx.log("request")

def response(ctx, flow):
    """
       Called when a server response has been received.
    """
    ctx.log("response")

def error(ctx, flow):
    """
        Called when a flow error has occured, e.g. invalid server responses, or
        interrupted connections. This is distinct from a valid server HTTP error
        response, which is simply a response with an HTTP error code.
    """
    ctx.log("error")

def clientdisconnect(ctx, client_disconnect):
    """
        Called when a client disconnects from the proxy.
    """
    ctx.log("clientdisconnect")

def done(ctx):
    """
        Called once on script shutdown, after any other events.
    """
    ctx.log("done")
