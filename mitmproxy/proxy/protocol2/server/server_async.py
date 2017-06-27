"""
Proxy Server Implementation using asyncio.
The very high level overview is as follows:

    - Spawn one coroutine per client connection and create a reverse proxy layer to example.com
    - Process any commands from layer (such as opening a server connection)
    - Wait for any IO and send it as events to top layer.
"""
import asyncio
import collections
import socket
from typing import MutableMapping

from mitmproxy.proxy.protocol2 import events, commands
from mitmproxy.proxy.protocol2.context import Client, Context
from mitmproxy.proxy.protocol2.context import Connection
from mitmproxy.proxy.protocol2.reverse_proxy import ReverseProxy

StreamIO = collections.namedtuple('StreamIO', ['r', 'w'])


class ConnectionHandler:
    def __init__(self, reader, writer):
        addr = writer.get_extra_info('peername')

        self.client = Client(addr)
        self.context = Context(self.client)

        # self.layer = ReverseProxy(self.context, ("localhost", 443))
        self.layer = ReverseProxy(self.context, ("localhost", 80))

        self.transports: MutableMapping[Connection, StreamIO] = {
            self.client: StreamIO(reader, writer)
        }

        self.lock = asyncio.Lock()

    async def handle_client(self):
        await self.server_event(events.Start())
        await self.handle_connection(self.client)

        print("client connection done, closing transports!")

        if self.transports:
            await asyncio.wait([
                self.close_connection(x)
                for x in self.transports
            ])

        print("transports closed!")

    async def close_connection(self, connection):
        io = self.transports.pop(connection, None)
        if not io:
            print(f"Already closed: {connection}")
        print(f"Closing {connection}")
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
                await self.server_event(events.DataReceived(connection, data))
            else:
                connection.connected = False
                if connection in self.transports:
                    await self.close_connection(connection)
                await self.server_event(events.ConnectionClosed(connection))
                break

    async def open_connection(self, command: commands.OpenConnection):
        reader, writer = await asyncio.open_connection(
            *command.connection.address
        )
        self.transports[command.connection] = StreamIO(reader, writer)
        command.connection.connected = True
        await self.server_event(events.OpenConnectionReply(command, None))
        await self.handle_connection(command.connection)

    async def server_event(self, event: events.Event):
        print("*", type(event).__name__)
        async with self.lock:
            print("<#", event)
            layer_commands = self.layer.handle_event(event)
            for command in layer_commands:
                print("<<", command)
                if isinstance(command, commands.OpenConnection):
                    asyncio.ensure_future(self.open_connection(command))
                elif isinstance(command, commands.SendData):
                    self.transports[command.connection].w.write(command.data)
                elif isinstance(command, commands.Hook):
                    # TODO: pass to master here.
                    print(f"~ {command.name}: {command.data}")
                    asyncio.ensure_future(
                        self.server_event(events.HookReply(command, None))
                    )
                elif isinstance(command, commands.CloseConnection):
                    asyncio.ensure_future(
                        self.close_connection(command.connection)
                    )
                else:
                    raise NotImplementedError(f"Unexpected event: {command}")
            print("#>")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()


    async def handle(reader, writer):
        await ConnectionHandler(reader, writer).handle_client()


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
