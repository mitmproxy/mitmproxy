from netlib import tcp
from time import sleep
import tutils, socket

"""
    Note that the choice of response code in these tests matters more than you
    might think. libcurl treats a 304 response code differently from, say, a
    200 response code - it will correctly terminate a 304 response with no
    content-length header, whereas it will block forever waiting for content
    for a 200 response.
"""

class SanityMixin:
    def test_http(self):
        assert self.pathod("304").status_code == 304
        assert self.master.state.view

    def test_large(self):
        assert len(self.pathod("200:b@50k").content) == 1024*50

    def test_replay(self):
        assert self.pathod("304").status_code == 304
        assert len(self.master.state.view) == 1
        l = self.master.state.view[0]
        assert l.response.code == 304
        l.request.path = "/p/305"
        rt = self.master.replay_request(l, block=True)
        assert l.response.code == 305

        # Disconnect error
        l.request.path = "/p/305:d0"
        rt = self.master.replay_request(l, block=True)
        assert l.error

        # Port error
        l.request.port = 1
        self.master.replay_request(l, block=True)
        assert l.error


class TestHTTP(tutils.HTTPProxTest, SanityMixin):
    def test_invalid_http(self):
        t = tcp.TCPClient("127.0.0.1", self.proxy.port)
        t.connect()
        t.wfile.write("invalid\n\n")
        t.wfile.flush()
        assert "Bad Request" in t.rfile.readline()

    def test_invalid_connect(self):
        t = tcp.TCPClient("127.0.0.1", self.proxy.port)
        t.connect()
        t.wfile.write("CONNECT invalid\n\n")
        t.wfile.flush()
        assert "Bad Request" in t.rfile.readline()


class TestHTTPS(tutils.HTTPProxTest, SanityMixin):
    ssl = True


class TestReverse(tutils.ReverseProxTest, SanityMixin):
    reverse = True


class TestTransparent(tutils.TransparentProxTest, SanityMixin):
    transparent = True


class TestProxy(tutils.HTTPProxTest):
    def test_http(self):
        f = self.pathod("304")
        assert f.status_code == 304

        l = self.master.state.view[0]
        assert l.request.client_conn.address
        assert "host" in l.request.headers
        assert l.response.code == 304

    def test_response_timestamps(self):
        # test that we notice at least 2 sec delay between timestamps
        # in response object
        f = self.pathod("304:b@1k:p50,2")
        assert f.status_code == 304

        response = self.master.state.view[0].response
        assert 2 <= response.timestamp_end - response.timestamp_start <= 2.2

    def test_request_timestamps(self):
        # test that we notice at least 2 sec delay between timestamps
        # in request object
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect(("127.0.0.1", self.proxy.port))

        # call pathod server, wait a second to complete the request
        connection.send("GET http://localhost:%d/p/304:b@1k HTTP/1.1\r\n"%self.server.port)
        sleep(2.1)
        connection.send("\r\n");
        connection.recv(50000)
        connection.close()

        request, response = self.master.state.view[0].request, self.master.state.view[0].response
        assert response.code == 304  # sanity test for our low level request
        assert 2 <= request.timestamp_end - request.timestamp_start <= 2.2

    def test_request_timestamps_not_affected_by_client_time(self):
        # test that don't include user wait time in request's timestamps

        f = self.pathod("304:b@10k")
        assert f.status_code == 304
        sleep(1)
        f = self.pathod("304:b@10k")
        assert f.status_code == 304

        request = self.master.state.view[0].request
        assert request.timestamp_end - request.timestamp_start <= 0.1

        request = self.master.state.view[1].request
        assert request.timestamp_end - request.timestamp_start <= 0.1
