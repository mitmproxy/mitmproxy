from __future__ import absolute_import, print_function, division

import sys
import collections

import tornado.httpserver
import tornado.ioloop

from typing import Optional  # noqa

from mitmproxy import builtins
from mitmproxy import controller
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import options
from mitmproxy.web import app
from netlib.http import authentication


class Stop(Exception):
    pass


class WebFlowView(flow.FlowView):

    def __init__(self, store):
        super(WebFlowView, self).__init__(store, None)

    def _add(self, f):
        super(WebFlowView, self)._add(f)
        app.ClientConnection.broadcast(
            type="UPDATE_FLOWS",
            cmd="add",
            data=app.convert_flow_to_json_dict(f)
        )

    def _update(self, f):
        super(WebFlowView, self)._update(f)
        app.ClientConnection.broadcast(
            type="UPDATE_FLOWS",
            cmd="update",
            data=app.convert_flow_to_json_dict(f)
        )

    def _remove(self, f):
        super(WebFlowView, self)._remove(f)
        app.ClientConnection.broadcast(
            type="UPDATE_FLOWS",
            cmd="remove",
            data=dict(id=f.id)
        )

    def _recalculate(self, flows):
        super(WebFlowView, self)._recalculate(flows)
        app.ClientConnection.broadcast(
            type="UPDATE_FLOWS",
            cmd="reset"
        )


class WebState(flow.State):

    def __init__(self):
        super(WebState, self).__init__()
        self.view._close()
        self.view = WebFlowView(self.flows)

        self._last_event_id = 0
        self.events = collections.deque(maxlen=1000)

    def add_log(self, e, level):
        self._last_event_id += 1
        entry = {
            "id": self._last_event_id,
            "message": e,
            "level": level
        }
        self.events.append(entry)
        app.ClientConnection.broadcast(
            type="UPDATE_EVENTLOG",
            cmd="add",
            data=entry
        )

    def clear(self):
        super(WebState, self).clear()
        self.events.clear()
        app.ClientConnection.broadcast(
            type="UPDATE_EVENTLOG",
            cmd="reset",
            data=[]
        )


class Options(options.Options):
    def __init__(
            self,
            intercept=None,  # type: Optional[str]
            wdebug=bool,  # type: bool
            wport=8081,  # type: int
            wiface="127.0.0.1",  # type: str
            wauthenticator=None,  # type: Optional[authentication.PassMan]
            wsingleuser=None,  # type: Optional[str]
            whtpasswd=None,  # type: Optional[str]
            **kwargs
    ):
        self.wdebug = wdebug
        self.wport = wport
        self.wiface = wiface
        self.wauthenticator = wauthenticator
        self.wsingleuser = wsingleuser
        self.whtpasswd = whtpasswd
        self.intercept = intercept
        super(Options, self).__init__(**kwargs)

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


class WebMaster(flow.FlowMaster):

    def __init__(self, server, options):
        super(WebMaster, self).__init__(options, server, WebState())
        self.addons.add(*builtins.default_addons())
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

        if options.outfile:
            err = self.start_stream_to_path(
                options.outfile[0],
                options.outfile[1]
            )
            if err:
                print("Stream file error: {}".format(err), file=sys.stderr)
                sys.exit(1)

        if self.options.app:
            self.start_app(self.options.app_host, self.options.app_port)

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

    def _process_flow(self, f):
        if self.state.intercept and self.state.intercept(
                f) and not f.request.is_replay:
            f.intercept(self)
        return f

    @controller.handler
    def request(self, f):
        super(WebMaster, self).request(f)
        return self._process_flow(f)

    @controller.handler
    def response(self, f):
        super(WebMaster, self).response(f)
        return self._process_flow(f)

    @controller.handler
    def error(self, f):
        super(WebMaster, self).error(f)
        return self._process_flow(f)

    def add_log(self, e, level="info"):
        super(WebMaster, self).add_log(e, level)
        return self.state.add_log(e, level)
