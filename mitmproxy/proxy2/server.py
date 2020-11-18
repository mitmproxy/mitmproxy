"""
Proxy Server Implementation using asyncio.
The very high level overview is as follows:

    - Spawn one coroutine per client connection and create a reverse proxy layer to example.com
    - Process any commands from layer (such as opening a server connection)
    - Wait for any IO and send it as events to top layer.
"""
import abc
import asyncio
import socket
import time
import traceback
import typing
from contextlib import contextmanager
from dataclasses import dataclass

from OpenSSL import SSL
from mitmproxy import http, options as moptions
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import commands, events, layer, layers, server_hooks
from mitmproxy.proxy2.context import Client, Connection, ConnectionState, Context
from mitmproxy.proxy2.layers import tls
from mitmproxy.utils import human
from mitmproxy.utils.data import pkg_data


class TimeoutWatchdog:
    last_activity: float
    CONNECTION_TIMEOUT = 10 * 60
    can_timeout: asyncio.Event
    blocker: int

    def __init__(self, callback: typing.Callable[[], typing.Any]):
        self.callback = callback
        self.last_activity = time.time()
        self.can_timeout = asyncio.Event()
        self.can_timeout.set()
        self.blocker = 0

    def register_activity(self):
        self.last_activity = time.time()

    async def watch(self):
        while True:
            await self.can_timeout.wait()
            try:
                await asyncio.sleep(self.CONNECTION_TIMEOUT - (time.time() - self.last_activity))
            except asyncio.CancelledError:
                return
            if self.last_activity + self.CONNECTION_TIMEOUT < time.time():
                await self.callback()
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
    handler: typing.Optional[asyncio.Task] = None
    reader: typing.Optional[asyncio.StreamReader] = None
    writer: typing.Optional[asyncio.StreamWriter] = None


class ConnectionHandler(metaclass=abc.ABCMeta):
    transports: typing.MutableMapping[Connection, ConnectionIO]
    timeout_watchdog: TimeoutWatchdog
    client: Client

    def __init__(self, context: Context) -> None:
        self.client = context.client
        self.transports = {}

        # Ask for the first layer right away.
        # In a reverse proxy scenario, this is necessary as we would otherwise hang
        # on protocols that start with a server greeting.
        self.layer = layer.NextLayer(context, ask_on_start=True)
        self.timeout_watchdog = TimeoutWatchdog(self.on_timeout)

    async def handle_client(self) -> None:
        watch = asyncio.ensure_future(self.timeout_watchdog.watch())

        self.log("client connect")
        await self.handle_hook(server_hooks.ClientConnectedHook(self.client))
        if self.client.error:
            self.log("client kill connection")
            self.transports.pop(self.client).writer.close()
        else:
            handler = asyncio.create_task(
                self.handle_connection(self.client)
            )
            self.transports[self.client].handler = handler
            self.server_event(events.Start())
            await handler

        self.log("client disconnect")
        self.client.timestamp_end = time.time()
        await self.handle_hook(server_hooks.ClientClosedHook(self.client))
        watch.cancel()

        if self.transports:
            self.log("closing transports...", "debug")
            for x in self.transports.values():
                x.handler.cancel()
            await asyncio.wait([x.handler for x in self.transports.values()])
            self.log("transports closed!", "debug")

    async def open_connection(self, command: commands.OpenConnection) -> None:
        if not command.connection.address:
            raise ValueError("Cannot open connection, no hostname given.")

        hook_data = server_hooks.ServerConnectionHookData(
            client=self.client,
            server=command.connection
        )
        await self.handle_hook(server_hooks.ServerConnectHook(hook_data))
        if command.connection.error:
            self.log(f"server connection to {human.format_address(command.connection.address)} killed before connect.")
            self.server_event(events.OpenConnectionReply(command, "Connection killed."))
            return

        try:
            command.connection.timestamp_start = time.time()
            reader, writer = await asyncio.open_connection(*command.connection.address)
        except (IOError, asyncio.CancelledError) as e:
            self.log(f"error establishing server connection: {e}")
            command.connection.error = str(e)
            self.server_event(events.OpenConnectionReply(command, str(e)))
        else:
            command.connection.timestamp_tcp_setup = time.time()
            command.connection.state = ConnectionState.OPEN
            command.connection.peername = writer.get_extra_info('peername')
            command.connection.sockname = writer.get_extra_info('sockname')
            self.transports[command.connection].reader = reader
            self.transports[command.connection].writer = writer

            if command.connection.address[0] != command.connection.peername[0]:
                addr = f"{command.connection.address[0]} ({human.format_address(command.connection.peername)})"
            else:
                addr = human.format_address(command.connection.address)
            self.log(f"server connect {addr}")
            connected_hook = asyncio.create_task(self.handle_hook(server_hooks.ServerConnectedHook(hook_data)))

            self.server_event(events.OpenConnectionReply(command, None))
            try:
                await self.handle_connection(command.connection)
            finally:
                self.log(f"server disconnect {addr}")
                command.connection.timestamp_end = time.time()
                await connected_hook  # wait here for this so that closed always comes after connected.
                await self.handle_hook(server_hooks.ServerClosedHook(hook_data))

    async def handle_connection(self, connection: Connection) -> None:
        reader = self.transports[connection].reader
        assert reader
        try:
            while True:
                try:
                    data = await reader.read(65535)
                except socket.error:
                    data = b""
                except asyncio.CancelledError:
                    if connection.state & ConnectionState.CAN_WRITE:
                        self.close_our_end(connection)
                    data = b""
                if data:
                    self.server_event(events.DataReceived(connection, data))
                else:
                    connection.state &= ~ConnectionState.CAN_READ
                    self.server_event(events.ConnectionClosed(connection))
                    # we may still use this connection to *send* stuff,
                    # even though the remote has closed their side of the connection.
                    # to make this work we keep this task running and wait for cancellation.
                    if connection.state is ConnectionState.CLOSED:
                        self.transports[connection].handler.cancel()
                    await asyncio.Event().wait()
        except asyncio.CancelledError:
            connection.state = ConnectionState.CLOSED
            io = self.transports.pop(connection)
            io.writer.close()

    async def on_timeout(self) -> None:
        self.log(f"Closing connection due to inactivity: {self.client}")
        self.transports[self.client].handler.cancel()

    async def hook_task(self, hook: commands.Hook) -> None:
        await self.handle_hook(hook)
        if hook.blocking:
            self.server_event(events.HookReply(hook))

    @abc.abstractmethod
    async def handle_hook(self, hook: commands.Hook) -> None:
        pass

    def log(self, message: str, level: str = "info") -> None:
        print(message)

    def server_event(self, event: events.Event) -> None:
        self.timeout_watchdog.register_activity()
        try:
            layer_commands = self.layer.handle_event(event)
            for command in layer_commands:

                if isinstance(command, commands.OpenConnection):
                    assert command.connection not in self.transports
                    handler = asyncio.create_task(
                        self.open_connection(command)
                    )
                    self.transports[command.connection] = ConnectionIO(handler=handler)
                elif isinstance(command, commands.ConnectionCommand) and command.connection not in self.transports:
                    return  # The connection has already been closed.
                elif isinstance(command, commands.SendData):
                    self.transports[command.connection].writer.write(command.data)
                elif isinstance(command, commands.CloseConnection):
                    self.close_our_end(command.connection)
                elif isinstance(command, commands.GetSocket):
                    socket = self.transports[command.connection].writer.get_extra_info("socket")
                    self.server_event(events.GetSocketReply(command, socket))
                elif isinstance(command, commands.Hook):
                    asyncio.create_task(self.hook_task(command))
                elif isinstance(command, commands.Log):
                    self.log(command.message, command.level)
                else:
                    raise RuntimeError(f"Unexpected command: {command}")
        except Exception:
            self.log(f"mitmproxy has crashed!\n{traceback.format_exc()}", level="error")

    def close_our_end(self, connection):
        if connection.state is ConnectionState.CLOSED:
            return
        self.log(f"shutting down {connection}", "debug")
        try:
            self.transports[connection].writer.write_eof()
        except socket.error:
            connection.state = ConnectionState.CLOSED
        connection.state &= ~ConnectionState.CAN_WRITE

        # if we are closing the client connection, we should destroy everything.
        if connection == self.client:
            self.transports[connection].handler.cancel()
        # If we have already received a close, let's finish everything.
        elif connection.state is ConnectionState.CLOSED:
            self.transports[connection].handler.cancel()


class StreamConnectionHandler(ConnectionHandler, metaclass=abc.ABCMeta):
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, options: moptions.Options) -> None:
        client = Client(
            writer.get_extra_info('peername'),
            writer.get_extra_info('sockname'),
            time.time(),
        )
        context = Context(client, options)
        super().__init__(context)
        self.transports[client] = ConnectionIO(handler=None, reader=reader, writer=writer)


class SimpleConnectionHandler(StreamConnectionHandler):
    """Simple handler that does not really process any hooks."""

    hook_handlers: typing.Dict[str, typing.Callable]

    def __init__(self, reader, writer, options, hooks):
        super().__init__(reader, writer, options)
        self.hook_handlers = hooks

    async def handle_hook(
            self,
            hook: commands.Hook
    ) -> None:
        if hook.name in self.hook_handlers:
            self.hook_handlers[hook.name](*hook.as_tuple())

    def log(self, message: str, level: str = "info"):
        if "Hook" not in message:
            pass  # print(message, file=sys.stderr if level in ("error", "warn") else sys.stdout)


if __name__ == "__main__":
    # simple standalone implementation for testing.
    loop = asyncio.get_event_loop()

    opts = moptions.Options()
    # options duplicated here to simplify testing setup
    opts.add_option(
        "connection_strategy", str, "lazy",
        "Determine when server connections should be established.",
        choices=("eager", "lazy")
    )
    opts.add_option(
        "keep_host_header", bool, False,
        """
        Reverse Proxy: Keep the original host header instead of rewriting it
        to the reverse proxy target.
        """
    )
    opts.mode = "reverse:http://127.0.0.1:3000/"


    async def handle(reader, writer):
        layer_stack = [
            # lambda ctx: layers.ServerTLSLayer(ctx),
            # lambda ctx: layers.HttpLayer(ctx, HTTPMode.regular),
            # lambda ctx: setattr(ctx.server, "tls", True) or layers.ServerTLSLayer(ctx),
            # lambda ctx: layers.ClientTLSLayer(ctx),
            lambda ctx: layers.modes.ReverseProxy(ctx),
            lambda ctx: layers.HttpLayer(ctx, HTTPMode.transparent)
        ]

        def next_layer(nl: layer.NextLayer):
            nl.layer = layer_stack.pop(0)(nl.context)
            nl.layer.debug = "  " * len(nl.context.layers)

        def request(flow: http.HTTPFlow):
            if "cached" in flow.request.path:
                flow.response = http.HTTPResponse.make(418, f"(cached) {flow.request.text}")
            if "toggle-tls" in flow.request.path:
                if flow.request.url.startswith("https://"):
                    flow.request.url = flow.request.url.replace("https://", "http://")
                else:
                    flow.request.url = flow.request.url.replace("http://", "https://")
            if "redirect" in flow.request.path:
                flow.request.host = "httpbin.org"

        def tls_start(tls_start: tls.TlsStartData):
            # INSECURE
            ssl_context = SSL.Context(SSL.SSLv23_METHOD)
            if tls_start.conn == tls_start.context.client:
                ssl_context.use_privatekey_file(
                    pkg_data.path("../test/mitmproxy/data/verificationcerts/trusted-leaf.key")
                )
                ssl_context.use_certificate_chain_file(
                    pkg_data.path("../test/mitmproxy/data/verificationcerts/trusted-leaf.crt")
                )

            tls_start.ssl_conn = SSL.Connection(ssl_context)

            if tls_start.conn == tls_start.context.client:
                tls_start.ssl_conn.set_accept_state()
            else:
                tls_start.ssl_conn.set_connect_state()
                tls_start.ssl_conn.set_tlsext_host_name(tls_start.context.client.sni)

        await SimpleConnectionHandler(reader, writer, opts, {
            "next_layer": next_layer,
            "request": request,
            "tls_start": tls_start,
        }).handle_client()


    coro = asyncio.start_server(handle, '127.0.0.1', 8080, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print(f"Serving on {human.format_address(server.sockets[0].getsockname())}")
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
