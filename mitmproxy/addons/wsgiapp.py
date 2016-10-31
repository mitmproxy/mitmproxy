from mitmproxy import ctx
from mitmproxy import exceptions

from mitmproxy.net import wsgi
from mitmproxy import version


class WSGIApp:
    """
        An addon that hosts a WSGI app withing mitproxy, at a specified
        hostname and port.
    """
    def __init__(self, app, host, port):
        self.app, self.host, self.port = app, host, port

    def serve(self, app, flow):
        """
            Serves app on flow, and prevents further handling of the flow.
        """
        app = wsgi.WSGIAdaptor(
            app,
            flow.request.pretty_host,
            flow.request.port,
            version.MITMPROXY
        )
        err = app.serve(
            flow,
            flow.client_conn.wfile,
            **{"mitmproxy.master": ctx.master}
        )
        if err:
            ctx.log.error("Error in wsgi app. %s" % err)
            raise exceptions.AddonHalt()
        flow.reply.kill()

    def request(self, f):
        if (f.request.pretty_host, f.request.port) == (self.host, self.port):
            self.serve(self.app, f)
