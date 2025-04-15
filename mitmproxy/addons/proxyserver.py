"""
This addon is responsible for starting/stopping the proxy server sockets/instances specified by the mode option.
"""

from __future__ import annotations

import asyncio
import collections
import ipaddress
import logging
from collections.abc import Iterable
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Optional

from wsproto.frame_protocol import Opcode

from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy import platform
from mitmproxy import tcp
from mitmproxy import udp
from mitmproxy import websocket
from mitmproxy.connection import Address
from mitmproxy.flow import Flow
from mitmproxy.proxy import events
from mitmproxy.proxy import mode_specs
from mitmproxy.proxy import server_hooks
from mitmproxy.proxy.layers.tcp import TcpMessageInjected
from mitmproxy.proxy.layers.udp import UdpMessageInjected
from mitmproxy.proxy.layers.websocket import WebSocketMessageInjected
from mitmproxy.proxy.mode_servers import ProxyConnectionHandler
from mitmproxy.proxy.mode_servers import ServerInstance
from mitmproxy.proxy.mode_servers import ServerManager
from mitmproxy.utils import asyncio_utils
from mitmproxy.utils import human
from mitmproxy.utils import signals

logger = logging.getLogger(__name__)


class Servers:
    def __init__(self, manager: ServerManager):
        self.changed = signals.AsyncSignal(lambda: None)
        self._instances: dict[mode_specs.ProxyMode, ServerInstance] = dict()
        self._lock = asyncio.Lock()
        self._manager = manager

    @property
    def is_updating(self) -> bool:
        return self._lock.locked()

    async def update(self, modes: Iterable[mode_specs.ProxyMode]) -> bool:
        all_ok = True

        async with self._lock:
            new_instances: dict[mode_specs.ProxyMode, ServerInstance] = {}

            start_tasks = []
            if ctx.options.server:
                # Create missing modes and keep existing ones.
                for spec in modes:
                    if spec in self._instances:
                        instance = self._instances[spec]
                    else:
                        instance = ServerInstance.make(spec, self._manager)
                        start_tasks.append(instance.start())
                    new_instances[spec] = instance

            # Shutdown modes that have been removed from the list.
            stop_tasks = [
                s.stop()
                for spec, s in self._instances.items()
                if spec not in new_instances
            ]

            if not start_tasks and not stop_tasks:
                return (
                    True  # nothing to do, so we don't need to trigger `self.changed`.
                )

            self._instances = new_instances
            # Notify listeners about the new not-yet-started servers.
            await self.changed.send()

            # We first need to free ports before starting new servers.
            for ret in await asyncio.gather(*stop_tasks, return_exceptions=True):
                if ret:
                    all_ok = False
                    logger.error(str(ret))
            for ret in await asyncio.gather(*start_tasks, return_exceptions=True):
                if ret:
                    all_ok = False
                    logger.error(str(ret))

        await self.changed.send()
        return all_ok

    def __len__(self) -> int:
        return len(self._instances)

    def __iter__(self) -> Iterator[ServerInstance]:
        return iter(self._instances.values())

    def __getitem__(self, mode: str | mode_specs.ProxyMode) -> ServerInstance:
        if isinstance(mode, str):
            mode = mode_specs.ProxyMode.parse(mode)
        return self._instances[mode]


class Proxyserver(ServerManager):
    """
    This addon runs the actual proxy server.
    """

    connections: dict[tuple | str, ProxyConnectionHandler]
    servers: Servers

    is_running: bool
    _connect_addr: Address | None = None

    def __init__(self):
        self.connections = {}
        self.servers = Servers(self)
        self.is_running = False

    def __repr__(self):
        return f"Proxyserver({len(self.connections)} active conns)"

    @command.command("proxyserver.active_connections")
    def active_connections(self) -> int:
        return len(self.connections)

    @contextmanager
    def register_connection(
        self, connection_id: tuple | str, handler: ProxyConnectionHandler
    ):
        self.connections[connection_id] = handler
        try:
            yield
        finally:
            del self.connections[connection_id]

    def load(self, loader):
        loader.add_option(
            "store_streamed_bodies",
            bool,
            False,
            "Store HTTP request and response bodies when streamed (see `stream_large_bodies`). "
            "This increases memory consumption, but makes it possible to inspect streamed bodies.",
        )
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
            Stream data to the client if request or response body exceeds the given
            threshold. If streamed, the body will not be stored in any way,
            and such responses cannot be modified. Understands k/m/g
            suffixes, i.e. 3m for 3 megabytes. To store streamed bodies, see `store_streamed_bodies`.
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

    def running(self):
        self.is_running = True

    def configure(self, updated) -> None:
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
                if ctx.options.connect_addr:
                    self._connect_addr = (
                        str(ipaddress.ip_address(ctx.options.connect_addr)),
                        0,
                    )
                else:
                    self._connect_addr = None
            except ValueError:
                raise exceptions.OptionsError(
                    f"Invalid value for connect_addr: {ctx.options.connect_addr!r}. Specify a valid IP address."
                )
        if "mode" in updated or "server" in updated:
            # Make sure that all modes are syntactically valid...
            modes: list[mode_specs.ProxyMode] = []
            for mode in ctx.options.mode:
                try:
                    modes.append(mode_specs.ProxyMode.parse(mode))
                except ValueError as e:
                    raise exceptions.OptionsError(
                        f"Invalid proxy mode specification: {mode} ({e})"
                    )

            # ...and don't listen on the same address.
            listen_addrs = []
            for m in modes:
                if m.transport_protocol == "both":
                    protocols = ["tcp", "udp"]
                else:
                    protocols = [m.transport_protocol]
                host = m.listen_host(ctx.options.listen_host)
                port = m.listen_port(ctx.options.listen_port)
                if port is None:
                    continue
                for proto in protocols:
                    listen_addrs.append((host, port, proto))
            if len(set(listen_addrs)) != len(listen_addrs):
                (host, port, _) = collections.Counter(listen_addrs).most_common(1)[0][0]
                dup_addr = human.format_address((host or "0.0.0.0", port))
                raise exceptions.OptionsError(
                    f"Cannot spawn multiple servers on the same address: {dup_addr}"
                )

            if ctx.options.mode and not ctx.master.addons.get("nextlayer"):
                logger.warning("Warning: Running proxyserver without nextlayer addon!")
            if any(isinstance(m, mode_specs.TransparentMode) for m in modes):
                if platform.original_addr:
                    platform.init_transparent_mode()
                else:
                    raise exceptions.OptionsError(
                        "Transparent mode not supported on this platform."
                    )

            if self.is_running:
                asyncio_utils.create_task(
                    self.servers.update(modes),
                    name="update servers",
                    keep_ref=True,
                )

    async def setup_servers(self) -> bool:
        """Setup proxy servers. This may take an indefinite amount of time to complete (e.g. on permission prompts)."""
        return await self.servers.update(
            [mode_specs.ProxyMode.parse(m) for m in ctx.options.mode]
        )

    def listen_addrs(self) -> list[Address]:
        return [addr for server in self.servers for addr in server.listen_addrs]

    def inject_event(self, event: events.MessageInjected):
        connection_id: str | tuple
        if event.flow.client_conn.transport_protocol != "udp":
            connection_id = event.flow.client_conn.id
        else:  # pragma: no cover
            # temporary workaround: for UDP we don't have persistent client IDs yet.
            connection_id = (
                event.flow.client_conn.peername,
                event.flow.client_conn.sockname,
            )
        if connection_id not in self.connections:
            raise ValueError("Flow is not from a live connection.")

        asyncio_utils.create_task(
            self.connections[connection_id].server_event(event),
            name=f"inject_event",
            keep_ref=True,
            client=event.flow.client_conn.peername,
        )

    @command.command("inject.websocket")
    def inject_websocket(
        self, flow: Flow, to_client: bool, message: bytes, is_text: bool = True
    ):
        if not isinstance(flow, http.HTTPFlow) or not flow.websocket:
            logger.warning("Cannot inject WebSocket messages into non-WebSocket flows.")

        msg = websocket.WebSocketMessage(
            Opcode.TEXT if is_text else Opcode.BINARY, not to_client, message
        )
        event = WebSocketMessageInjected(flow, msg)
        try:
            self.inject_event(event)
        except ValueError as e:
            logger.warning(str(e))

    @command.command("inject.tcp")
    def inject_tcp(self, flow: Flow, to_client: bool, message: bytes):
        if not isinstance(flow, tcp.TCPFlow):
            logger.warning("Cannot inject TCP messages into non-TCP flows.")

        event = TcpMessageInjected(flow, tcp.TCPMessage(not to_client, message))
        try:
            self.inject_event(event)
        except ValueError as e:
            logger.warning(str(e))

    @command.command("inject.udp")
    def inject_udp(self, flow: Flow, to_client: bool, message: bytes):
        if not isinstance(flow, udp.UDPFlow):
            logger.warning("Cannot inject UDP messages into non-UDP flows.")

        event = UdpMessageInjected(flow, udp.UDPMessage(not to_client, message))
        try:
            self.inject_event(event)
        except ValueError as e:
            logger.warning(str(e))

    def server_connect(self, data: server_hooks.ServerConnectionHookData):
        if data.server.sockname is None:
            data.server.sockname = self._connect_addr

        # Prevent mitmproxy from recursively connecting to itself.
        assert data.server.address
        connect_host, connect_port, *_ = data.server.address

        for server in self.servers:
            for listen_host, listen_port, *_ in server.listen_addrs:
                self_connect = (
                    connect_port == listen_port
                    and connect_host in ("localhost", "127.0.0.1", "::1", listen_host)
                    and server.mode.transport_protocol == data.server.transport_protocol
                )
                if self_connect:
                    data.server.error = (
                        "Request destination unknown. "
                        "Unable to figure out where this request should be forwarded to."
                    )
                    return
