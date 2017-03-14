import socket
import os
import threading
import ssl
import OpenSSL
import pytest
from unittest import mock

from mitmproxy import connections
from mitmproxy import exceptions
from mitmproxy.net import tcp
from mitmproxy.net.http import http1
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from .net import tservers
from pathod import test


class TestClientConnection:

    def test_send(self):
        c = tflow.tclient_conn()
        c.send(b'foobar')
        c.send([b'foo', b'bar'])
        with pytest.raises(TypeError):
            c.send('string')
        with pytest.raises(TypeError):
            c.send(['string', 'not'])
        assert c.wfile.getvalue() == b'foobarfoobar'

    def test_repr(self):
        c = tflow.tclient_conn()
        assert 'address:22' in repr(c)
        assert 'ALPN' in repr(c)
        assert 'TLS' not in repr(c)

        c.alpn_proto_negotiated = None
        c.tls_established = True
        assert 'ALPN' not in repr(c)
        assert 'TLS' in repr(c)

    def test_tls_established_property(self):
        c = tflow.tclient_conn()
        c.tls_established = True
        assert c.ssl_established
        assert c.tls_established
        c.tls_established = False
        assert not c.ssl_established
        assert not c.tls_established

    def test_make_dummy(self):
        c = connections.ClientConnection.make_dummy(('foobar', 1234))
        assert c.address == ('foobar', 1234)

    def test_state(self):
        c = tflow.tclient_conn()
        assert connections.ClientConnection.from_state(c.get_state()).get_state() == \
            c.get_state()

        c2 = tflow.tclient_conn()
        c2.address = (c2.address[0], 4242)
        assert not c == c2

        c2.timestamp_start = 42
        c.set_state(c2.get_state())
        assert c.timestamp_start == 42

        c3 = c.copy()
        assert c3.get_state() != c.get_state()
        c.id = c3.id = "foo"
        assert c3.get_state() == c.get_state()

    def test_eq(self):
        c = tflow.tclient_conn()
        c2 = c.copy()
        assert c == c
        assert c != c2
        assert c != 42
        assert hash(c) != hash(c2)

class TestServerConnection:

    def test_send(self):
        c = tflow.tserver_conn()
        c.send(b'foobar')
        c.send([b'foo', b'bar'])
        with pytest.raises(TypeError):
            c.send('string')
        with pytest.raises(TypeError):
            c.send(['string', 'not'])
        assert c.wfile.getvalue() == b'foobarfoobar'

    def test_repr(self):
        c = tflow.tserver_conn()

        c.sni = 'foobar'
        c.tls_established = True
        c.alpn_proto_negotiated = b'h2'
        assert 'address:22' in repr(c)
        assert 'ALPN' in repr(c)
        assert 'TLS: foobar' in repr(c)

        c.sni = None
        c.tls_established = True
        c.alpn_proto_negotiated = None
        assert 'ALPN' not in repr(c)
        assert 'TLS' in repr(c)

        c.sni = None
        c.tls_established = False
        assert 'TLS' not in repr(c)

    def test_tls_established_property(self):
        c = tflow.tserver_conn()
        c.tls_established = True
        assert c.ssl_established
        assert c.tls_established
        c.tls_established = False
        assert not c.ssl_established
        assert not c.tls_established

    def test_make_dummy(self):
        c = connections.ServerConnection.make_dummy(('foobar', 1234))
        assert c.address == ('foobar', 1234)

    def test_simple(self):
        d = test.Daemon()
        c = connections.ServerConnection((d.IFACE, d.port))
        c.connect()
        f = tflow.tflow()
        f.server_conn = c
        f.request.path = "/p/200:da"

        # use this protocol just to assemble - not for actual sending
        c.wfile.write(http1.assemble_request(f.request))
        c.wfile.flush()

        assert http1.read_response(c.rfile, f.request, 1000)
        assert d.last_log()

        c.finish()
        d.shutdown()

    def test_terminate_error(self):
        d = test.Daemon()
        c = connections.ServerConnection((d.IFACE, d.port))
        c.connect()
        c.connection = mock.Mock()
        c.connection.recv = mock.Mock(return_value=False)
        c.connection.flush = mock.Mock(side_effect=exceptions.TcpDisconnect)
        c.finish()
        d.shutdown()

    def test_sni(self):
        c = connections.ServerConnection(('', 1234))
        with pytest.raises(ValueError, matches='sni must be str, not '):
            c.establish_ssl(None, b'foobar')

    def test_state(self):
        c = tflow.tserver_conn()
        c2 = c.copy()
        assert c2.get_state() != c.get_state()
        c.id = c2.id = "foo"
        assert c2.get_state() == c.get_state()

    def test_eq(self):
        c = tflow.tserver_conn()
        c2 = c.copy()
        assert c == c
        assert c != c2
        assert c != 42
        assert hash(c) != hash(c2)


class TestClientConnectionTLS:

    @pytest.mark.parametrize("sni", [
        None,
        "example.com"
    ])
    def test_tls_with_sni(self, sni):
        address = ('127.0.0.1', 0)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(address)
        sock.listen()
        address = sock.getsockname()

        def client_run():
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            s = socket.create_connection(address)
            s = ctx.wrap_socket(s, server_hostname=sni)
            s.send(b'foobar')
            s.shutdown(socket.SHUT_RDWR)
        threading.Thread(target=client_run).start()

        connection, client_address = sock.accept()
        c = connections.ClientConnection(connection, client_address, None)

        cert = tutils.test_data.path("mitmproxy/net/data/server.crt")
        key = OpenSSL.crypto.load_privatekey(
            OpenSSL.crypto.FILETYPE_PEM,
            open(tutils.test_data.path("mitmproxy/net/data/server.key"), "rb").read())
        c.convert_to_ssl(cert, key)
        assert c.connected()
        assert c.sni == sni
        assert c.tls_established
        assert c.rfile.read(6) == b'foobar'
        c.finish()


class TestServerConnectionTLS(tservers.ServerTestBase):
    ssl = True

    class handler(tcp.BaseHandler):
        def handle(self):
            self.finish()

    @pytest.mark.parametrize("clientcert", [
        None,
        tutils.test_data.path("mitmproxy/data/clientcert"),
        os.path.join(tutils.test_data.path("mitmproxy/data/clientcert"), "client.pem"),
    ])
    def test_tls(self, clientcert):
        c = connections.ServerConnection(("127.0.0.1", self.port))
        c.connect()
        c.establish_ssl(clientcert, "foo.com")
        assert c.connected()
        assert c.sni == "foo.com"
        assert c.tls_established
        c.close()
        c.finish()
