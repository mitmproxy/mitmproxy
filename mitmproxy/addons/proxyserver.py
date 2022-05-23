import asyncio
from asyncio import base_events
import ipaddress
import re
import struct
from typing import Optional

from mitmproxy import (
    command,
    ctx,
    exceptions,
    flow,
    http,
    log,
    master,
    options,
    platform,
    tcp,
    websocket,
)
from mitmproxy.connection import Address
from mitmproxy.flow import Flow
from mitmproxy.net import udp
from mitmproxy.proxy import commands, events, layers, server_hooks
from mitmproxy.proxy import server
from mitmproxy.proxy.layers.tcp import TcpMessageInjected
from mitmproxy.proxy.layers.websocket import WebSocketMessageInjected
from mitmproxy.utils import asyncio_utils, human
from wsproto.frame_protocol import Opcode


class ProxyConnectionHandler(server.LiveConnectionHandler):
    master: master.Master

    def __init__(self, master, r, w, options, timeout=None):
        self.master = master
        super().__init__(r, w, options)
        self.log_prefix = f"{human.format_address(self.client.peername)}: "
        if timeout is not None:
            self.timeout_watchdog.CONNECTION_TIMEOUT = timeout

    async def handle_hook(self, hook: commands.StartHook) -> None:
        with self.timeout_watchdog.disarm():
            # We currently only support single-argument hooks.
            (data,) = hook.args()
            await self.master.addons.handle_lifecycle(hook)
            if isinstance(data, flow.Flow):
                await data.wait_for_resume()

    def log(self, message: str, level: str = "info") -> None:
        x = log.LogEntry(self.log_prefix + message, level)
        asyncio_utils.create_task(
            self.master.addons.handle_lifecycle(log.AddLogHook(x)),
            name="ProxyConnectionHandler.log",
        )


class Proxyserver:
    """
    This addon runs the actual proxy server.
    """

    tcp_server: Optional[base_events.Server]
    dns_server: Optional[udp.UdpServer]
    connect_addr: Optional[Address]
    listen_port: int
    dns_reverse_addr: Optional[tuple[str, int]]
    master: master.Master
    options: options.Options
    is_running: bool
    _connections: dict[tuple, ProxyConnectionHandler]

    def __init__(self):
        self._lock = asyncio.Lock()
        self.tcp_server = None
        self.dns_server = None
        self.connect_addr = None
        self.dns_reverse_addr = None
        self.is_running = False
        self._connections = {}

    def __repr__(self):
        return f"ProxyServer({'running' if self.running_servers else 'stopped'}, {len(self._connections)} active conns)"

    @property
    def _server_desc(self):
        yield "Proxy", self.tcp_server, lambda x: setattr(
            self, "tcp_server", x
        ), ctx.options.server, lambda: asyncio.start_server(
            self.handle_tcp_connection,
            self.options.listen_host,
            self.options.listen_port,
        )
        yield "DNS", self.dns_server, lambda x: setattr(
            self, "dns_server", x
        ), ctx.options.dns_server, lambda: udp.start_server(
            self.handle_dns_datagram,
            self.options.dns_listen_host or "127.0.0.1",
            self.options.dns_listen_port,
            transparent=self.options.dns_mode == "transparent",
        )

    @property
    def running_servers(self):
        return tuple(
            instance
            for _, instance, _, _, _ in self._server_desc
            if instance is not None
        )

    def load(self, loader):
        loader.add_option(
            "connection_strategy",
            str,
            "eager",
            "Determine when server connections should be established. When set to lazy, mitmproxy "
            "tries to defer establishing an upstream connection as long as possible. This makes it possible to "
            "use server replay while being offline. When set to eager, mitmproxy can detect protocols with "
            "server-side greetings, as well as accurately mirror TLS ALPN negotiation.",
            choices=("eager", "lazy"),
        )
        loader.add_option(
            "stream_large_bodies",
            Optional[str],
            None,
            """
            Stream data to the client if response body exceeds the given
            threshold. If streamed, the body will not be stored in any way.
            Understands k/m/g suffixes, i.e. 3m for 3 megabytes.
            """,
        )
        loader.add_option(
            "body_size_limit",
            Optional[str],
            None,
            """
            Byte size limit of HTTP request and response bodies. Understands
            k/m/g suffixes, i.e. 3m for 3 megabytes.
            """,
        )
        loader.add_option(
            "keep_host_header",
            bool,
            False,
            """
            Reverse Proxy: Keep the original host header instead of rewriting it
            to the reverse proxy target.
            """,
        )
        loader.add_option(
            "proxy_debug",
            bool,
            False,
            "Enable debug logs in the proxy core.",
        )
        loader.add_option(
            "normalize_outbound_headers",
            bool,
            True,
            """
            Normalize outgoing HTTP/2 header names, but emit a warning when doing so.
            HTTP/2 does not allow uppercase header names. This option makes sure that HTTP/2 headers set
            in custom scripts are lowercased before they are sent.
            """,
        )
        loader.add_option(
            "validate_inbound_headers",
            bool,
            True,
            """
            Make sure that incoming HTTP requests are not malformed.
            Disabling this option makes mitmproxy vulnerable to HTTP smuggling attacks.
            """,
        )
        loader.add_option(
            "connect_addr",
            Optional[str],
            None,
            """Set the local IP address that mitmproxy should use when connecting to upstream servers.""",
        )
        loader.add_option(
            "dns_server", bool, False, """Start a DNS server. Disabled by default."""
        )
        loader.add_option(
            "dns_listen_host", str, "", """Address to bind DNS server to."""
        )
        loader.add_option("dns_listen_port", int, 53, """DNS server service port.""")
        loader.add_option(
            "dns_mode",
            str,
            "regular",
            """
            One of "regular", "reverse:<ip>[:<port>]" or "transparent".
            regular....: requests will be resolved using the local resolver
            reverse....: forward queries to another DNS server
            transparent: transparent mode
            """,
        )

    async def running(self):
        self.master = ctx.master
        self.options = ctx.options
        self.is_running = True
        await self.refresh_server()

    def configure(self, updated):
        if "stream_large_bodies" in updated:
            try:
                human.parse_size(ctx.options.stream_large_bodies)
            except ValueError:
                raise exceptions.OptionsError(
                    f"Invalid stream_large_bodies specification: "
                    f"{ctx.options.stream_large_bodies}"
                )
        if "body_size_limit" in updated:
            try:
                human.parse_size(ctx.options.body_size_limit)
            except ValueError:
                raise exceptions.OptionsError(
                    f"Invalid body_size_limit specification: "
                    f"{ctx.options.body_size_limit}"
                )
        if "connect_addr" in updated:
            try:
                self.connect_addr = (str(ipaddress.ip_address(ctx.options.connect_addr)), 0) if ctx.options.connect_addr else None
            except ValueError:
                raise exceptions.OptionsError(
                    f"Invalid connection address {ctx.options.connect_addr!r}, specify a valid IP address."
                )

        if "dns_mode" in updated:
            m = re.match(
                r"^(regular|reverse:(?P<host>[^:]+)(:(?P<port>\d+))?|transparent)$",
                ctx.options.dns_mode,
            )
            if not m:
                raise exceptions.OptionsError(
                    f"Invalid DNS mode {ctx.options.dns_mode!r}."
                )
            if m["host"]:
                try:
                    self.dns_reverse_addr = (
                        str(ipaddress.ip_address(m["host"])),
                        int(m["port"]) if m["port"] is not None else 53,
                    )
                except ValueError:
                    raise exceptions.OptionsError(
                        f"Invalid DNS reverse mode, expected 'reverse:ip[:port]' got {ctx.options.dns_mode!r}."
                    )
            else:
                self.dns_reverse_addr = None
        if "mode" in updated and ctx.options.mode == "transparent":  # pragma: no cover
            platform.init_transparent_mode()
        if self.is_running and any(
            x in updated
            for x in [
                "server",
                "listen_host",
                "listen_port",
                "dns_server",
                "dns_mode",
                "dns_listen_host",
                "dns_listen_port",
            ]
        ):
            asyncio.create_task(self.refresh_server())

    async def refresh_server(self):
        async with self._lock:
            await self.shutdown_server()
            if ctx.options.server and not ctx.master.addons.get("nextlayer"):
                ctx.log.warn("Warning: Running proxyserver without nextlayer addon!")
            for name, instance, set_instance, enabled, start in self._server_desc:
                if instance is None and enabled:
                    try:
                        instance = await start()
                    except OSError as e:
                        ctx.log.error(str(e))
                    else:
                        set_instance(instance)
                        # TODO: This is a bit confusing currently for `-p 0`.
                        addrs = {
                            f"{human.format_address(s.getsockname())}"
                            for s in instance.sockets
                        }
                        ctx.log.info(
                            f"{name} server listening at {' and '.join(addrs)}"
                        )

    async def shutdown_server(self):
        for name, instance, set_instance, _, _ in self._server_desc:
            if instance is not None:
                ctx.log.info(f"Stopping {name} server...")
                try:
                    instance.close()
                    await instance.wait_closed()
                except OSError as e:
                    ctx.log.error(str(e))
                else:
                    set_instance(None)

    async def handle_connection(self, connection_id: tuple):
        handler = self._connections[connection_id]
        task = asyncio.current_task()
        assert task
        asyncio_utils.set_task_debug_info(
            task,
            name=f"Proxyserver.handle_connection",
            client=handler.client.peername,
        )
        try:
            await handler.handle_client()
        finally:
            del self._connections[connection_id]

    async def handle_tcp_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        connection_id = (
            "tcp",
            writer.get_extra_info("peername"),
            writer.get_extra_info("sockname"),
        )
        self._connections[connection_id] = ProxyConnectionHandler(
            self.master, reader, writer, self.options
        )
        await self.handle_connection(connection_id)

    def handle_dns_datagram(
        self,
        transport: asyncio.DatagramTransport,
        data: bytes,
        remote_addr: Address,
        local_addr: Address,
    ) -> None:
        try:
            dns_id = struct.unpack_from("!H", data, 0)
        except struct.error:
            ctx.log.info(
                f"Invalid DNS datagram received from {human.format_address(remote_addr)}."
            )
            return
        connection_id = ("udp", dns_id, remote_addr, local_addr)
        if connection_id not in self._connections:
            reader = udp.DatagramReader()
            writer = udp.DatagramWriter(transport, remote_addr, reader)
            handler = ProxyConnectionHandler(
                self.master, reader, writer, self.options, 20
            )
            handler.layer = layers.DNSLayer(handler.layer.context)
            handler.layer.context.server.address = (
                local_addr
                if self.options.dns_mode == "transparent"
                else self.dns_reverse_addr
            )
            handler.layer.context.server.transport_protocol = "udp"
            self._connections[connection_id] = handler
            asyncio.create_task(self.handle_connection(connection_id))
        else:
            handler = self._connections[connection_id]
            client_reader = handler.transports[handler.client].reader
            assert isinstance(client_reader, udp.DatagramReader)
            reader = client_reader
        reader.feed_data(data, remote_addr)

    def inject_event(self, event: events.MessageInjected):
        connection_id = (
            "tcp",
            event.flow.client_conn.peername,
            event.flow.client_conn.sockname,
        )
        if connection_id not in self._connections:
            raise ValueError("Flow is not from a live connection.")
        self._connections[connection_id].server_event(event)

    @command.command("inject.websocket")
    def inject_websocket(
        self, flow: Flow, to_client: bool, message: bytes, is_text: bool = True
    ):
        if not isinstance(flow, http.HTTPFlow) or not flow.websocket:
            ctx.log.warn("Cannot inject WebSocket messages into non-WebSocket flows.")

        msg = websocket.WebSocketMessage(
            Opcode.TEXT if is_text else Opcode.BINARY, not to_client, message
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
        # FIXME: Move this to individual proxy modes.
        self_connect = ctx.server.address[1] in (
            self.options.dns_listen_port,
            self.options.listen_port,
        ) and ctx.server.address[0] in (
            "localhost",
            "127.0.0.1",
            "::1",
            self.options.listen_host,
            self.options.dns_listen_host,
        )
        if self_connect:
            ctx.server.error = (
                "Request destination unknown. "
                "Unable to figure out where this request should be forwarded to."
            )
        if ctx.server.sockname is None:
            ctx.server.sockname = self.connect_addr
