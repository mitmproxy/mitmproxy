from __future__ import absolute_import, print_function
import tornado.ioloop
import tornado.httpserver
from .. import controller, flow
from . import app


class Stop(Exception):
    pass


class WebState(flow.State):
    def __init__(self):
        flow.State.__init__(self)


class Options(object):
    attributes = [
        "app",
        "app_domain",
        "app_ip",
        "anticache",
        "anticomp",
        "client_replay",
        "eventlog",
        "keepserving",
        "kill",
        "intercept",
        "no_server",
        "refresh_server_playback",
        "rfile",
        "scripts",
        "showhost",
        "replacements",
        "rheaders",
        "setheaders",
        "server_replay",
        "stickycookie",
        "stickyauth",
        "stream_large_bodies",
        "verbosity",
        "wfile",
        "nopop",

        "wdebug",
        "wport",
        "wiface",
    ]

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.attributes:
            if not hasattr(self, i):
                setattr(self, i, None)


class WebMaster(flow.FlowMaster):
    def __init__(self, server, options):
        self.options = options
        self.app = app.Application(self.options.wdebug)
        super(WebMaster, self).__init__(server, WebState())

        self.last_log_id = 0

    def tick(self):
        flow.FlowMaster.tick(self, self.masterq, timeout=0)

    def run(self):  # pragma: no cover
        self.server.start_slave(
            controller.Slave,
            controller.Channel(self.masterq, self.should_exit)
        )
        iol = tornado.ioloop.IOLoop.instance()

        http_server = tornado.httpserver.HTTPServer(self.app)
        http_server.listen(self.options.wport)

        tornado.ioloop.PeriodicCallback(self.tick, 5).start()
        try:
            iol.start()
        except (Stop, KeyboardInterrupt):
            self.shutdown()

    def handle_request(self, f):
        app.ClientConnection.broadcast("add_flow", f.get_state(True))
        flow.FlowMaster.handle_request(self, f)
        if f:
            f.reply()
        return f

    def handle_response(self, f):
        app.ClientConnection.broadcast("update_flow", f.get_state(True))
        flow.FlowMaster.handle_response(self, f)
        if f:
            f.reply()
        return f

    def handle_error(self, f):
        app.ClientConnection.broadcast("update_flow", f.get_state(True))
        flow.FlowMaster.handle_error(self, f)
        return f

    def handle_log(self, l):
        self.last_log_id += 1
        app.ClientConnection.broadcast(
            "add_event", {
                "id": self.last_log_id,
                "message": l.msg,
                "level": l.level
            }
        )
        self.add_event(l.msg, l.level)
        l.reply()

