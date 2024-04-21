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
import errno
import json
import logging
import os
import socket
import sys
import textwrap
import typing
from abc import ABCMeta
from abc import abstractmethod
from contextlib import contextmanager
from pathlib import Path
from typing import cast
from typing import ClassVar
from typing import Generic
from typing import get_args
from typing import TYPE_CHECKING
from typing import TypeVar

import mitmproxy_rs

from mitmproxy import ctx
from mitmproxy import flow
from mitmproxy import platform
from mitmproxy.connection import Address
from mitmproxy.net import local_ip
from mitmproxy.proxy import commands
from mitmproxy.proxy import layers
from mitmproxy.proxy import mode_specs
from mitmproxy.proxy import server
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layer import Layer
from mitmproxy.utils import human

if sys.version_info < (3, 11):
    from typing_extensions import Self  # pragma: no cover
else:
    from typing import Self

if TYPE_CHECKING:
    from mitmproxy.master import Master

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


M = TypeVar("M", bound=mode_specs.ProxyMode)


class ServerManager(typing.Protocol):
    # temporary workaround: for UDP, we use the 4-tuple because we don't have a uuid.
    connections: dict[tuple | str, ProxyConnectionHandler]

    @contextmanager
    def register_connection(
        self, connection_id: tuple | str, handler: ProxyConnectionHandler
    ): ...  # pragma: no cover


class ServerInstance(Generic[M], metaclass=ABCMeta):
    __modes: ClassVar[dict[str, type[ServerInstance]]] = {}

    last_exception: Exception | None = None

    def __init__(self, mode: M, manager: ServerManager):
        self.mode: M = mode
        self.manager: ServerManager = manager

    def __init_subclass__(cls, **kwargs):
        """Register all subclasses so that make() finds them."""
        # extract mode from Generic[Mode].
        mode = get_args(cls.__orig_bases__[0])[0]  # type: ignore
        if not isinstance(mode, TypeVar):
            assert issubclass(mode, mode_specs.ProxyMode)
            assert mode.type_name not in ServerInstance.__modes
            ServerInstance.__modes[mode.type_name] = cls

    @classmethod
    def make(
        cls,
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

    async def start(self) -> None:
        try:
            await self._start()
        except Exception as e:
            self.last_exception = e
            raise
        else:
            self.last_exception = None
        if self.listen_addrs:
            addrs = " and ".join({human.format_address(a) for a in self.listen_addrs})
            logger.info(f"{self.mode.description} listening at {addrs}.")
        else:
            logger.info(f"{self.mode.description} started.")

    async def stop(self) -> None:
        listen_addrs = self.listen_addrs
        try:
            await self._stop()
        except Exception as e:
            self.last_exception = e
            raise
        else:
            self.last_exception = None
        if listen_addrs:
            addrs = " and ".join({human.format_address(a) for a in listen_addrs})
            logger.info(f"{self.mode.description} at {addrs} stopped.")
        else:
            logger.info(f"{self.mode.description} stopped.")

    @abstractmethod
    async def _start(self) -> None:
        pass

    @abstractmethod
    async def _stop(self) -> None:
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

    async def handle_stream(
        self,
        reader: asyncio.StreamReader | mitmproxy_rs.Stream,
        writer: asyncio.StreamWriter | mitmproxy_rs.Stream,
    ) -> None:
        handler = ProxyConnectionHandler(
            ctx.master, reader, writer, ctx.options, self.mode
        )
        handler.layer = self.make_top_layer(handler.layer.context)
        if isinstance(self.mode, mode_specs.TransparentMode):
            assert isinstance(writer, asyncio.StreamWriter)
            s = cast(socket.socket, writer.get_extra_info("socket"))
            try:
                assert platform.original_addr
                original_dst = platform.original_addr(s)
            except Exception as e:
                logger.error(f"Transparent mode failure: {e!r}")
                writer.close()
                return
            else:
                handler.layer.context.client.sockname = original_dst
                handler.layer.context.server.address = original_dst
        elif isinstance(
            self.mode, (mode_specs.WireGuardMode, mode_specs.LocalMode)
        ):  # pragma: no cover on platforms without wg-test-client
            handler.layer.context.server.address = writer.get_extra_info(
                "remote_endpoint", handler.layer.context.client.sockname
            )

        with self.manager.register_connection(handler.layer.context.client.id, handler):
            await handler.handle_client()

    async def handle_udp_stream(self, stream: mitmproxy_rs.Stream) -> None:
        await self.handle_stream(stream, stream)


class AsyncioServerInstance(ServerInstance[M], metaclass=ABCMeta):
    _servers: list[asyncio.Server | mitmproxy_rs.UdpServer]

    def __init__(self, *args, **kwargs) -> None:
        self._servers = []
        super().__init__(*args, **kwargs)

    @property
    def is_running(self) -> bool:
        return bool(self._servers)

    @property
    def listen_addrs(self) -> tuple[Address, ...]:
        addrs = []
        for s in self._servers:
            if isinstance(s, mitmproxy_rs.UdpServer):
                addrs.append(s.getsockname())
            else:
                try:
                    addrs.extend(sock.getsockname() for sock in s.sockets)
                except OSError:  # pragma: no cover
                    pass  # this can fail during shutdown, see https://github.com/mitmproxy/mitmproxy/issues/6529
        return tuple(addrs)

    async def _start(self) -> None:
        assert not self._servers
        host = self.mode.listen_host(ctx.options.listen_host)
        port = self.mode.listen_port(ctx.options.listen_port)
        try:
            self._servers = await self.listen(host, port)
        except OSError as e:
            message = f"{self.mode.description} failed to listen on {host or '*'}:{port} with {e}"
            if e.errno == errno.EADDRINUSE and self.mode.custom_listen_port is None:
                assert (
                    self.mode.custom_listen_host is None
                )  # since [@ [listen_addr:]listen_port]
                message += f"\nTry specifying a different port by using `--mode {self.mode.full_spec}@{port + 2}`."
            raise OSError(e.errno, message, e.filename) from e

    async def _stop(self) -> None:
        assert self._servers
        try:
            for s in self._servers:
                s.close()
            # https://github.com/python/cpython/issues/104344
            # await asyncio.gather(*[s.wait_closed() for s in self._servers])
        finally:
            # we always reset _server and ignore failures
            self._servers = []

    async def listen(
        self, host: str, port: int
    ) -> list[asyncio.Server | mitmproxy_rs.UdpServer]:
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
                    return [
                        await asyncio.start_server(self.handle_stream, host, fixed_port)
                    ]
                except Exception as e:
                    logger.debug(
                        f"Failed to listen on a single port ({e!r}), falling back to default behavior."
                    )
            return [await asyncio.start_server(self.handle_stream, host, port)]
        elif self.mode.transport_protocol == "udp":
            # we start two servers for dual-stack support.
            # On Linux, this would also be achievable by toggling IPV6_V6ONLY off, but this here works cross-platform.
            if host == "":
                ipv4 = await mitmproxy_rs.start_udp_server(
                    "0.0.0.0",
                    port,
                    self.handle_udp_stream,
                )
                try:
                    ipv6 = await mitmproxy_rs.start_udp_server(
                        "::",
                        ipv4.getsockname()[1],
                        self.handle_udp_stream,
                    )
                except Exception:  # pragma: no cover
                    logger.debug("Failed to listen on '::', listening on IPv4 only.")
                    return [ipv4]
                else:  # pragma: no cover
                    return [ipv4, ipv6]
            return [
                await mitmproxy_rs.start_udp_server(
                    host,
                    port,
                    self.handle_udp_stream,
                )
            ]
        else:
            raise AssertionError(self.mode.transport_protocol)


class WireGuardServerInstance(ServerInstance[mode_specs.WireGuardMode]):
    _server: mitmproxy_rs.WireGuardServer | None = None

    server_key: str
    client_key: str

    def make_top_layer(
        self, context: Context
    ) -> Layer:  # pragma: no cover on platforms without wg-test-client
        return layers.modes.TransparentProxy(context)

    @property
    def is_running(self) -> bool:
        return self._server is not None

    @property
    def listen_addrs(self) -> tuple[Address, ...]:
        if self._server:
            return (self._server.getsockname(),)
        else:
            return tuple()

    async def _start(self) -> None:
        assert self._server is None
        host = self.mode.listen_host(ctx.options.listen_host)
        port = self.mode.listen_port(ctx.options.listen_port)

        if self.mode.data:
            conf_path = Path(self.mode.data).expanduser()
        else:
            conf_path = Path(ctx.options.confdir).expanduser() / "wireguard.conf"

        if not conf_path.exists():
            conf_path.parent.mkdir(parents=True, exist_ok=True)
            conf_path.write_text(
                json.dumps(
                    {
                        "server_key": mitmproxy_rs.genkey(),
                        "client_key": mitmproxy_rs.genkey(),
                    },
                    indent=4,
                )
            )

        try:
            c = json.loads(conf_path.read_text())
            self.server_key = c["server_key"]
            self.client_key = c["client_key"]
        except Exception as e:
            raise ValueError(f"Invalid configuration file ({conf_path}): {e}") from e
        # error early on invalid keys
        p = mitmproxy_rs.pubkey(self.client_key)
        _ = mitmproxy_rs.pubkey(self.server_key)

        self._server = await mitmproxy_rs.start_wireguard_server(
            host or "0.0.0.0",
            port,
            self.server_key,
            [p],
            self.wg_handle_stream,
            self.wg_handle_stream,
        )

        conf = self.client_conf()
        assert conf
        logger.info("-" * 60 + "\n" + conf + "\n" + "-" * 60)

    def client_conf(self) -> str | None:
        if not self._server:
            return None
        host = (
            self.mode.listen_host(ctx.options.listen_host)
            or local_ip.get_local_ip()
            or local_ip.get_local_ip6()
        )
        port = self.mode.listen_port(ctx.options.listen_port)
        return textwrap.dedent(
            f"""
            [Interface]
            PrivateKey = {self.client_key}
            Address = 10.0.0.1/32
            DNS = 10.0.0.53

            [Peer]
            PublicKey = {mitmproxy_rs.pubkey(self.server_key)}
            AllowedIPs = 0.0.0.0/0
            Endpoint = {host}:{port}
            """
        ).strip()

    def to_json(self) -> dict:
        return {"wireguard_conf": self.client_conf(), **super().to_json()}

    async def _stop(self) -> None:
        assert self._server is not None
        try:
            self._server.close()
            await self._server.wait_closed()
        finally:
            self._server = None

    async def wg_handle_stream(
        self, stream: mitmproxy_rs.Stream
    ) -> None:  # pragma: no cover on platforms without wg-test-client
        await self.handle_stream(stream, stream)


class LocalRedirectorInstance(ServerInstance[mode_specs.LocalMode]):
    _server: ClassVar[mitmproxy_rs.LocalRedirector | None] = None
    """The local redirector daemon. Will be started once and then reused for all future instances."""
    _instance: ClassVar[LocalRedirectorInstance | None] = None
    """The current LocalRedirectorInstance. Will be unset again if an instance is stopped."""
    listen_addrs = ()

    @property
    def is_running(self) -> bool:
        return self._instance is not None

    def make_top_layer(self, context: Context) -> Layer:
        return layers.modes.TransparentProxy(context)

    @classmethod
    async def redirector_handle_stream(
        cls,
        stream: mitmproxy_rs.Stream,
    ) -> None:
        if cls._instance is not None:
            await cls._instance.handle_stream(stream, stream)

    async def _start(self) -> None:
        if self._instance:
            raise RuntimeError("Cannot spawn more than one local redirector.")

        if self.mode.data.startswith("!"):
            spec = f"{self.mode.data},{os.getpid()}"
        elif self.mode.data:
            spec = self.mode.data
        else:
            spec = f"!{os.getpid()}"

        cls = self.__class__
        cls._instance = self  # assign before awaiting to avoid races
        if cls._server is None:
            try:
                cls._server = await mitmproxy_rs.start_local_redirector(
                    cls.redirector_handle_stream,
                    cls.redirector_handle_stream,
                )
            except Exception:
                cls._instance = None
                raise

        cls._server.set_intercept(spec)

    async def _stop(self) -> None:
        assert self._instance
        assert self._server
        self.__class__._instance = None
        # We're not shutting down the server because we want to avoid additional UAC prompts.
        self._server.set_intercept("")


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


# class Http3Instance(AsyncioServerInstance[mode_specs.Http3Mode]):
#     def make_top_layer(self, context: Context) -> Layer:
#         return layers.modes.HttpProxy(context)
