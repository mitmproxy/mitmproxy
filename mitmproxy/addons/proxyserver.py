import asyncio
import warnings
from typing import Dict, Optional, Tuple

from mitmproxy import command, controller, ctx, exceptions, flow, http, log, master, options, platform, tcp, websocket
from mitmproxy.flow import Error, Flow
from mitmproxy.proxy import commands, events, server_hooks
from mitmproxy.proxy import server
from mitmproxy.proxy.layers.tcp import TcpMessageInjected
from mitmproxy.proxy.layers.websocket import WebSocketMessageInjected
from mitmproxy.utils import asyncio_utils, human
from wsproto.frame_protocol import Opcode


class AsyncReply(controller.Reply):
    """
    controller.Reply.q.get() is blocking, which we definitely want to avoid in a coroutine.
    This stub adds a .done asyncio.Event() that can be used instead.
    """

    def __init__(self, *args):
        self.done = asyncio.Event()
        self.loop = asyncio.get_event_loop()
        super().__init__(*args)

    def commit(self):
        super().commit()
        try:
            self.loop.call_soon_threadsafe(lambda: self.done.set())
        except RuntimeError:  # pragma: no cover
            pass  # event loop may already be closed.

    def kill(self, force=False):  # pragma: no cover
        warnings.warn("reply.kill() is deprecated, set the error attribute instead.", DeprecationWarning, stacklevel=2)
        self.obj.error = flow.Error(Error.KILLED_MESSAGE)


class ProxyConnectionHandler(server.StreamConnectionHandler):
    master: master.Master

    def __init__(self, master, r, w, options):
        self.master = master
        super().__init__(r, w, options)
        self.log_prefix = f"{human.format_address(self.client.peername)}: "

    async def handle_hook(self, hook: commands.StartHook) -> None:
        with self.timeout_watchdog.disarm():
            # We currently only support single-argument hooks.
            data, = hook.args()
            data.reply = AsyncReply(data)
            await self.master.addons.handle_lifecycle(hook)
            await data.reply.done.wait()
            data.reply = None

    def log(self, message: str, level: str = "info") -> None:
        x = log.LogEntry(self.log_prefix + message, level)
        x.reply = controller.DummyReply()  # type: ignore
        asyncio_utils.create_task(
            self.master.addons.handle_lifecycle(log.AddLogHook(x)),
            name="ProxyConnectionHandler.log"
        )


class Proxyserver:
    """
    This addon runs the actual proxy server.
    """
    server: Optional[asyncio.AbstractServer]
    listen_port: int
    master: master.Master
    options: options.Options
    is_running: bool
    _connections: Dict[Tuple, ProxyConnectionHandler]

    def __init__(self):
        self._lock = asyncio.Lock()
        self.server = None
        self.is_running = False
        self._connections = {}

    def __repr__(self):
        return f"ProxyServer({'running' if self.server else 'stopped'}, {len(self._connections)} active conns)"

    def load(self, loader):
        loader.add_option(
            "connection_strategy", str, "eager",
            "Determine when server connections should be established. When set to lazy, mitmproxy "
            "tries to defer establishing an upstream connection as long as possible. This makes it possible to "
            "use server replay while being offline. When set to eager, mitmproxy can detect protocols with "
            "server-side greetings, as well as accurately mirror TLS ALPN negotiation.",
            choices=("eager", "lazy")
        )
        loader.add_option(
            "stream_large_bodies", Optional[str], None,
            """
            Stream data to the client if response body exceeds the given
            threshold. If streamed, the body will not be stored in any way.
            Understands k/m/g suffixes, i.e. 3m for 3 megabytes.
            """
        )
        loader.add_option(
            "body_size_limit", Optional[str], None,
            """
            Byte size limit of HTTP request and response bodies. Understands
            k/m/g suffixes, i.e. 3m for 3 megabytes.
            """
        )
        loader.add_option(
            "keep_host_header", bool, False,
            """
            Reverse Proxy: Keep the original host header instead of rewriting it
            to the reverse proxy target.
            """
        )
        loader.add_option(
            "proxy_debug", bool, False,
            "Enable debug logs in the proxy core.",
        )

    def running(self):
        self.master = ctx.master
        self.options = ctx.options
        self.is_running = True
        self.configure(["listen_port"])

    def configure(self, updated):
        if "stream_large_bodies" in updated:
            try:
                human.parse_size(ctx.options.stream_large_bodies)
            except ValueError:
                raise exceptions.OptionsError(f"Invalid stream_large_bodies specification: "
                                              f"{ctx.options.stream_large_bodies}")
        if "body_size_limit" in updated:
            try:
                human.parse_size(ctx.options.body_size_limit)
            except ValueError:
                raise exceptions.OptionsError(f"Invalid body_size_limit specification: "
                                              f"{ctx.options.body_size_limit}")
        if not self.is_running:
            return
        if "mode" in updated and ctx.options.mode == "transparent":  # pragma: no cover
            platform.init_transparent_mode()
        if any(x in updated for x in ["server", "listen_host", "listen_port"]):
            asyncio.create_task(self.refresh_server())

    async def refresh_server(self):
        async with self._lock:
            if self.server:
                await self.shutdown_server()
                self.server = None
            if ctx.options.server:
                if not ctx.master.addons.get("nextlayer"):
                    ctx.log.warn("Warning: Running proxyserver without nextlayer addon!")
                self.server = await asyncio.start_server(
                    self.handle_connection,
                    self.options.listen_host,
                    self.options.listen_port,
                )
                addrs = {f"http://{human.format_address(s.getsockname())}" for s in self.server.sockets}
                ctx.log.info(f"Proxy server listening at {' and '.join(addrs)}")

    async def shutdown_server(self):
        ctx.log.info("Stopping server...")
        self.server.close()
        await self.server.wait_closed()
        self.server = None

    async def handle_connection(self, r, w):
        peername = w.get_extra_info('peername')
        asyncio_utils.set_task_debug_info(
            asyncio.current_task(),
            name=f"Proxyserver.handle_connection",
            client=peername,
        )
        handler = ProxyConnectionHandler(
            self.master,
            r,
            w,
            self.options
        )
        self._connections[peername] = handler
        try:
            await handler.handle_client()
        finally:
            del self._connections[peername]

    def inject_event(self, event: events.MessageInjected):
        if event.flow.client_conn.peername not in self._connections:
            raise ValueError("Flow is not from a live connection.")
        self._connections[event.flow.client_conn.peername].server_event(event)

    @command.command("inject.websocket")
    def inject_websocket(self, flow: Flow, to_client: bool, message: bytes, is_text: bool = True):
        if not isinstance(flow, http.HTTPFlow) or not flow.websocket:
            ctx.log.warn("Cannot inject WebSocket messages into non-WebSocket flows.")

        msg = websocket.WebSocketMessage(
            Opcode.TEXT if is_text else Opcode.BINARY,
            not to_client,
            message
        )
        event = WebSocketMessageInjected(flow, msg)
        try:
            self.inject_event(event)
        except ValueError as e:
            ctx.log.warn(str(e))

    @command.command("inject.tcp")
    def inject_tcp(self, flow: Flow, to_client: bool, message: bytes):
        if not isinstance(flow, tcp.TCPFlow):
            ctx.log.warn("Cannot inject TCP messages into non-TCP flows.")

        event = TcpMessageInjected(flow, tcp.TCPMessage(not to_client, message))
        try:
            self.inject_event(event)
        except ValueError as e:
            ctx.log.warn(str(e))

    def server_connect(self, ctx: server_hooks.ServerConnectionHookData):
        assert ctx.server.address
        self_connect = (
            ctx.server.address[1] == self.options.listen_port
            and
            ctx.server.address[0] in ("localhost", "127.0.0.1", "::1", self.options.listen_host)
        )
        if self_connect:
            ctx.server.error = "Stopped mitmproxy from recursively connecting to itself."
