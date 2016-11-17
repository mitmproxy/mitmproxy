"""
Minimal server implementation based on https://docs.python.org/3/library/selectors.html#examples.
May be worth to replace this with something asyncio-based to overcome the issues outlined by the
FIXMEs below.
"""
import functools
import selectors
import socket
from typing import MutableMapping

from mitmproxy.proxy.protocol2 import events
from mitmproxy.proxy.protocol2.context import Connection
from mitmproxy.proxy.protocol2.context import Context, Client
from mitmproxy.proxy.protocol2.reverse_proxy import ReverseProxy


class TCPServer:
    def __init__(self, address):
        self.connections = {}  # type: MutableMapping[Connection, socket.socket]

        self.sel = selectors.DefaultSelector()
        sock = socket.socket()
        sock.bind(address)
        sock.listen(100)
        sock.setblocking(False)
        self.sel.register(sock, selectors.EVENT_READ, self.accept)

    def accept(self, server_sock, mask):
        sock, addr = server_sock.accept()  # Should be ready
        sock.setblocking(False)

        client = Client(addr)
        context = Context(client)
        layer = ReverseProxy(context, ("example.com", 80))

        self.receive_event(layer, events.Start())

        callback = functools.partial(self.read, layer, client)

        self.sel.register(
            sock,
            selectors.EVENT_READ,
            callback
        )

        self.connections[client] = sock

    def read(self, layer, conn, sock, mask):
        data = sock.recv(4096)  # Should be ready
        if data:
            self.receive_event(layer, events.ReceiveData(conn, data))
        else:
            # TODO: Needs proper teardown.
            self.sel.unregister(sock)
            sock.close()
            self.receive_event(layer, events.CloseConnection(conn))

    def receive_event(self, layer, event):
        print(">>", event)
        layer_events = layer.handle_event(event)
        for event in layer_events:
            print("<<", event)
            if isinstance(event, events.OpenConnection):
                # FIXME: This is blocking!
                sock = socket.create_connection(event.connection.address)
                sock.setblocking(False)
                event.connection.connected = True
                layer_events.send(42)
                callback = functools.partial(self.read, layer, event.connection)
                self.sel.register(
                    sock,
                    selectors.EVENT_READ,
                    callback
                )
                self.connections[event.connection] = sock
            elif isinstance(event, events.SendData):
                # FIXME: This may fail.
                self.connections[event.connection].sendall(event.data)
            else:
                raise NotImplementedError("Unexpected event: {}".format(event))

    def run(self):
        while True:
            events = self.sel.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)


if __name__ == '__main__':
    s = TCPServer(('', 8080))
    s.run()
