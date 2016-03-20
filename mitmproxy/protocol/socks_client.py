import socket
import six
import sys

from netlib.exceptions import TcpException
from netlib import (tcp, socks)
from netlib.socks import (
    METHOD, VERSION, CMD, USERNAME_PASSWORD_VERSION, REP,
    UsernamePasswordAuth, UsernamePasswordAuthResponse,
    ClientGreeting, ServerGreeting, Message, SocksError
)

from .base import (Layer, ProxyServerConnection)
from ..exceptions import ProtocolException

class SocksClientLayer(Layer):

    def __init__(self, ctx, server_tls):
        super(SocksClientLayer, self).__init__(ctx)
        self.server_conn = ProxyServerConnection(
            self.ctx.server_conn.address,
            self.ctx
        )
        self.server_tls = server_tls
        self.socks_address = tcp.Address((u"127.0.0.1", 1080))
        self.ctx.set_server(self.socks_address)
        self.socks_username = "test"
        self.socks_password = "test"

    def __call__(self):
        layer = self.ctx.next_layer(self)
        layer()

    def _socks_username_password_auth(self):
        rfile, wfile = self.server_conn.rfile, self.server_conn.wfile
        cauth = UsernamePasswordAuth(USERNAME_PASSWORD_VERSION.DEFAULT, self.socks_username, self.socks_password)
        cauth.to_file(wfile)
        wfile.flush()
        sauth = UsernamePasswordAuthResponse.from_file(rfile)
        if sauth.status != 0:
            raise SocksError(0, "authentication failed")

    def set_server(self, address, server_tls=None, sni=None):
        self.server_conn = ProxyServerConnection(address, self.ctx)
        self.ctx.set_server(self.socks_address, server_tls, sni)

    def connect(self):
        if self.server_conn.address is None:
            raise ProtocolException("Cannot connect to server, no server address given.")
        try:
            self.ctx.connect()
            rfile, wfile = self.server_conn.rfile, self.server_conn.wfile
            methods = [METHOD.NO_AUTHENTICATION_REQUIRED]
            if self.socks_username is not None and self.socks_password is not None:
                methods.append(METHOD.USERNAME_PASSWORD)
            cgreeting = ClientGreeting(VERSION.SOCKS5, methods)
            cgreeting.to_file(wfile)
            wfile.flush()
            sgreeting = ServerGreeting.from_file(rfile)
            if sgreeting.method not in methods:
                raise SocksError(sgreeting.method, "No acceptable authentication methods")
            if sgreeting.method == socks.METHOD.USERNAME_PASSWORD:
                self._socks_username_password_auth()
            atyp = socks.get_address_atyp(self.server_conn.address)
            cmsg = Message(VERSION.SOCKS5, CMD.CONNECT, atyp, self.server_conn.address)
            cmsg.to_file(wfile)
            wfile.flush()
            smsg = Message.from_file(rfile)
            if smsg.msg != REP.SUCCEEDED:
                raise SocksError(smsg.msg, "Connect fail")
        except (TcpException, SocksError) as e:
            six.reraise(
                ProtocolException,
                ProtocolException(
                    "Server connection to server {} pass socks5 proxy {} failed: {}".format(
                        repr(self.server_conn.address), repr(self.server_conn.via.address), str(e)
                    )
                ),
                sys.exc_info()[2]
            )
