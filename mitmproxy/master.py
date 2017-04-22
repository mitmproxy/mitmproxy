import threading
import contextlib
import queue

from mitmproxy import addonmanager
from mitmproxy import options
from mitmproxy import controller
from mitmproxy import eventsequence
from mitmproxy import exceptions
from mitmproxy import connections
from mitmproxy import http
from mitmproxy import log
from mitmproxy.proxy.protocol import http_replay
from mitmproxy.types import basethread

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
    def __init__(self, opts, server):
        self.options = opts or options.Options()
        self.addons = addonmanager.AddonManager(self)
        self.event_queue = queue.Queue()
        self.should_exit = threading.Event()
        self.server = server
        self.first_tick = True
        channel = controller.Channel(self.event_queue, self.should_exit)
        server.set_channel(channel)

    @contextlib.contextmanager
    def handlecontext(self):
        # Handlecontexts also have to nest - leave cleanup to the outermost
        if mitmproxy_ctx.master:
            yield
            return
        mitmproxy_ctx.master = self
        mitmproxy_ctx.log = log.Log(self)
        try:
            yield
        finally:
            mitmproxy_ctx.master = None
            mitmproxy_ctx.log = None

    def tell(self, mtype, m):
        m.reply = controller.DummyReply()
        self.event_queue.put((mtype, m))

    def add_log(self, e, level):
        """
            level: debug, info, warn, error
        """
        self.addons.trigger("log", log.LogEntry(e, level))

    def start(self):
        self.should_exit.clear()
        ServerThread(self.server).start()

    def run(self):
        self.start()
        try:
            while not self.should_exit.is_set():
                # Don't choose a very small timeout in Python 2:
                # https://github.com/mitmproxy/mitmproxy/issues/443
                # TODO: Lower the timeout value if we move to Python 3.
                self.tick(0.1)
        finally:
            self.shutdown()

    def tick(self, timeout):
        if self.first_tick:
            self.first_tick = False
            self.addons.trigger("running")
        self.addons.trigger("tick")
        changed = False
        try:
            mtype, obj = self.event_queue.get(timeout=timeout)
            if mtype not in eventsequence.Events:
                raise exceptions.ControlException(
                    "Unknown event %s" % repr(mtype)
                )
            self.addons.handle_lifecycle(mtype, obj)
            self.event_queue.task_done()
            changed = True
        except queue.Empty:
            pass
        return changed

    def shutdown(self):
        self.server.shutdown()
        self.should_exit.set()
        self.addons.trigger("done")

    def create_request(self, method, url):
        """
        Create a new artificial and minimalist request also adds it to flowlist.

        Raises:
            ValueError, if the url is malformed.
        """
        req = http.HTTPRequest.make(method, url)
        c = connections.ClientConnection.make_dummy(("", 0))
        s = connections.ServerConnection.make_dummy((req.host, req.port))

        f = http.HTTPFlow(c, s)
        f.request = req
        self.load_flow(f)
        return f

    def load_flow(self, f):
        """
        Loads a flow
        """
        if isinstance(f, http.HTTPFlow):
            if self.server and self.options.mode.startswith("reverse:"):
                f.request.host = self.server.config.upstream_server.address[0]
                f.request.port = self.server.config.upstream_server.address[1]
                f.request.scheme = self.server.config.upstream_server.scheme
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
        if f.request.raw_content is None:
            raise exceptions.ReplayException(
                "Can't replay flow with missing content."
            )
        if not f.request:
            raise exceptions.ReplayException(
                "Can't replay flow with missing request."
            )

        f.backup()
        f.request.is_replay = True

        f.response = None
        f.error = None

        rt = http_replay.RequestReplayThread(
            self.server.config,
            f,
            self.event_queue,
            self.should_exit
        )
        rt.start()  # pragma: no cover
        if block:
            rt.join()
        return rt
