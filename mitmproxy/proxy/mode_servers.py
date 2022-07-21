"""
This module defines "server instances", which manage
the TCP/UDP servers spawned my mitmproxy as specified by the proxy mode.

Example:

    mode = ProxyMode.parse("reverse:https://example.com")
    inst = ServerInstance.make(mode, manager_that_handles_callbacks)
    await inst.start()
    # TCP server is running now.
"""
from __future__ import annotations

import asyncio
import struct
import typing
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from functools import cached_property
from typing import ClassVar, Generic, TypeVar, cast, get_args

from mitmproxy import ctx, flow, log
from mitmproxy.connection import Address
from mitmproxy.master import Master
from mitmproxy.net import udp
from mitmproxy.proxy import commands, layers, mode_specs, server
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layer import Layer
from mitmproxy.utils import asyncio_utils, human


class ProxyConnectionHandler(server.LiveConnectionHandler):
    master: Master

    def __init__(self, master, r, w, options, mode):
        self.master = master
        super().__init__(r, w, options, mode)
        self.log_prefix = f"{human.format_address(self.client.peername)}: "

    async def handle_hook(self, hook: commands.StartHook) -> None:
        with self.timeout_watchdog.disarm():
            # We currently only support single-argument hooks.
            (data,) = hook.args()
            await self.master.addons.handle_lifecycle(hook)
            if isinstance(data, flow.Flow):
                await data.wait_for_resume()  # pragma: no cover

    def log(self, message: str, level: str = "info") -> None:
        x = log.LogEntry(self.log_prefix + message, level)
        asyncio_utils.create_task(
            self.master.addons.handle_lifecycle(log.AddLogHook(x)),
            name="ProxyConnectionHandler.log",
        )


M = TypeVar('M', bound=mode_specs.ProxyMode)


class ServerManager(typing.Protocol):
    connections: dict[tuple, ProxyConnectionHandler]

    @contextmanager
    def register_connection(self, connection_id: tuple, handler: ProxyConnectionHandler):
        ...  # pragma: no cover


class ServerInstance(Generic[M], metaclass=ABCMeta):

    __modes: ClassVar[dict[str, type[ServerInstance]]] = {}

    def __init__(self, mode: M, manager: ServerManager):
        self.mode: M = mode
        self.manager: ServerManager = manager

    def __init_subclass__(cls, **kwargs):
        """Register all subclasses so that make() finds them."""
        # extract mode from Generic[Mode].
        mode = get_args(cls.__orig_bases__[0])[0]
        if mode != M:
            assert mode.type not in ServerInstance.__modes
            ServerInstance.__modes[mode.type] = cls

    @staticmethod
    def make(
        mode: mode_specs.ProxyMode | str,
        manager: ServerManager,
    ) -> ServerInstance:
        if isinstance(mode, str):
            mode = mode_specs.ProxyMode.parse(mode)
        return ServerInstance.__modes[mode.type](mode, manager)

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @property
    @abstractmethod
    def listen_addrs(self) -> tuple[Address, ...]:
        pass


class TcpServerInstance(ServerInstance[M], metaclass=ABCMeta):
    server: asyncio.Server | None = None

    @abstractmethod
    def make_top_layer(self, context: Context) -> Layer:
        pass

    async def handle_tcp_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        connection_id = (
            "tcp",
            writer.get_extra_info("peername"),
            writer.get_extra_info("sockname"),
        )
        handler = ProxyConnectionHandler(
            ctx.master, reader, writer, ctx.options, self.mode
        )
        handler.layer = self.make_top_layer(handler.layer.context)
        with self.manager.register_connection(connection_id, handler):
            await handler.handle_client()

    async def start(self):
        assert not self.server
        self.server = await asyncio.start_server(
            self.handle_tcp_connection,
            self.mode.listen_host(ctx.options.listen_host),
            self.mode.listen_port(ctx.options.listen_port),
        )

        addrs = {f"{human.format_address(s)}" for s in self.listen_addrs}
        ctx.log.info(
            f"{self.log_desc} listening at {' and '.join(addrs)}."
        )

    @property
    @abstractmethod
    def log_desc(self) -> str:
        pass

    async def stop(self):
        assert self.server
        self.server.close()
        await self.server.wait_closed()
        ctx.log.info(f"Stopped {self.mode.type} proxy server.")

    @cached_property
    def listen_addrs(self) -> tuple[Address, ...]:
        assert self.server
        return tuple(s.getsockname() for s in self.server.sockets)


class RegularInstance(TcpServerInstance[mode_specs.RegularMode]):
    log_desc = "HTTP(S) proxy"

    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.HttpProxy(context)


class UpstreamInstance(TcpServerInstance[mode_specs.UpstreamMode]):
    log_desc = "HTTP(S) proxy (upstream mode)"

    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.HttpUpstreamProxy(context)


class TransparentInstance(TcpServerInstance[mode_specs.TransparentMode]):
    log_desc = "Transparent proxy"

    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.TransparentProxy(context)


class ReverseInstance(TcpServerInstance[mode_specs.ReverseMode]):
    @property
    def log_desc(self) -> str:
        return f"Reverse proxy to {self.mode.data}"

    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.ReverseProxy(context)


class Socks5Instance(TcpServerInstance[mode_specs.Socks5Mode]):
    log_desc = "SOCKS v5 proxy"

    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.Socks5Proxy(context)


class DnsInstance(ServerInstance[mode_specs.DnsMode]):
    server: udp.UdpServer | None = None

    async def start(self):
        assert not self.server
        self.server = await udp.start_server(
            self.handle_dns_datagram,
            self.mode.listen_host(ctx.options.listen_host),
            self.mode.listen_port(ctx.options.listen_port),
            transparent=False
        )
        addrs = {f"{human.format_address(s)}" for s in self.listen_addrs}
        ctx.log.info(
            f"DNS server listening at {' and '.join(addrs)}."
        )

    async def stop(self):
        assert self.server
        self.server.close()
        await self.server.wait_closed()
        ctx.log.info(f"Stopped {self.mode.type} proxy server.")

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
        if connection_id not in self.manager.connections:
            reader = udp.DatagramReader()
            writer = udp.DatagramWriter(transport, remote_addr, reader)
            handler = ProxyConnectionHandler(
                ctx.master, reader, writer, ctx.options, self.mode
            )
            handler.timeout_watchdog.CONNECTION_TIMEOUT = 20
            handler.layer = layers.DNSLayer(handler.layer.context)
            handler.layer.context.server.address = (self.mode.data or "resolve-local", 53)
            handler.layer.context.server.transport_protocol = "udp"

            # pre-register here - we may get datagrams before the task is executed.
            self.manager.connections[connection_id] = handler
            asyncio.create_task(self.handle_dns_connection(connection_id, handler))
        else:
            handler = self.manager.connections[connection_id]
            reader = cast(udp.DatagramReader, handler.transports[handler.client].reader)
        reader.feed_data(data, remote_addr)

    async def handle_dns_connection(self, connection_id, handler):
        with self.manager.register_connection(connection_id, handler):
            await handler.handle_client()

    @cached_property
    def listen_addrs(self) -> tuple[Address, ...]:
        assert self.server
        return tuple(s.getsockname() for s in self.server.sockets)
