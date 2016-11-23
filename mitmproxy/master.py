import os
import threading
import contextlib
import queue
import sys

from mitmproxy import addonmanager
from mitmproxy import options
from mitmproxy import controller
from mitmproxy import events
from mitmproxy import exceptions
from mitmproxy import connections
from mitmproxy import http
from mitmproxy import log
from mitmproxy import io
from mitmproxy.proxy.protocol import http_replay
from mitmproxy.types import basethread
import mitmproxy.net.http

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
        with self.handlecontext():
            self.addons("log", log.LogEntry(e, level))

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
        with self.handlecontext():
            self.addons("tick")
        changed = False
        try:
            mtype, obj = self.event_queue.get(timeout=timeout)
            if mtype not in events.Events:
                raise exceptions.ControlException(
                    "Unknown event %s" % repr(mtype)
                )
            handle_func = getattr(self, mtype)
            if not callable(handle_func):
                raise exceptions.ControlException(
                    "Handler %s not callable" % mtype
                )
            if not handle_func.__dict__.get("__handler"):
                raise exceptions.ControlException(
                    "Handler function %s is not decorated with controller.handler" % (
                        handle_func
                    )
                )
            handle_func(obj)
            self.event_queue.task_done()
            changed = True
        except queue.Empty:
            pass
        return changed

    def shutdown(self):
        self.server.shutdown()
        self.should_exit.set()
        self.addons.done()

    def create_request(self, method, scheme, host, port, path):
        """
            this method creates a new artificial and minimalist request also adds it to flowlist
        """
        c = connections.ClientConnection.make_dummy(("", 0))
        s = connections.ServerConnection.make_dummy((host, port))

        f = http.HTTPFlow(c, s)
        headers = mitmproxy.net.http.Headers()

        req = http.HTTPRequest(
            "absolute",
            method,
            scheme,
            host,
            port,
            path,
            b"HTTP/1.1",
            headers,
            b""
        )
        f.request = req
        self.load_flow(f)
        return f

    def load_flow(self, f):
        """
        Loads a flow
        """
        if isinstance(f, http.HTTPFlow):
            if self.server and self.options.mode == "reverse":
                f.request.host = self.server.config.upstream_server.address.host
                f.request.port = self.server.config.upstream_server.address.port
                f.request.scheme = self.server.config.upstream_server.scheme
        f.reply = controller.DummyReply()
        for e, o in events.event_sequence(f):
            getattr(self, e)(o)

    def load_flows(self, fr: io.FlowReader) -> int:
        """
            Load flows from a FlowReader object.
        """
        cnt = 0
        for i in fr.stream():
            cnt += 1
            self.load_flow(i)
        return cnt

    def load_flows_file(self, path: str) -> int:
        path = os.path.expanduser(path)
        try:
            if path == "-":
                # This is incompatible with Python 3 - maybe we can use click?
                freader = io.FlowReader(sys.stdin)
                return self.load_flows(freader)
            else:
                with open(path, "rb") as f:
                    freader = io.FlowReader(f)
                    return self.load_flows(freader)
        except IOError as v:
            raise exceptions.FlowReadException(v.strerror)

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

    @controller.handler
    def log(self, l):
        pass

    @controller.handler
    def clientconnect(self, root_layer):
        pass

    @controller.handler
    def clientdisconnect(self, root_layer):
        pass

    @controller.handler
    def serverconnect(self, server_conn):
        pass

    @controller.handler
    def serverdisconnect(self, server_conn):
        pass

    @controller.handler
    def next_layer(self, top_layer):
        pass

    @controller.handler
    def http_connect(self, f):
        pass

    @controller.handler
    def error(self, f):
        pass

    @controller.handler
    def requestheaders(self, f):
        pass

    @controller.handler
    def request(self, f):
        pass

    @controller.handler
    def responseheaders(self, f):
        pass

    @controller.handler
    def response(self, f):
        pass

    @controller.handler
    def websocket_handshake(self, f):
        pass

    @controller.handler
    def websocket_start(self, flow):
        pass

    @controller.handler
    def websocket_message(self, flow):
        pass

    @controller.handler
    def websocket_error(self, flow):
        pass

    @controller.handler
    def websocket_end(self, flow):
        pass

    @controller.handler
    def tcp_start(self, flow):
        pass

    @controller.handler
    def tcp_message(self, flow):
        pass

    @controller.handler
    def tcp_error(self, flow):
        pass

    @controller.handler
    def tcp_end(self, flow):
        pass
