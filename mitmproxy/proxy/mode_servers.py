"""
This module defines "server instances", which manage
the TCP/UDP servers spawned by mitmproxy as specified by the proxy mode.

Example:

    mode = ProxyMode.parse("reverse:https://example.com")
    inst = ServerInstance.make(mode, manager_that_handles_callbacks)
    await inst.start()
    # TCP server is running now.
"""
from __future__ import annotations

import asyncio
import json
import logging
import socket
import textwrap
import typing
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import ClassVar, Generic, TypeVar, cast, get_args

import errno
import mitmproxy_wireguard as wg

from mitmproxy import ctx, flow, platform
from mitmproxy.connection import Address
from mitmproxy.master import Master
from mitmproxy.net import local_ip, udp
from mitmproxy.net.udp_wireguard import WireGuardDatagramTransport
from mitmproxy.proxy import commands, layers, mode_specs, server
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layer import Layer
from mitmproxy.utils import human

logger = logging.getLogger(__name__)


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


M = TypeVar('M', bound=mode_specs.ProxyMode)


class ServerManager(typing.Protocol):
    connections: dict[tuple, ProxyConnectionHandler]

    @contextmanager
    def register_connection(self, connection_id: tuple, handler: ProxyConnectionHandler):
        ...  # pragma: no cover


# Python 3.11: Use typing.Self
Self = TypeVar("Self", bound="ServerInstance")


class ServerInstance(Generic[M], metaclass=ABCMeta):
    __modes: ClassVar[dict[str, type[ServerInstance]]] = {}

    def __init__(self, mode: M, manager: ServerManager):
        self.mode: M = mode
        self.manager: ServerManager = manager
        self.last_exception: Exception | None = None

    def __init_subclass__(cls, **kwargs):
        """Register all subclasses so that make() finds them."""
        # extract mode from Generic[Mode].
        mode = get_args(cls.__orig_bases__[0])[0]
        if not isinstance(mode, TypeVar):
            assert issubclass(mode, mode_specs.ProxyMode)
            assert mode.type_name not in ServerInstance.__modes
            ServerInstance.__modes[mode.type_name] = cls

    @classmethod
    def make(
        cls: typing.Type[Self],
        mode: mode_specs.ProxyMode | str,
        manager: ServerManager,
    ) -> Self:
        if isinstance(mode, str):
            mode = mode_specs.ProxyMode.parse(mode)
        inst = ServerInstance.__modes[mode.type_name](mode, manager)

        if not isinstance(inst, cls):
            raise ValueError(f"{mode!r} is not a spec for a {cls.__name__} server.")

        return inst

    @property
    @abstractmethod
    def is_running(self) -> bool:
        pass

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

    @abstractmethod
    def make_top_layer(self, context: Context) -> Layer:
        pass

    def to_json(self) -> dict:
        return {
            "type": self.mode.type_name,
            "description": self.mode.description,
            "full_spec": self.mode.full_spec,
            "is_running": self.is_running,
            "last_exception": str(self.last_exception) if self.last_exception else None,
            "listen_addrs": self.listen_addrs,
        }

    async def handle_tcp_connection(
        self,
        reader: asyncio.StreamReader | wg.TcpStream,
        writer: asyncio.StreamWriter | wg.TcpStream,
    ) -> None:
        handler = ProxyConnectionHandler(
            ctx.master, reader, writer, ctx.options, self.mode
        )
        handler.layer = self.make_top_layer(handler.layer.context)
        if isinstance(self.mode, mode_specs.TransparentMode):
            s = cast(socket.socket, writer.get_extra_info("socket"))
            try:
                assert platform.original_addr
                original_dst = platform.original_addr(s)
            except Exception as e:
                logger.error(f"Transparent mode failure: {e!r}")
                return
            else:
                handler.layer.context.client.sockname = original_dst
                handler.layer.context.server.address = original_dst
        elif isinstance(self.mode, mode_specs.WireGuardMode):
            original_dst = writer.get_extra_info("original_dst")
            handler.layer.context.client.sockname = original_dst
            handler.layer.context.server.address = original_dst

        connection_id = (
            handler.layer.context.client.transport_protocol,
            handler.layer.context.client.peername,
            handler.layer.context.client.sockname,
        )
        with self.manager.register_connection(connection_id, handler):
            await handler.handle_client()

    def handle_udp_datagram(
        self,
        transport: asyncio.DatagramTransport,
        data: bytes,
        remote_addr: Address,
        local_addr: Address,
    ) -> None:
        connection_id = ("udp", remote_addr, local_addr)
        if connection_id not in self.manager.connections:
            reader = udp.DatagramReader()
            writer = udp.DatagramWriter(transport, remote_addr, reader)
            handler = ProxyConnectionHandler(
                ctx.master, reader, writer, ctx.options, self.mode
            )
            handler.timeout_watchdog.CONNECTION_TIMEOUT = 20
            handler.layer = self.make_top_layer(handler.layer.context)
            handler.layer.context.client.transport_protocol = "udp"
            handler.layer.context.server.transport_protocol = "udp"
            if isinstance(self.mode, mode_specs.WireGuardMode):
                handler.layer.context.server.address = local_addr

            # pre-register here - we may get datagrams before the task is executed.
            self.manager.connections[connection_id] = handler
            asyncio.create_task(self.handle_udp_connection(connection_id, handler))
        else:
            handler = self.manager.connections[connection_id]
            reader = cast(udp.DatagramReader, handler.transports[handler.client].reader)
        reader.feed_data(data, remote_addr)

    async def handle_udp_connection(self, connection_id: tuple, handler: ProxyConnectionHandler) -> None:
        with self.manager.register_connection(connection_id, handler):
            await handler.handle_client()


class AsyncioServerInstance(ServerInstance[M], metaclass=ABCMeta):
    _server: asyncio.Server | udp.UdpServer | None = None
    _listen_addrs: tuple[Address, ...] = tuple()

    @property
    def is_running(self) -> bool:
        return self._server is not None

    async def start(self) -> None:
        assert self._server is None
        host = self.mode.listen_host(ctx.options.listen_host)
        port = self.mode.listen_port(ctx.options.listen_port)
        try:
            self._server = await self.listen(host, port)
            self._listen_addrs = tuple(s.getsockname() for s in self._server.sockets)
        except OSError as e:
            self.last_exception = e
            message = f"{self.mode.description} failed to listen on {host or '*'}:{port} with {e}"
            if e.errno == errno.EADDRINUSE and self.mode.custom_listen_port is None:
                assert self.mode.custom_listen_host is None  # since [@ [listen_addr:]listen_port]
                message += f"\nTry specifying a different port by using `--mode {self.mode.full_spec}@{port + 1}`."
            raise OSError(e.errno, message, e.filename) from e
        except Exception as e:
            self.last_exception = e
            raise
        else:
            self.last_exception = None
        addrs = " and ".join({human.format_address(a) for a in self._listen_addrs})
        logger.info(f"{self.mode.description} listening at {addrs}.")

    async def stop(self) -> None:
        assert self._server is not None
        # we always reset _server and _listen_addrs and ignore failures
        server = self._server
        listen_addrs = self._listen_addrs
        self._server = None
        self._listen_addrs = tuple()
        try:
            server.close()
            await server.wait_closed()
        except Exception as e:
            self.last_exception = e
            raise
        else:
            self.last_exception = None
        addrs = " and ".join({human.format_address(a) for a in listen_addrs})
        logger.info(f"Stopped {self.mode.description} at {addrs}.")

    async def listen(self, host: str, port: int) -> asyncio.Server | udp.UdpServer:
        if self.mode.transport_protocol == "tcp":
            # workaround for https://github.com/python/cpython/issues/89856:
            # We want both IPv4 and IPv6 sockets to bind to the same port.
            # This may fail (https://github.com/mitmproxy/mitmproxy/pull/5542#issuecomment-1222803291),
            # so we try to cover the 99% case and then give up and fall back to what asyncio does.
            if port == 0:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.bind(("", 0))
                    fixed_port = s.getsockname()[1]
                    s.close()
                    return await asyncio.start_server(self.handle_tcp_connection, host, fixed_port)
                except Exception as e:
                    logger.debug(f"Failed to listen on a single port ({e!r}), falling back to default behavior.")
            return await asyncio.start_server(self.handle_tcp_connection, host, port)
        elif self.mode.transport_protocol == "udp":
            # create_datagram_endpoint only creates one socket, so the workaround above doesn't apply
            # NOTE once we do dual servers, we should consider creating sockets manually to ensure
            # both TCP and UDP listen to the same IPs and same ports
            return await udp.start_server(
                self.handle_udp_datagram,
                host,
                port,
            )
        else:
            raise AssertionError(self.mode.transport_protocol)

    @property
    def listen_addrs(self) -> tuple[Address, ...]:
        return self._listen_addrs


class WireGuardServerInstance(ServerInstance[mode_specs.WireGuardMode]):
    _server: wg.Server | None = None
    _listen_addrs: tuple[Address, ...] = tuple()

    server_key: str
    client_key: str

    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.TransparentProxy(context)

    @property
    def is_running(self) -> bool:
        return self._server is not None

    async def start(self) -> None:
        assert self._server is None
        host = self.mode.listen_host(ctx.options.listen_host)
        port = self.mode.listen_port(ctx.options.listen_port)

        if self.mode.data:
            conf_path = Path(self.mode.data).expanduser()
        else:
            conf_path = Path(ctx.options.confdir).expanduser() / "wireguard.conf"

        try:
            if not conf_path.exists():
                conf_path.write_text(json.dumps({
                    "server_key": wg.genkey(),
                    "client_key": wg.genkey(),
                }, indent=4))

            try:
                c = json.loads(conf_path.read_text())
                self.server_key = c["server_key"]
                self.client_key = c["client_key"]
            except Exception as e:
                raise ValueError(f"Invalid configuration file ({conf_path}): {e}") from e
            # error early on invalid keys
            p = wg.pubkey(self.client_key)
            _ = wg.pubkey(self.server_key)

            self._server = await wg.start_server(
                host,
                port,
                self.server_key,
                [p],
                self.wg_handle_tcp_connection,
                self.wg_handle_udp_datagram,
            )
            self._listen_addrs = (self._server.getsockname(),)
        except Exception as e:
            self.last_exception = e
            message = f"{self.mode.description} failed to listen on {host or '*'}:{port} with {e}"
            raise OSError(message) from e
        else:
            self.last_exception = None

        addrs = " and ".join({human.format_address(a) for a in self.listen_addrs})
        conf = self.client_conf()
        assert conf
        logger.info(
            f"{self.mode.description} listening at {addrs}.\n"
            + "------------------------------------------------------------\n"
            + conf
            + "\n------------------------------------------------------------"
        )

    def client_conf(self) -> str | None:
        if not self._server:
            return None
        host = local_ip.get_local_ip() or local_ip.get_local_ip6()
        port = self.mode.listen_port(ctx.options.listen_port)
        return textwrap.dedent(f"""
            [Interface]
            PrivateKey = {self.client_key}
            Address = 10.0.0.1/32
            DNS = 10.0.0.53

            [Peer]
            PublicKey = {wg.pubkey(self.server_key)}
            AllowedIPs = 0.0.0.0/0
            Endpoint = {host}:{port}
            """).strip()

    def to_json(self) -> dict:
        return {
            "wireguard_conf": self.client_conf(),
            **super().to_json()
        }

    async def stop(self) -> None:
        assert self._server is not None
        self._server.close()
        await self._server.wait_closed()
        self._server = None
        self.last_exception = None

        addrs = " and ".join({human.format_address(a) for a in self.listen_addrs})
        logger.info(f"Stopped {self.mode.description} at {addrs}.")

    @property
    def listen_addrs(self) -> tuple[Address, ...]:
        return self._listen_addrs

    async def wg_handle_tcp_connection(self, stream: wg.TcpStream) -> None:
        await self.handle_tcp_connection(stream, stream)

    def wg_handle_udp_datagram(self, data: bytes, remote_addr: Address, local_addr: Address) -> None:
        assert self._server is not None
        transport = WireGuardDatagramTransport(self._server, local_addr, remote_addr)
        self.handle_udp_datagram(
            transport,
            data,
            remote_addr,
            local_addr
        )


class RegularInstance(AsyncioServerInstance[mode_specs.RegularMode]):
    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.HttpProxy(context)


class UpstreamInstance(AsyncioServerInstance[mode_specs.UpstreamMode]):
    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.HttpUpstreamProxy(context)


class TransparentInstance(AsyncioServerInstance[mode_specs.TransparentMode]):
    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.TransparentProxy(context)


class ReverseInstance(AsyncioServerInstance[mode_specs.ReverseMode]):
    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.ReverseProxy(context)


class Socks5Instance(AsyncioServerInstance[mode_specs.Socks5Mode]):
    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.Socks5Proxy(context)


class DnsInstance(AsyncioServerInstance[mode_specs.DnsMode]):
    def make_top_layer(self, context: Context) -> Layer:
        return layers.DNSLayer(context)
