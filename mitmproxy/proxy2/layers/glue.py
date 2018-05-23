import asyncio
import io
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

"""
class GlueChannel:
    def __init__(self, server):
        self.server = server

    def ask(self, mtype, m):
        asyncio.get_event_loop().call_soon_threadsafe(
            lambda: self.server.server_event(
                GlueHook(
                    commands.Hook(mtype, m)
                )
            )
        )

    def tell(self, mtype, m):
        raise NotImplementedError()
"""


class GlueEvent(events.Event):
    def __init__(self, command: commands.Command):
        self.command = command


class GlueGetConnectionHandler(commands.Command):
    blocking = True


class GlueGetConnectionHandlerReply(events.CommandReply):
    pass


class GlueClientWfile(io.BufferedWriter):
    raw: io.BytesIO
    ch: server.ConnectionHandler
    loop: asyncio.AbstractEventLoop

    def __init__(self, ch, client, loop):
        self.ch = ch
        self.client = client
        self.loop = loop
        super().__init__(io.BytesIO())

    def flush(self, *args, **kwargs):
        super().flush()
        val = self.raw.getvalue()
        self.loop.call_soon_threadsafe(
            lambda: self.ch.server_event(GlueEvent(commands.SendData(
                self.client,
                val
            )))
        )
        self.raw.seek(0)
        self.raw.truncate()

    def __getattribute__(self, item):
        if GLUE_DEBUG and item not in ("raw", "loop", "ch", "client"):
            print(f"[client_conn.wfile] {item}")
        return super().__getattribute__(item)


class GlueClientConnection(connections.ClientConnection):
    def __init__(self, s: socket.socket, address, ch, client, loop):
        super().__init__(s, address, None)
        self.wfile = GlueClientWfile(ch, client, loop)

    def __getattribute__(self, item):
        if GLUE_DEBUG:
            print(f"[client_conn] {item}")
        return super().__getattribute__(item)


class GlueServerConnection(connections.ServerConnection):
    def __init__(self, s: socket.socket):
        super().__init__(s)

    def __getattribute__(self, item):
        if GLUE_DEBUG:
            print(f"[server_conn] {item}")
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
        # self.ctx = GlueTopLayerCtx(m)

    @property
    def __class__(self):
        return self.cls

    def __getattribute__(self, item):
        if GLUE_DEBUG and item not in ("root_context",):
            print(f"[top_layer] {item}")
        return object.__getattribute__(self, item)

    def __getattr__(self, item):
        return getattr(self.root_context, item)


"""
class GlueTopLayerCtx:
    def __init__(self, cls):
        self.cls = cls

    @property
    def __class__(self):
        return self.cls
"""


class GlueLayer(Layer):
    """
    Translate between old and new proxy core.
    """
    context: Context
    connection_handler: server.ConnectionHandler

    def log(self, msg, level):
        self.master.channel.tell("log", LogEntry(msg, level))

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        if GLUE_DEBUG:
            print("start!")
        loop = asyncio.get_event_loop()

        self.connection_handler = yield GlueGetConnectionHandler()
        self.master = ctx.master

        self.c1, self.c2 = socket.socketpair(socket.AF_INET)
        self.s1, self.s2 = socket.socketpair(socket.AF_INET)

        self.client_conn = GlueClientConnection(self.c1, self.context.client.address,
                                                self.connection_handler, self.context.client,
                                                loop)
        self.root_context = proxy.RootContext(
            self.client_conn,
            proxy.ProxyConfig(self.context.options),
            self.master.channel
        )

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
                self.c2.shutdown(socket.SHUT_RDWR)
                self.c2.close()
            else:
                raise NotImplementedError()
        yield from ()

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _):
        yield from ()
