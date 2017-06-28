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
import typing

from mitmproxy.proxy.protocol2 import events, commands
from mitmproxy.proxy.protocol2.context import Client, Context
from mitmproxy.proxy.protocol2.context import Connection
from mitmproxy.proxy.protocol2.reverse_proxy import ReverseProxy


class StreamIO(typing.NamedTuple):
    r: asyncio.StreamReader
    w: asyncio.StreamWriter


class ConnectionHandler(metaclass=abc.ABCMeta):
    transports: typing.MutableMapping[Connection, StreamIO]

    def __init__(self, reader, writer):
        addr = writer.get_extra_info('peername')

        self.client = Client(addr)
        self.context = Context(self.client)

        # self.layer = ReverseProxy(self.context, ("localhost", 443))
        self.layer = ReverseProxy(self.context, ("localhost", 80))

        self.transports = {
            self.client: StreamIO(reader, writer)
        }

    def _debug(self, *args):
        print(*args)

    async def handle_client(self):
        self.server_event(events.Start())
        await self.handle_connection(self.client)

        self._debug("client connection done, closing transports!")

        if self.transports:
            await asyncio.wait([
                self.close_connection(x)
                for x in self.transports
            ])

        self._debug("transports closed!")

    async def close_connection(self, connection):
        io = self.transports.pop(connection, None)
        if not io:
            self._debug(f"Already closed: {connection}")
        self._debug(f"Closing {connection}")
        try:
            await io.w.drain()
            io.w.write_eof()
        except socket.error:
            pass
        io.w.close()

    async def handle_connection(self, connection):
        reader, writer = self.transports[connection]
        while True:
            try:
                data = await reader.read(4096)
            except socket.error:
                data = b""
            if data:
                self.server_event(events.DataReceived(connection, data))
            else:
                connection.connected = False
                if connection in self.transports:
                    await self.close_connection(connection)
                self.server_event(events.ConnectionClosed(connection))
                break

    async def open_connection(self, command: commands.OpenConnection):
        try:
            reader, writer = await asyncio.open_connection(
                *command.connection.address
            )
        except IOError as e:
            self.server_event(events.OpenConnectionReply(command, str(e)))
        else:
            self.transports[command.connection] = StreamIO(reader, writer)
            command.connection.connected = True
            self.server_event(events.OpenConnectionReply(command, None))
            await self.handle_connection(command.connection)

    @abc.abstractmethod
    async def handle_hook(self, hook: commands.Hook) -> None:
        pass

    def server_event(self, event: events.Event) -> None:
        self._debug(">>", event)
        layer_commands = self.layer.handle_event(event)
        for command in layer_commands:
            self._debug("<<", command)
            if isinstance(command, commands.OpenConnection):
                asyncio.ensure_future(
                    self.open_connection(command)
                )
            elif isinstance(command, commands.SendData):
                self.transports[command.connection].w.write(command.data)
            elif isinstance(command, commands.CloseConnection):
                asyncio.ensure_future(
                    self.close_connection(command.connection)
                )
            elif isinstance(command, commands.Hook):
                asyncio.ensure_future(
                    self.handle_hook(command)
                )
            else:
                raise RuntimeError(f"Unexpected event: {command}")


class SimpleConnectionHandler(ConnectionHandler):
    """Simple handler that does not process any hooks."""

    async def handle_hook(self, hook: commands.Hook) -> None:
        self.server_event(events.HookReply(hook, None))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()


    async def handle(reader, writer):
        await SimpleConnectionHandler(reader, writer).handle_client()


    coro = asyncio.start_server(handle, '127.0.0.1', 8080, loop=loop)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()
