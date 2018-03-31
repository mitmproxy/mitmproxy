import threading
import contextlib
import asyncio
import signal

from mitmproxy import addonmanager
from mitmproxy import options
from mitmproxy import controller
from mitmproxy import eventsequence
from mitmproxy import exceptions
from mitmproxy import command
from mitmproxy import http
from mitmproxy import websocket
from mitmproxy import log
from mitmproxy.net import server_spec
from mitmproxy.proxy.protocol import http_replay
from mitmproxy.coretypes import basethread

from . import ctx as mitmproxy_ctx


class ServerThread(basethread.BaseThread):
    def __init__(self, server):
        self.server = server
        address = getattr(self.server, "address", None)
        super().__init__(
            "ServerThread ({})".format(repr(address))
        )

    def run(self):
        self.server.serve_forever()


class Master:
    """
        The master handles mitmproxy's main event loop.
    """
    def __init__(self, opts):
        self.event_queue = asyncio.Queue()

        self.options = opts or options.Options()  # type: options.Options
        self.commands = command.CommandManager(self)
        self.addons = addonmanager.AddonManager(self)
        self.should_exit = threading.Event()
        self._server = None
        self.first_tick = True
        self.waiting_flows = []

    @property
    def server(self):
        return self._server

    @server.setter
    def server(self, server):
        server.set_channel(controller.Channel(asyncio.get_event_loop(), self.event_queue))
        self._server = server

    @contextlib.contextmanager
    def handlecontext(self):
        # Handlecontexts also have to nest - leave cleanup to the outermost
        if mitmproxy_ctx.master:
            yield
            return
        mitmproxy_ctx.master = self
        mitmproxy_ctx.log = log.Log(self)
        mitmproxy_ctx.options = self.options
        try:
            yield
        finally:
            mitmproxy_ctx.master = None
            mitmproxy_ctx.log = None
            mitmproxy_ctx.options = None

    def tell(self, mtype, m):
        m.reply = controller.DummyReply()
        self.event_queue.put((mtype, m))

    def add_log(self, e, level):
        """
            level: debug, alert, info, warn, error
        """
        self.addons.trigger("log", log.LogEntry(e, level))

    def start(self):
        self.should_exit.clear()
        if self.server:
            ServerThread(self.server).start()

    async def main(self):
        while True:
            if self.should_exit.is_set():
                return
            mtype, obj = await self.event_queue.get()
            if mtype not in eventsequence.Events:
                raise exceptions.ControlException(
                    "Unknown event %s" % repr(mtype)
                )
            self.addons.handle_lifecycle(mtype, obj)
            self.event_queue.task_done()

    async def tick(self):
        if self.first_tick:
            self.first_tick = False
            self.addons.trigger("running")
        while True:
            if self.should_exit.is_set():
                asyncio.get_event_loop().stop()
                return
            self.addons.trigger("tick")
            await asyncio.sleep(0.1)

    def run(self):
        self.start()
        asyncio.ensure_future(self.main())
        asyncio.ensure_future(self.tick())
        asyncio.get_event_loop().run_forever()
        self.shutdown()
        self.addons.trigger("done")

    def shutdown(self):
        if self.server:
            self.server.shutdown()
        self.should_exit.set()

    def _change_reverse_host(self, f):
        """
        When we load flows in reverse proxy mode, we adjust the target host to
        the reverse proxy destination for all flows we load. This makes it very
        easy to replay saved flows against a different host.
        """
        if self.options.mode.startswith("reverse:"):
            _, upstream_spec = server_spec.parse_with_mode(self.options.mode)
            f.request.host, f.request.port = upstream_spec.address
            f.request.scheme = upstream_spec.scheme

    def load_flow(self, f):
        """
        Loads a flow and links websocket & handshake flows
        """

        if isinstance(f, http.HTTPFlow):
            self._change_reverse_host(f)
            if 'websocket' in f.metadata:
                self.waiting_flows.append(f)

        if isinstance(f, websocket.WebSocketFlow):
            hf = [hf for hf in self.waiting_flows if hf.id == f.metadata['websocket_handshake']][0]
            f.handshake_flow = hf
            self.waiting_flows.remove(hf)
            self._change_reverse_host(f.handshake_flow)

        f.reply = controller.DummyReply()
        for e, o in eventsequence.iterate(f):
            self.addons.handle_lifecycle(e, o)

    def replay_request(
            self,
            f: http.HTTPFlow,
            block: bool=False
    ) -> http_replay.RequestReplayThread:
        """
        Replay a HTTP request to receive a new response from the server.

        Args:
            f: The flow to replay.
            block: If True, this function will wait for the replay to finish.
                This causes a deadlock if activated in the main thread.

        Returns:
            The thread object doing the replay.

        Raises:
            exceptions.ReplayException, if the flow is in a state
            where it is ineligible for replay.
        """

        if f.live:
            raise exceptions.ReplayException(
                "Can't replay live flow."
            )
        if f.intercepted:
            raise exceptions.ReplayException(
                "Can't replay intercepted flow."
            )
        if not f.request:
            raise exceptions.ReplayException(
                "Can't replay flow with missing request."
            )
        if f.request.raw_content is None:
            raise exceptions.ReplayException(
                "Can't replay flow with missing content."
            )

        f.backup()
        f.request.is_replay = True

        f.response = None
        f.error = None

        if f.request.http_version == "HTTP/2.0":  # https://github.com/mitmproxy/mitmproxy/issues/2197
            f.request.http_version = "HTTP/1.1"
            host = f.request.headers.pop(":authority")
            f.request.headers.insert(0, "host", host)

        rt = http_replay.RequestReplayThread(self.options, f, self.server.channel)
        rt.start()  # pragma: no cover
        if block:
            rt.join()
        return rt
