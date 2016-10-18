from mitmproxy import ctx

from netlib import wsgi
from netlib import version


class WSGIApp:
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
            ctx.log.warn("Error in wsgi app. %s" % err, "error")
        flow.reply.kill()

    def request(self, f):
        if (f.request.pretty_host, f.request.port) == (self.host, self.port):
            self.serve(self.app, f)
