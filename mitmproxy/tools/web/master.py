import sys
import webbrowser
from typing import Optional

import tornado.httpserver
import tornado.ioloop
from mitmproxy import addons
from mitmproxy import exceptions
from mitmproxy import log
from mitmproxy import master
from mitmproxy import options
from mitmproxy.addons import eventstore
from mitmproxy.addons import intercept
from mitmproxy.addons import view
from mitmproxy.tools.web import app


class Options(options.Options):
    def __init__(
            self,
            *,  # all args are keyword-only.
            intercept: Optional[str] = None,
            wdebug: bool = False,
            wport: int = 8081,
            wiface: str = "127.0.0.1",
            **kwargs
    ) -> None:
        self.intercept = intercept
        self.wdebug = wdebug
        self.wport = wport
        self.wiface = wiface
        super().__init__(**kwargs)


class WebMaster(master.Master):
    def __init__(self, options, server):
        super().__init__(options, server)
        self.view = view.View()
        self.view.sig_view_add.connect(self._sig_view_add)
        self.view.sig_view_remove.connect(self._sig_view_remove)
        self.view.sig_view_update.connect(self._sig_view_update)
        self.view.sig_view_refresh.connect(self._sig_view_refresh)

        self.events = eventstore.EventStore()
        self.events.sig_add.connect(self._sig_events_add)
        self.events.sig_refresh.connect(self._sig_events_refresh)

        self.options.changed.connect(self._sig_options_update)

        self.addons.add(self.events, self.view, intercept.Intercept())
        self.addons.add(*addons.default_addons())
        self.app = app.Application(
            self, self.options.wdebug
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

    def _sig_view_remove(self, view, flow):
        app.ClientConnection.broadcast(
            resource="flows",
            cmd="remove",
            data=dict(id=flow.id)
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
        app.ClientConnection.broadcast(
            resource="settings",
            cmd="update",
            data={k: getattr(options, k) for k in updated}
        )

    def run(self):  # pragma: no cover

        iol = tornado.ioloop.IOLoop.instance()

        http_server = tornado.httpserver.HTTPServer(self.app)
        http_server.listen(self.options.wport, self.options.wiface)

        iol.add_callback(self.start)
        tornado.ioloop.PeriodicCallback(lambda: self.tick(timeout=0), 5).start()
        try:
            url = "http://{}:{}/".format(self.options.wiface, self.options.wport)
            print("Server listening at {}".format(url), file=sys.stderr)
            if not open_browser(url):
                print("No webbrowser found. Please open a browser and point it to {}".format(url))

            iol.start()
        except (KeyboardInterrupt):
            self.shutdown()


def open_browser(url: str) -> bool:
    """
    Open a URL in a browser window.
    In contrast to webbrowser.open, we limit the list of suitable browsers.
    This gracefully degrades to a no-op on headless servers, where webbrowser.open
    would otherwise open lynx.

    Returns:
        True, if a browser has been opened
        False, if no suitable browser has been found.
    """
    browsers = (
        "windows-default", "macosx",
        "google-chrome", "chrome", "chromium", "chromium-browser",
        "firefox", "opera", "safari",
    )
    for browser in browsers:
        try:
            b = webbrowser.get(browser)
        except webbrowser.Error:
            pass
        else:
            b.open(url)
            return True
    return False
