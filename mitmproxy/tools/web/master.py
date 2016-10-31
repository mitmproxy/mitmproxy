import sys

import tornado.httpserver
import tornado.ioloop

from typing import Optional

from mitmproxy import addons
from mitmproxy import exceptions
from mitmproxy.addons import view
from mitmproxy.addons import intercept
from mitmproxy import options
from mitmproxy import master
from mitmproxy.tools.web import app
from mitmproxy.net.http import authentication


class Stop(Exception):
    pass


class _WebState():
    def add_log(self, e, level):
        # server-side log ids are odd
        self._last_event_id += 2
        entry = {
            "id": self._last_event_id,
            "message": e,
            "level": level
        }
        self.events.append(entry)
        app.ClientConnection.broadcast(
            resource="events",
            cmd="add",
            data=entry
        )

    def clear(self):
        super().clear()
        self.events.clear()
        app.ClientConnection.broadcast(
            resource="events",
            cmd="reset"
        )


class Options(options.Options):
    def __init__(
            self,
            *,  # all args are keyword-only.
            intercept: Optional[str] = None,
            wdebug: bool = False,
            wport: int = 8081,
            wiface: str = "127.0.0.1",
            wauthenticator: Optional[authentication.PassMan] = None,
            wsingleuser: Optional[str] = None,
            whtpasswd: Optional[str] = None,
            **kwargs
    ):
        self.wdebug = wdebug
        self.wport = wport
        self.wiface = wiface
        self.wauthenticator = wauthenticator
        self.wsingleuser = wsingleuser
        self.whtpasswd = whtpasswd
        self.intercept = intercept
        super().__init__(**kwargs)

    # TODO: This doesn't belong here.
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


class WebMaster(master.Master):

    def __init__(self, options, server):
        super().__init__(options, server)
        self.view = view.View()
        self.view.sig_add.connect(self._sig_add)
        self.view.sig_remove.connect(self._sig_remove)
        self.view.sig_update.connect(self._sig_update)
        self.view.sig_refresh.connect(self._sig_refresh)

        self.addons.add(*addons.default_addons())
        self.addons.add(self.view, intercept.Intercept())
        self.app = app.Application(
            self, self.options.wdebug, self.options.wauthenticator
        )
        # This line is just for type hinting
        self.options = self.options  # type: Options
        if options.rfile:
            try:
                self.load_flows_file(options.rfile)
            except exceptions.FlowReadException as v:
                self.add_log(
                    "Could not read flow file: %s" % v,
                    "error"
                )

    def _sig_add(self, view, flow):
        app.ClientConnection.broadcast(
            resource="flows",
            cmd="add",
            data=app.convert_flow_to_json_dict(flow)
        )

    def _sig_update(self, view, flow):
        app.ClientConnection.broadcast(
            resource="flows",
            cmd="update",
            data=app.convert_flow_to_json_dict(flow)
        )

    def _sig_remove(self, view, flow):
        app.ClientConnection.broadcast(
            resource="flows",
            cmd="remove",
            data=dict(id=flow.id)
        )

    def _sig_refresh(self, view):
        app.ClientConnection.broadcast(
            resource="flows",
            cmd="reset"
        )

    def run(self):  # pragma: no cover

        iol = tornado.ioloop.IOLoop.instance()

        http_server = tornado.httpserver.HTTPServer(self.app)
        http_server.listen(self.options.wport)

        iol.add_callback(self.start)
        tornado.ioloop.PeriodicCallback(lambda: self.tick(timeout=0), 5).start()
        try:
            print("Server listening at http://{}:{}".format(
                self.options.wiface, self.options.wport), file=sys.stderr)
            iol.start()
        except (Stop, KeyboardInterrupt):
            self.shutdown()

    # def add_log(self, e, level="info"):
    #     super().add_log(e, level)
    #     return self.state.add_log(e, level)
