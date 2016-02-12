from __future__ import absolute_import, print_function
import collections
import tornado.ioloop
import tornado.httpserver

from netlib.http import authentication

from .. import controller, flow
from . import app


class Stop(Exception):
    pass


class WebFlowView(flow.FlowView):

    def __init__(self, store):
        super(WebFlowView, self).__init__(store, None)

    def _add(self, f):
        super(WebFlowView, self)._add(f)
        app.ClientConnection.broadcast(
            type="flows",
            cmd="add",
            data=app._strip_content(f.get_state())
        )

    def _update(self, f):
        super(WebFlowView, self)._update(f)
        app.ClientConnection.broadcast(
            type="flows",
            cmd="update",
            data=app._strip_content(f.get_state())
        )

    def _remove(self, f):
        super(WebFlowView, self)._remove(f)
        app.ClientConnection.broadcast(
            type="flows",
            cmd="remove",
            data=f.id
        )

    def _recalculate(self, flows):
        super(WebFlowView, self)._recalculate(flows)
        app.ClientConnection.broadcast(
            type="flows",
            cmd="reset"
        )


class WebState(flow.State):

    def __init__(self):
        super(WebState, self).__init__()
        self.view._close()
        self.view = WebFlowView(self.flows)

        self._last_event_id = 0
        self.events = collections.deque(maxlen=1000)

    def add_event(self, e, level):
        self._last_event_id += 1
        entry = {
            "id": self._last_event_id,
            "message": e,
            "level": level
        }
        self.events.append(entry)
        app.ClientConnection.broadcast(
            type="events",
            cmd="add",
            data=entry
        )

    def clear(self):
        super(WebState, self).clear()
        self.events.clear()
        app.ClientConnection.broadcast(
            type="events",
            cmd="reset",
            data=[]
        )


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
        "wauthenticator",
        "wsingleuser",
        "whtpasswd",
    ]

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        for i in self.attributes:
            if not hasattr(self, i):
                setattr(self, i, None)

    def process_web_options(self, parser):
        if self.wsingleuser or self.whtpasswd:
            if self.wsingleuser:
                if len(self.wsingleuser.split(':')) != 2:
                    return parser.error(
                        "Invalid single-user specification. Please use the format username:password"
                    )
                username, password = self.wsingleuser.split(':')
                self.wauthenticator = authentication.PassManSingleUser(username, password)
            elif self.whtpasswd:
                try:
                    self.wauthenticator = authentication.PassManHtpasswd(self.whtpasswd)
                except ValueError as v:
                    return parser.error(v.message)
        else:
            self.wauthenticator = None


class WebMaster(flow.FlowMaster):

    def __init__(self, server, options):
        self.options = options
        super(WebMaster, self).__init__(server, WebState())
        self.app = app.Application(self, self.options.wdebug, self.options.wauthenticator)
        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except flow.FlowReadError as v:
                self.add_event(
                    "Could not read flow file: %s" % v,
                    "error"
                )

        if options.outfile:
            err = self.start_stream_to_path(
                options.outfile[0],
                options.outfile[1]
            )
            if err:
                print >> sys.stderr, "Stream file error:", err
                sys.exit(1)

        if self.options.app:
            self.start_app(self.options.app_host, self.options.app_port)

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

    def _process_flow(self, f):
        if self.state.intercept and self.state.intercept(
                f) and not f.request.is_replay:
            f.intercept(self)
        else:
            f.reply()

    def handle_request(self, f):
        super(WebMaster, self).handle_request(f)
        self._process_flow(f)

    def handle_response(self, f):
        super(WebMaster, self).handle_response(f)
        self._process_flow(f)

    def handle_error(self, f):
        super(WebMaster, self).handle_error(f)
        self._process_flow(f)

    def add_event(self, e, level="info"):
        super(WebMaster, self).add_event(e, level)
        self.state.add_event(e, level)
