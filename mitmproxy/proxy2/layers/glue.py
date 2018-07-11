import asyncio
import socket
import sys
import threading
import traceback

from mitmproxy import proxy, connections, ctx, exceptions, http
from mitmproxy.log import LogEntry
from mitmproxy.net.http import http1
from mitmproxy.proxy import modes
from mitmproxy.proxy.protocol import ServerConnectionMixin
from mitmproxy.proxy2 import commands, events, server
from mitmproxy.proxy2.context import Context
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.utils import expect

"""
   ___
   ###        __    __   __    __   __    __    ®
  /---\      |  |  |  | |  |  |  | |  |  |  |
 |     |     |  |  |  | |  |__|  | |  |  |  |
 |     |     |  |  |  | |   __   | |  |  |  |
 |     |     |  `--'  | |  |  |  | |  `--'  |
 |     |      \______/  |__|  |__|  \______/
 +++++++

Temporary glue code to connect the old thread-based proxy core and the new sans-io implementation.
"""

GLUE_DEBUG = False


class GlueEvent(events.Event):
    def __init__(self, command: commands.Command):
        self.command = command


class GlueGetConnectionHandler(commands.Command):
    blocking = True


class GlueGetConnectionHandlerReply(events.CommandReply):
    pass


class GlueClientConnection(connections.ClientConnection):
    def __init__(self, s: socket.socket, address):
        super().__init__(s, address, None)

    def __getattribute__(self, item):
        if GLUE_DEBUG:
            print(f"[client_conn] {item}")
        return super().__getattribute__(item)


class GlueTopLayer(ServerConnectionMixin):
    root_context: proxy.RootContext

    def __init__(self, ctx, server_address):
        self.root_context = ctx
        super().__init__(server_address)
        mode = self.root_context.config.options.mode
        if mode.startswith("upstream:"):
            m = modes.HttpUpstreamProxy
        elif mode == "transparent":
            m = modes.TransparentProxy
        elif mode.startswith("reverse:"):
            m = modes.ReverseProxy
        elif mode == "socks5":
            m = modes.Socks5Proxy
        elif mode == "regular":
            m = modes.HttpProxy
        else:
            raise NotImplementedError()
        self.cls = m

    @property
    def __class__(self):
        return self.cls

    def __getattribute__(self, item):
        if GLUE_DEBUG and item not in ("root_context",):
            print(f"[top_layer] {item}")
        return object.__getattribute__(self, item)

    def __getattr__(self, item):
        return getattr(self.root_context, item)


class GlueLayer(Layer):
    """
    Translate between old and new proxy core.
    """
    context: Context
    connection_handler: server.ConnectionHandler

    def log(self, msg, level):
        self.master.channel.tell("log", LogEntry(msg, level))

    def _inject(self, command: commands.Command):
        e = GlueEvent(command)
        self.loop.call_soon_threadsafe(
            lambda: self.connection_handler.server_event(e)
        )

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        if GLUE_DEBUG:
            print("start!")
        self.loop = asyncio.get_event_loop()

        self.connection_handler = yield GlueGetConnectionHandler()
        self.master = ctx.master

        self.c1, self.c2 = socketpair()

        self.client_conn = GlueClientConnection(self.c1, self.context.client.address)
        self.root_context = proxy.RootContext(
            self.client_conn,
            proxy.ProxyConfig(self.context.options),
            self.master.channel
        )

        def spin():
            while True:
                d = self.c2.recv(16384)
                if not d:
                    break
                self._inject(commands.SendData(self.context.client, d))

        self.spin = threading.Thread(target=spin)
        self.spin.daemon = True
        self.spin.start()

        def run():
            try:
                self.layer = self.root_context.next_layer(
                    GlueTopLayer(self.root_context, self.context.server.address)
                )
                self.layer()
            except exceptions.Kill:
                self.log("Connection killed", "info")
            except exceptions.ProtocolException as e:
                if isinstance(e, exceptions.ClientHandshakeException):
                    self.log(
                        "Client Handshake failed. "
                        "The client may not trust the proxy's certificate for {}.".format(e.server),
                        "warn"
                    )
                    self.log(repr(e), "debug")
                elif isinstance(e, exceptions.InvalidServerCertificate):
                    self.log(str(e), "warn")
                    self.log(
                        "Invalid certificate, closing connection. Pass --insecure to disable validation.",
                        "warn")
                else:
                    self.log(str(e), "warn")

                    self.log(repr(e), "debug")
                # If an error propagates to the topmost level,
                # we send an HTTP error response, which is both
                # understandable by HTTP clients and humans.
                try:
                    error_response = http.make_error_response(502, repr(e))
                    self.client_conn.send(http1.assemble_response(error_response))
                except exceptions.TcpException:
                    pass
            except Exception:
                self.log(traceback.format_exc(), "error")
                print(traceback.format_exc(), file=sys.stderr)
                print("mitmproxy has crashed!", file=sys.stderr)
                print("Please lodge a bug report at: https://github.com/mitmproxy/mitmproxy",
                      file=sys.stderr)

        self.thread = threading.Thread(target=run)

        self._handle_event = self.translate_event

        self.thread.start()
        if GLUE_DEBUG:
            print("done start")

    _handle_event = start

    @expect(events.DataReceived, events.ConnectionClosed, GlueEvent)
    def translate_event(self, event: events.Event) -> commands.TCommandGenerator:
        if GLUE_DEBUG:
            print("event!", event)
        if isinstance(event, events.DataReceived):
            if event.connection == self.context.client:
                self.c2.sendall(event.data)
            else:
                raise NotImplementedError()
        elif isinstance(event, GlueEvent):
            yield event.command
        elif isinstance(event, events.ConnectionClosed):
            if event.connection == self.context.client:
                self.c1.shutdown(socket.SHUT_RDWR)
                self.c1.close()
                self.c2.shutdown(socket.SHUT_RDWR)
                self.c2.close()
                self._handle_event = self.done
            else:
                raise NotImplementedError()
        yield from ()

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _):
        yield from ()


# https://github.com/python/cpython/blob/5c23e21ef655db35af45ed98a62eb54bff64dbd0/Lib/socket.py#L493
def socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
    if family == socket.AF_INET:
        host = socket._LOCALHOST
    elif family == socket.AF_INET6:
        host = socket._LOCALHOST_V6
    else:
        raise ValueError("Only AF_INET and AF_INET6 socket address families "
                         "are supported")
    if type != socket.SOCK_STREAM:
        raise ValueError("Only SOCK_STREAM socket type is supported")
    if proto != 0:
        raise ValueError("Only protocol zero is supported")

    # We create a connected TCP socket. Note the trick with
    # setblocking(False) that prevents us from having to create a thread.
    lsock = socket.socket(family, type, proto)
    try:
        lsock.bind((host, 0))
        lsock.listen()
        # On IPv6, ignore flow_info and scope_id
        addr, port = lsock.getsockname()[:2]
        csock = socket.socket(family, type, proto)
        try:
            csock.setblocking(False)
            try:
                csock.connect((addr, port))
            except (BlockingIOError, InterruptedError):
                pass
            csock.setblocking(True)
            ssock, _ = lsock.accept()
        except:
            csock.close()
            raise
    finally:
        lsock.close()
    return (ssock, csock)
