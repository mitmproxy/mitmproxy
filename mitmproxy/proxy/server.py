"""
Proxy Server Implementation using asyncio.
The very high level overview is as follows:

    - Spawn one coroutine per client connection and create a reverse proxy layer to example.com
    - Process any commands from layer (such as opening a server connection)
    - Wait for any IO and send it as events to top layer.
"""
import abc
import asyncio
import collections
import logging

import time
import traceback
from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Union

import mitmproxy_wireguard as wg
from OpenSSL import SSL

from mitmproxy import http, options as moptions, tls
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy import commands, events, layer, layers, mode_specs, server_hooks
from mitmproxy.connection import Address, Client, Connection, ConnectionState
from mitmproxy.net import udp
from mitmproxy.utils import asyncio_utils
from mitmproxy.utils import human
from mitmproxy.utils.data import pkg_data


logger = logging.getLogger(__name__)


class TimeoutWatchdog:
    last_activity: float
    CONNECTION_TIMEOUT = 10 * 60
    can_timeout: asyncio.Event
    blocker: int

    def __init__(self, callback: Callable[[], Awaitable]):
        self.callback = callback
        self.last_activity = time.time()
        self.can_timeout = asyncio.Event()
        self.can_timeout.set()
        self.blocker = 0

    def register_activity(self):
        self.last_activity = time.time()

    async def watch(self):
        try:
            while True:
                await self.can_timeout.wait()
                await asyncio.sleep(
                    self.CONNECTION_TIMEOUT - (time.time() - self.last_activity)
                )
                if self.last_activity + self.CONNECTION_TIMEOUT < time.time():
                    await self.callback()
                    return
        except asyncio.CancelledError:
            return

    @contextmanager
    def disarm(self):
        self.can_timeout.clear()
        self.blocker += 1
        try:
            yield
        finally:
            self.blocker -= 1
            if self.blocker == 0:
                self.register_activity()
                self.can_timeout.set()


@dataclass
class ConnectionIO:
    handler: Optional[asyncio.Task] = None
    reader: Optional[Union[asyncio.StreamReader, udp.DatagramReader, wg.TcpStream]] = None
    writer: Optional[Union[asyncio.StreamWriter, udp.DatagramWriter, wg.TcpStream]] = None


class ConnectionHandler(metaclass=abc.ABCMeta):
    transports: MutableMapping[Connection, ConnectionIO]
    timeout_watchdog: TimeoutWatchdog
    client: Client
    max_conns: collections.defaultdict[Address, asyncio.Semaphore]
    layer: "layer.Layer"
    wakeup_timer: set[asyncio.Task]

    def __init__(self, context: Context) -> None:
        self.client = context.client
        self.transports = {}
        self.max_conns = collections.defaultdict(lambda: asyncio.Semaphore(5))
        self.wakeup_timer = set()

        # Ask for the first layer right away.
        # In a reverse proxy scenario, this is necessary as we would otherwise hang
        # on protocols that start with a server greeting.
        self.layer = layer.NextLayer(context, ask_on_start=True)
        self.timeout_watchdog = TimeoutWatchdog(self.on_timeout)

        # workaround for https://bugs.python.org/issue40124 / https://bugs.python.org/issue29930
        self._drain_lock = asyncio.Lock()

    async def handle_client(self) -> None:
        asyncio_utils.set_current_task_debug_info(
            name=f"client handler",
            client=self.client.peername,
        )
        watch = asyncio_utils.create_task(
            self.timeout_watchdog.watch(),
            name="timeout watchdog",
            client=self.client.peername,
        )

        self.log("client connect")
        await self.handle_hook(server_hooks.ClientConnectedHook(self.client))
        if self.client.error:
            self.log("client kill connection")
            writer = self.transports.pop(self.client).writer
            assert writer
            writer.close()
        else:
            handler = asyncio_utils.create_task(
                self.handle_connection(self.client),
                name=f"client connection handler",
                client=self.client.peername,
            )
            self.transports[self.client].handler = handler
            self.server_event(events.Start())
            await asyncio.wait([handler])
            if not handler.cancelled() and (e := handler.exception()):
                self.log(f"mitmproxy has crashed!\n{traceback.format_exception(e)}", logging.ERROR)

        watch.cancel()
        while self.wakeup_timer:
            timer = self.wakeup_timer.pop()
            timer.cancel()

        self.log("client disconnect")
        self.client.timestamp_end = time.time()
        await self.handle_hook(server_hooks.ClientDisconnectedHook(self.client))

        if self.transports:
            self.log("closing transports...", logging.DEBUG)
            for io in self.transports.values():
                if io.handler:
                    io.handler.cancel("client disconnected")
            await asyncio.wait(
                [x.handler for x in self.transports.values() if x.handler]
            )
            self.log("transports closed!", logging.DEBUG)

    async def open_connection(self, command: commands.OpenConnection) -> None:
        if not command.connection.address:
            self.log(f"Cannot open connection, no hostname given.")
            self.server_event(
                events.OpenConnectionCompleted(
                    command, f"Cannot open connection, no hostname given."
                )
            )
            return

        hook_data = server_hooks.ServerConnectionHookData(
            client=self.client, server=command.connection
        )
        await self.handle_hook(server_hooks.ServerConnectHook(hook_data))
        if err := command.connection.error:
            self.log(
                f"server connection to {human.format_address(command.connection.address)} killed before connect: {err}"
            )
            self.server_event(
                events.OpenConnectionCompleted(command, f"Connection killed: {err}")
            )
            return

        async with self.max_conns[command.connection.address]:
            reader: Union[asyncio.StreamReader, udp.DatagramReader]
            writer: Union[asyncio.StreamWriter, udp.DatagramWriter]
            try:
                command.connection.timestamp_start = time.time()
                if command.connection.transport_protocol == "tcp":
                    reader, writer = await asyncio.open_connection(
                        *command.connection.address,
                        local_addr=command.connection.sockname,
                    )
                elif command.connection.transport_protocol == "udp":
                    reader, writer = await udp.open_connection(
                        *command.connection.address,
                        local_addr=command.connection.sockname,
                    )
                else:
                    raise AssertionError(command.connection.transport_protocol)
            except (OSError, asyncio.CancelledError) as e:
                err = str(e)
                if not err:  # str(CancelledError()) returns empty string.
                    err = "connection cancelled"
                self.log(f"error establishing server connection: {err}")
                command.connection.error = err
                self.server_event(events.OpenConnectionCompleted(command, err))
                if isinstance(e, asyncio.CancelledError):
                    # From https://docs.python.org/3/library/asyncio-exceptions.html#asyncio.CancelledError:
                    # > In almost all situations the exception must be re-raised.
                    # It is not really defined what almost means here, but we play safe.
                    raise
            else:
                if command.connection.transport_protocol == "tcp":
                    # TODO: Rename to `timestamp_setup` and make it agnostic for both TCP (SYN/ACK) and UDP (DNS resl.)
                    command.connection.timestamp_tcp_setup = time.time()
                command.connection.state = ConnectionState.OPEN
                command.connection.peername = writer.get_extra_info("peername")
                command.connection.sockname = writer.get_extra_info("sockname")
                self.transports[command.connection].reader = reader
                self.transports[command.connection].writer = writer

                assert command.connection.peername
                if command.connection.address[0] != command.connection.peername[0]:
                    addr = f"{human.format_address(command.connection.address)} ({human.format_address(command.connection.peername)})"
                else:
                    addr = human.format_address(command.connection.address)
                self.log(f"server connect {addr}")
                await self.handle_hook(server_hooks.ServerConnectedHook(hook_data))
                self.server_event(events.OpenConnectionCompleted(command, None))

                # during connection opening, this function is the designated handler that can be cancelled.
                # once we have a connection, we do want the teardown here to happen in any case, so we
                # reassign the handler to .handle_connection and then clean up here once that is done.
                new_handler = asyncio_utils.create_task(
                    self.handle_connection(command.connection),
                    name=f"server connection handler for {addr}",
                    client=self.client.peername,
                )
                self.transports[command.connection].handler = new_handler
                await asyncio.wait([new_handler])

                self.log(f"server disconnect {addr}")
                command.connection.timestamp_end = time.time()
                await self.handle_hook(server_hooks.ServerDisconnectedHook(hook_data))

    async def wakeup(self, request: commands.RequestWakeup) -> None:
        await asyncio.sleep(request.delay)
        task = asyncio.current_task()
        assert task is not None
        self.wakeup_timer.discard(task)
        self.server_event(events.Wakeup(request))

    async def handle_connection(self, connection: Connection) -> None:
        """
        Handle a connection for its entire lifetime.
        This means we read until EOF,
        but then possibly also keep on waiting for our side of the connection to be closed.
        """
        cancelled = None
        reader = self.transports[connection].reader
        assert reader
        while True:
            try:
                data = await reader.read(65535)
                if not data:
                    raise OSError("Connection closed by peer.")
            except OSError:
                break
            except asyncio.CancelledError as e:
                cancelled = e
                break

            self.server_event(events.DataReceived(connection, data))

            try:
                await self.drain_writers()
            except asyncio.CancelledError as e:
                cancelled = e
                break

        if cancelled is None:
            connection.state &= ~ConnectionState.CAN_READ
        else:
            connection.state = ConnectionState.CLOSED

        self.server_event(events.ConnectionClosed(connection))

        if cancelled is None and connection.state is ConnectionState.CAN_WRITE:
            # we may still use this connection to *send* stuff,
            # even though the remote has closed their side of the connection.
            # to make this work we keep this task running and wait for cancellation.
            await asyncio.Event().wait()

        try:
            writer = self.transports[connection].writer
            assert writer
            writer.close()
        except OSError:
            pass
        self.transports.pop(connection)

        if cancelled:
            raise cancelled

    async def drain_writers(self):
        """
        Drain all writers to create some backpressure. We won't continue reading until there's space available in our
        write buffers, so if we cannot write fast enough our own read buffers run full and the TCP recv stream is throttled.
        """
        async with self._drain_lock:
            for transport in self.transports.values():
                if transport.writer is not None:
                    try:
                        await transport.writer.drain()
                    except OSError as e:
                        if transport.handler is not None:
                            transport.handler.cancel(f"Error sending data: {e}")

    async def on_timeout(self) -> None:
        self.log(f"Closing connection due to inactivity: {self.client}")
        handler = self.transports[self.client].handler
        assert handler
        handler.cancel("timeout")

    async def hook_task(self, hook: commands.StartHook) -> None:
        await self.handle_hook(hook)
        if hook.blocking:
            self.server_event(events.HookCompleted(hook))

    @abc.abstractmethod
    async def handle_hook(self, hook: commands.StartHook) -> None:
        pass

    def log(self, message: str, level: int = logging.INFO) -> None:
        logger.log(
            level,
            message,
            extra={"client": self.client.peername}
        )

    def server_event(self, event: events.Event) -> None:
        self.timeout_watchdog.register_activity()
        try:
            layer_commands = self.layer.handle_event(event)
            for command in layer_commands:

                if isinstance(command, commands.OpenConnection):
                    assert command.connection not in self.transports
                    handler = asyncio_utils.create_task(
                        self.open_connection(command),
                        name=f"server connection manager {command.connection.address}",
                        client=self.client.peername,
                    )
                    self.transports[command.connection] = ConnectionIO(handler=handler)
                elif isinstance(command, commands.RequestWakeup):
                    task = asyncio_utils.create_task(
                        self.wakeup(command),
                        name=f"wakeup timer ({command.delay:.1f}s)",
                        client=self.client.peername,
                    )
                    assert task is not None
                    self.wakeup_timer.add(task)
                elif (
                    isinstance(command, commands.ConnectionCommand)
                    and command.connection not in self.transports
                ):
                    pass  # The connection has already been closed.
                elif isinstance(command, commands.SendData):
                    writer = self.transports[command.connection].writer
                    assert writer
                    if not writer.is_closing():
                        writer.write(command.data)
                elif isinstance(command, commands.CloseConnection):
                    self.close_connection(command.connection, command.half_close)
                elif isinstance(command, commands.StartHook):
                    asyncio_utils.create_task(
                        self.hook_task(command),
                        name=f"handle_hook({command.name})",
                        client=self.client.peername,
                    )
                elif isinstance(command, commands.Log):
                    self.log(command.message, command.level)
                else:
                    raise RuntimeError(f"Unexpected command: {command}")
        except Exception:
            self.log(f"mitmproxy has crashed!\n{traceback.format_exc()}", logging.ERROR)

    def close_connection(
        self, connection: Connection, half_close: bool = False
    ) -> None:
        if half_close:
            if not connection.state & ConnectionState.CAN_WRITE:
                return
            self.log(f"half-closing {connection}", logging.DEBUG)
            try:
                writer = self.transports[connection].writer
                assert writer
                if not writer.is_closing():
                    writer.write_eof()
            except OSError:
                # if we can't write to the socket anymore we presume it completely dead.
                connection.state = ConnectionState.CLOSED
            else:
                connection.state &= ~ConnectionState.CAN_WRITE
        else:
            connection.state = ConnectionState.CLOSED

        if connection.state is ConnectionState.CLOSED:
            handler = self.transports[connection].handler
            assert handler
            handler.cancel("closed by command")


class LiveConnectionHandler(ConnectionHandler, metaclass=abc.ABCMeta):
    def __init__(
        self,
        reader: Union[asyncio.StreamReader, wg.TcpStream],
        writer: Union[asyncio.StreamWriter, wg.TcpStream],
        options: moptions.Options,
        mode: mode_specs.ProxyMode,
    ) -> None:
        client = Client(
            writer.get_extra_info("peername"),
            writer.get_extra_info("sockname"),
            time.time(),
            proxy_mode=mode,
        )
        context = Context(client, options)
        super().__init__(context)
        self.transports[client] = ConnectionIO(
            handler=None, reader=reader, writer=writer
        )


class SimpleConnectionHandler(LiveConnectionHandler):  # pragma: no cover
    """Simple handler that does not really process any hooks."""

    hook_handlers: dict[str, Callable]

    def __init__(self, reader, writer, options, mode, hooks):
        super().__init__(reader, writer, options, mode)
        self.hook_handlers = hooks

    async def handle_hook(self, hook: commands.StartHook) -> None:
        if hook.name in self.hook_handlers:
            self.hook_handlers[hook.name](*hook.args())


if __name__ == "__main__":  # pragma: no cover
    # simple standalone implementation for testing.
    loop = asyncio.get_event_loop()

    opts = moptions.Options()
    # options duplicated here to simplify testing setup
    opts.add_option(
        "connection_strategy",
        str,
        "lazy",
        "Determine when server connections should be established.",
        choices=("eager", "lazy"),
    )
    opts.add_option(
        "keep_host_header",
        bool,
        False,
        """
        Reverse Proxy: Keep the original host header instead of rewriting it
        to the reverse proxy target.
        """,
    )

    async def handle(reader, writer):
        layer_stack = [
            # lambda ctx: layers.ServerTLSLayer(ctx),
            # lambda ctx: layers.HttpLayer(ctx, HTTPMode.regular),
            # lambda ctx: setattr(ctx.server, "tls", True) or layers.ServerTLSLayer(ctx),
            # lambda ctx: layers.ClientTLSLayer(ctx),
            lambda ctx: layers.modes.ReverseProxy(ctx),
            lambda ctx: layers.HttpLayer(ctx, HTTPMode.transparent),
        ]

        def next_layer(nl: layer.NextLayer):
            l = layer_stack.pop(0)(nl.context)
            l.debug = "  " * len(nl.context.layers)
            nl.layer = l

        def request(flow: http.HTTPFlow):
            if "cached" in flow.request.path:
                flow.response = http.Response.make(418, f"(cached) {flow.request.text}")
            if "toggle-tls" in flow.request.path:
                if flow.request.url.startswith("https://"):
                    flow.request.url = flow.request.url.replace("https://", "http://")
                else:
                    flow.request.url = flow.request.url.replace("http://", "https://")
            if "redirect" in flow.request.path:
                flow.request.host = "httpbin.org"

        def tls_start_client(tls_start: tls.TlsData):
            # INSECURE
            ssl_context = SSL.Context(SSL.SSLv23_METHOD)
            ssl_context.use_privatekey_file(
                pkg_data.path(
                    "../test/mitmproxy/data/verificationcerts/trusted-leaf.key"
                )
            )
            ssl_context.use_certificate_chain_file(
                pkg_data.path(
                    "../test/mitmproxy/data/verificationcerts/trusted-leaf.crt"
                )
            )
            tls_start.ssl_conn = SSL.Connection(ssl_context)
            tls_start.ssl_conn.set_accept_state()

        def tls_start_server(tls_start: tls.TlsData):
            # INSECURE
            ssl_context = SSL.Context(SSL.SSLv23_METHOD)
            tls_start.ssl_conn = SSL.Connection(ssl_context)
            tls_start.ssl_conn.set_connect_state()
            if tls_start.context.client.sni is not None:
                tls_start.ssl_conn.set_tlsext_host_name(
                    tls_start.context.client.sni.encode()
                )

        await SimpleConnectionHandler(
            reader,
            writer,
            opts,
            mode_specs.ProxyMode.parse("reverse:http://127.0.0.1:3000/"),
            {
                "next_layer": next_layer,
                "request": request,
                "tls_start_client": tls_start_client,
                "tls_start_server": tls_start_server,
            },
        ).handle_client()

    coro = asyncio.start_server(handle, "127.0.0.1", 8080, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    assert server.sockets
    print(f"Serving on {human.format_address(server.sockets[0].getsockname())}")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
