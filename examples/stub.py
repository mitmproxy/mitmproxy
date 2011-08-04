"""
    This is a script stub, with empty definitions for all events.
"""

def start(ctx):
    """
        Called once on script startup, before any other events.
    """
    pass

def clientconnect(ctx, client_connect):
    """
        Called when a client initiates a connection to the proxy. Note that a
        connection can correspond to multiple HTTP requests
    """
    pass

def request(ctx, flow):
    """
        Called when a client request has been received.
    """

def response(ctx, flow):
    """
       Called when a server response has been received.
    """
    pass

def error(ctx, flow):
    """
        Called when a flow error has occured, e.g. invalid server responses, or
        interrupted connections. This is distinct from a valid server HTTP error
        response, which is simply a response with an HTTP error code. 
    """
    pass

def clientdisconnect(ctx, client_disconnect):
    """
        Called when a client disconnects from the proxy.
    """
    pass

def done(ctx):
    """
        Called once on script shutdown, after any other events.
    """
    pass
