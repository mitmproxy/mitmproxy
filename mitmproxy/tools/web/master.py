import tornado.httpserver
import tornado.ioloop
from tornado.platform.asyncio import AsyncIOMainLoop

from mitmproxy import addons
from mitmproxy import log
from mitmproxy import master
from mitmproxy import optmanager
from mitmproxy.addons import eventstore
from mitmproxy.addons import intercept
from mitmproxy.addons import readfile
from mitmproxy.addons import termlog
from mitmproxy.addons import view
from mitmproxy.tools.web import app, webaddons, static_viewer


class WebMaster(master.Master):
    def __init__(self, options, with_termlog=True):
        super().__init__(options)
        self.view = view.View()
        self.view.sig_view_add.connect(self._sig_view_add)
        self.view.sig_view_remove.connect(self._sig_view_remove)
        self.view.sig_view_update.connect(self._sig_view_update)
        self.view.sig_view_refresh.connect(self._sig_view_refresh)

        self.events = eventstore.EventStore()
        self.events.sig_add.connect(self._sig_events_add)
        self.events.sig_refresh.connect(self._sig_events_refresh)

        self.options.changed.connect(self._sig_options_update)
        self.options.changed.connect(self._sig_settings_update)

        self.addons.add(*addons.default_addons())
        self.addons.add(
            webaddons.WebAddon(),
            intercept.Intercept(),
            readfile.ReadFile(),
            static_viewer.StaticViewer(),
            self.view,
            self.events,
        )
        if with_termlog:
            self.addons.add(termlog.TermLog())
        self.app = app.Application(
            self, self.options.web_debug
        )

    def _sig_view_add(self, view, flow):
        app.ClientConnection.broadcast(
            resource="flows",
            cmd="add",
            data=app.flow_to_json(flow)
        )

    def _sig_view_update(self, view, flow):
        app.ClientConnection.broadcast(
            resource="flows",
            cmd="update",
            data=app.flow_to_json(flow)
        )

    def _sig_view_remove(self, view, flow, index):
        app.ClientConnection.broadcast(
            resource="flows",
            cmd="remove",
            data=flow.id
        )

    def _sig_view_refresh(self, view):
        app.ClientConnection.broadcast(
            resource="flows",
            cmd="reset"
        )

    def _sig_events_add(self, event_store, entry: log.LogEntry):
        app.ClientConnection.broadcast(
            resource="events",
            cmd="add",
            data=app.logentry_to_json(entry)
        )

    def _sig_events_refresh(self, event_store):
        app.ClientConnection.broadcast(
            resource="events",
            cmd="reset"
        )

    def _sig_options_update(self, options, updated):
        options_dict = optmanager.dump_dicts(options, updated)
        app.ClientConnection.broadcast(
            resource="options",
            cmd="update",
            data=options_dict
        )

    def _sig_settings_update(self, options, updated):
        app.ClientConnection.broadcast(
            resource="settings",
            cmd="update",
            data={k: getattr(options, k) for k in updated}
        )

    def run(self):  # pragma: no cover
        AsyncIOMainLoop().install()
        iol = tornado.ioloop.IOLoop.instance()
        http_server = tornado.httpserver.HTTPServer(self.app)
        http_server.listen(self.options.web_port, self.options.web_host)
        web_url = f"http://{self.options.web_host}:{self.options.web_port}/"
        self.log.info(
            f"Web server listening at {web_url}",
        )
        self.run_loop(iol.start)
