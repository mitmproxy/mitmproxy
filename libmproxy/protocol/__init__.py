from ..proxy import ServerConnection, AddressPriority

KILL = 0  # const for killed requests

class ConnectionTypeChange(Exception):
    """
    Gets raised if the connetion type has been changed (e.g. after HTTP/1.1 101 Switching Protocols).
    It's up to the raising ProtocolHandler to specify the new conntype before raising the exception.
    """
    pass


class ProtocolHandler(object):
    def __init__(self, c):
        self.c = c
        """@type: libmproxy.proxy.ConnectionHandler"""

    def handle_messages(self):
        """
        This method gets called if a client connection has been made. Depending on the proxy settings,
        a server connection might already exist as well.
        """
        raise NotImplementedError  # pragma: nocover

    def handle_error(self, error):
        """
        This method gets called should there be an uncaught exception during the connection.
        This might happen outside of handle_messages, e.g. if the initial SSL handshake fails in transparent mode.
        """
        raise error  # pragma: nocover


class TemporaryServerChangeMixin(object):
    """
    This mixin allows safe modification of the target server,
    without any need to expose the ConnectionHandler to the Flow.
    """
    def change_server(self, address, ssl):
        if address == self.c.server_conn.address():
            return
        priority = AddressPriority.MANUALLY_CHANGED

        if self.c.server_conn.priority > priority:
            self.log("Attempt to change server address, "
                     "but priority is too low (is: %s, got: %s)" % (self.server_conn.priority, priority))
            return

        self.log("Temporarily change server connection: %s:%s -> %s:%s" % (
            self.c.server_conn.address.host,
            self.c.server_conn.address.port,
            address.host,
            address.port
        ))

        if not hasattr(self, "_backup_server_conn"):
            self._backup_server_conn = self.c.server_conn
            self.c.server_conn = None
        else:  # This is at least the second temporary change. We can kill the current connection.
            self.c.del_server_connection()

        self.c.set_server_address(address, priority)
        if ssl:
            self.establish_ssl(server=True)

    def restore_server(self):
        if not hasattr(self, "_backup_server_conn"):
            return

        self.log("Restore original server connection: %s:%s -> %s:%s" % (
            self.c.server_conn.address.host,
            self.c.server_conn.address.port,
            self._backup_server_conn.host,
            self._backup_server_conn.port
        ))

        self.c.del_server_connection()
        self.c.server_conn = self._backup_server_conn
        del self._backup_server_conn

from . import http, tcp

protocols = {
    'http': dict(handler=http.HTTPHandler, flow=http.HTTPFlow),
    'tcp': dict(handler=tcp.TCPHandler)
}  # PyCharm type hinting behaves bad if this is a dict constructor...


def _handler(conntype, connection_handler):
    if conntype in protocols:
        return protocols[conntype]["handler"](connection_handler)

    raise NotImplementedError   # pragma: nocover


def handle_messages(conntype, connection_handler):
    return _handler(conntype, connection_handler).handle_messages()


def handle_error(conntype, connection_handler, error):
    return _handler(conntype, connection_handler).handle_error(error)


