import errno
import logging

import tornado.httpserver
import tornado.ioloop

from mitmproxy import addons
from mitmproxy import flow
from mitmproxy import log
from mitmproxy import master
from mitmproxy import options
from mitmproxy import optmanager
from mitmproxy.addons import errorcheck
from mitmproxy.addons import eventstore
from mitmproxy.addons import intercept
from mitmproxy.addons import readfile
from mitmproxy.addons import view
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.tools.web import app
from mitmproxy.tools.web import static_viewer
from mitmproxy.tools.web import webaddons

logger = logging.getLogger(__name__)


class WebMaster(master.Master):
    def __init__(self, opts: options.Options, with_termlog: bool = True):
        super().__init__(opts, with_termlog=with_termlog)
        self.view = view.View()
        self.view.sig_view_add.connect(self._sig_view_add)
        self.view.sig_view_remove.connect(self._sig_view_remove)
        self.view.sig_view_update.connect(self._sig_view_update)
        self.view.sig_view_refresh.connect(self._sig_view_refresh)

        self.events = eventstore.EventStore()
        self.events.sig_add.connect(self._sig_events_add)
        self.events.sig_refresh.connect(self._sig_events_refresh)

        self.options.changed.connect(self._sig_options_update)

        self.addons.add(*addons.default_addons())
        self.addons.add(
            webaddons.WebAddon(),
            intercept.Intercept(),
            readfile.ReadFileStdin(),
            static_viewer.StaticViewer(),
            self.view,
            self.events,
            errorcheck.ErrorCheck(),
        )
        self.app = app.Application(self, self.options.web_debug)
        self.proxyserver: Proxyserver = self.addons.get("proxyserver")
        self.proxyserver.servers.changed.connect(self._sig_servers_changed)

    def _sig_view_add(self, flow: flow.Flow) -> None:
        app.ClientConnection.broadcast(
            resource="flows", cmd="add", data=app.flow_to_json(flow)
        )

    def _sig_view_update(self, flow: flow.Flow) -> None:
        app.ClientConnection.broadcast(
            resource="flows", cmd="update", data=app.flow_to_json(flow)
        )

    def _sig_view_remove(self, flow: flow.Flow, index: int) -> None:
        app.ClientConnection.broadcast(resource="flows", cmd="remove", data=flow.id)

    def _sig_view_refresh(self) -> None:
        app.ClientConnection.broadcast(resource="flows", cmd="reset")

    def _sig_events_add(self, entry: log.LogEntry) -> None:
        app.ClientConnection.broadcast(
            resource="events", cmd="add", data=app.logentry_to_json(entry)
        )

    def _sig_events_refresh(self) -> None:
        app.ClientConnection.broadcast(resource="events", cmd="reset")

    def _sig_options_update(self, updated: set[str]) -> None:
        options_dict = optmanager.dump_dicts(self.options, updated)
        app.ClientConnection.broadcast(
            resource="options", cmd="update", data=options_dict
        )

    def _sig_servers_changed(self) -> None:
        app.ClientConnection.broadcast(
            resource="state",
            cmd="update",
            data={"servers": [s.to_json() for s in self.proxyserver.servers]},
        )

    async def running(self):
        # Register tornado with the current event loop
        tornado.ioloop.IOLoop.current()

        # Add our web app.
        http_server = tornado.httpserver.HTTPServer(
            self.app, max_buffer_size=2**32
        )  # 4GB
        try:
            http_server.listen(self.options.web_port, self.options.web_host)
        except OSError as e:
            message = f"Web server failed to listen on {self.options.web_host or '*'}:{self.options.web_port} with {e}"
            if e.errno == errno.EADDRINUSE:
                message += f"\nTry specifying a different port by using `--set web_port={self.options.web_port + 2}`."
            raise OSError(e.errno, message, e.filename) from e

        logger.info(
            f"Web server listening at http://{self.options.web_host}:{self.options.web_port}/",
        )

        return await super().running()
