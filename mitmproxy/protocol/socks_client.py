import socket

from netlib import socks
from netlib.exceptions import TcpException
from netlib import tcp

from .base import Layer
from ..exceptions import ProtocolException

class SocksClientLayer(Layer):

    def __init__(self, ctx, server_tls):
        Layer.__init__(self, ctx)
        self.server_tls = server_tls
        self.socks_addr = tcp.Address(("127.0.0.1", 1080))
        self.socks_username = "test"
        self.socks_password = "test"

    def __call__(self):
        layer = self.ctx.next_layer(self)
        layer()

    def _socks_username_password_auth(self, rfile, wfile):
        if self.socks_username is None or self.socks_password is None:
            raise socks.SocksError(0, "authentication failed")
        cauth = socks.UsernamePasswordAuth(socks.USERNAME_PASSWORD_VERSION.DEFAULT, self.socks_username, self.socks_password)
        cauth.to_file(wfile)
        wfile.flush()
        sauth = socks.UsernamePasswordAuthResponse.from_file(rfile)
        if sauth.status != 0:
            raise socks.SocksError(0, "authentication failed")

    def _get_atype(self, address):
        try:
            if address.use_ipv6:
                taddr = socket.inet_pton(socket.AF_INET6, address.host)
                return socks.ATYP.IPV4_ADDRESS
            else:
                taddr = socket.inet_aton(address.host)
                return socks.ATYP.IPV6_ADDRESS
        except:
            return socks.ATYP.DOMAINNAME

    def set_server(self, address, server_tls=None, sni=None):
        self.target_address = address;
        self.ctx.set_server(address, server_tls, sni)

    def connect(self):
        if not self.target_address:
            raise ProtocolException("Cannot connect to server, no server address given.")
        self.server_conn.address = self.socks_addr
        try:
            self.server_conn.connect()
            rfile, wfile = self.server_conn.rfile, self.server_conn.wfile
            method = (socks.METHOD.NO_AUTHENTICATION_REQUIRED,)
            if self.socks_username is not None and self.socks_password is not None:
                method = (socks.METHOD.NO_AUTHENTICATION_REQUIRED, socks.METHOD.USERNAME_PASSWORD)
            cgreeting = socks.ClientGreeting(socks.VERSION.SOCKS5, method)
            cgreeting.to_file(wfile)
            wfile.flush()
            sgreeting = socks.ServerGreeting.from_file(rfile)
            if sgreeting.method == socks.METHOD.NO_ACCEPTABLE_METHODS:
                raise socks.SocksError(sgreeting.method, "no acceptable methods")
            if sgreeting.method == socks.METHOD.USERNAME_PASSWORD:
                self._socks_username_password_auth(rfile, wfile)
            atype = self._get_atype(self.target_address)
            cmsg = socks.Message(socks.VERSION.SOCKS5, socks.CMD.CONNECT, atype, self.target_address)
            cmsg.to_file(wfile)
            wfile.flush()
            smsg = socks.Message.from_file(rfile)
            if smsg.msg != socks.REP.SUCCEEDED:
                raise socks.SocksError(smsg.msg, "connect fail")
        except (TcpException, socks.SocksError) as e:
            six.reraise(
                ProtocolException,
                ProtocolException(
                    "Server connection to socks5 proxy {} failed: {}".format(
                        repr(self.server_conn.address), str(e)
                    )
                ),
                sys.exc_info()[2]
            )
