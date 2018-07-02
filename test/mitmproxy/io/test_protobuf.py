import pytest

from mitmproxy import certs
from mitmproxy import http
from mitmproxy import exceptions
from mitmproxy.test import tflow, tutils, taddons
from mitmproxy.io import protobuf


class TestProtobuf:

    def test_roundtrip_client(self):
        c = tflow.tclient_conn()
        del c.reply
        c.rfile = None
        c.wfile = None
        pc = protobuf._dump_http_client_conn(c)
        lc = protobuf._load_http_client_conn(pc)
        assert c.__dict__ == lc.__dict__

    def test_roundtrip_client_cert(self, tdata):
        c = tflow.tclient_conn()
        c.rfile = None
        c.wfile = None
        del c.reply
        with open(tdata.path("mitmproxy/net/data/clientcert/client.pem"), "rb") as f:
            d = f.read()
        c.clientcert = certs.Cert.from_pem(d)
        pc = protobuf._dump_http_client_conn(c)
        lc = protobuf._load_http_client_conn(pc)
        assert c.__dict__ == lc.__dict__

    def test_roundtrip_server(self):
        s = tflow.tserver_conn()
        del s.reply
        s.wfile = None
        s.rfile = None
        ps = protobuf._dump_http_server_conn(s)
        ls = protobuf._load_http_server_conn(ps)
        assert s.__dict__ == ls.__dict__

    def test_roundtrip_server_cert(self, tdata):
        s = tflow.tserver_conn()
        del s.reply
        s.wfile = None
        s.rfile = None
        with open(tdata.path("mitmproxy/net/data/text_cert"), "rb") as f:
            d = f.read()
        s.cert = certs.Cert.from_pem(d)
        ps = protobuf._dump_http_server_conn(s)
        ls = protobuf._load_http_server_conn(ps)
        assert s.__dict__ == ls.__dict__

    def test_roundtrip_server_via(self):
        s = tflow.tserver_conn()
        s.via = tflow.tserver_conn()
        del s.reply
        s.wfile = None
        s.rfile = None
        ps = protobuf._dump_http_server_conn(s)
        ls = protobuf._load_http_server_conn(ps)
        assert s.__dict__ == ls.__dict__
        del s.via.reply
        s.via.wfile = None
        s.via.rfile = None
        assert s.via.__dict__ == ls.via.__dict__

    def test_roundtrip_http_request(self):
        req = http.HTTPRequest.wrap(tutils.treq())
        preq = protobuf._dump_http_request(req)
        lreq = protobuf._load_http_request(preq)
        assert req.__dict__ == lreq.__dict__

    def test_roundtrip_http_request_empty_content(self):
        req = http.HTTPRequest.wrap(tutils.treq(content=b""))
        preq = protobuf._dump_http_request(req)
        lreq = protobuf._load_http_request(preq)
        assert req.__dict__ == lreq.__dict__

    def test_roundtrip_http_response(self):
        res = http.HTTPResponse.wrap(tutils.tresp())
        pres = protobuf._dump_http_response(res)
        lres = protobuf._load_http_response(pres)
        assert res.__dict__ == lres.__dict__

    def test_roundtrip_http_response_empty_content(self):
        res = http.HTTPResponse.wrap(tutils.tresp(content=b""))
        pres = protobuf._dump_http_response(res)
        lres = protobuf._load_http_response(pres)
        assert res.__dict__ == lres.__dict__

    def test_roundtrip_http_error(self):
        err = tflow.terr()
        perr = protobuf._dump_http_error(err)
        lerr = protobuf._load_http_error(perr)
        assert err.__dict__ == lerr.__dict__

    def test_roundtrip_http_flow_only_req(self):
        f = tflow.tflow()
        f.reply = None
        pf = protobuf.dumps(f)
        lf = protobuf.loads(pf, "http")
        assert f.__dict__ == lf.__dict__

    def test_roundtrip_http_flow_res(self):
        f = tflow.tflow(resp=True)
        f.reply = None
        pf = protobuf.dumps(f)
        lf = protobuf.loads(pf, "http")
        assert f.__dict__ == lf.__dict__

    def test_unsupported_dumps(self):
        w = tflow.twebsocketflow()
        with pytest.raises(exceptions.TypeError):
            protobuf.dumps(w)

    def test_unsupported_loads(self):
        b = b"blobs"
        with pytest.raises(exceptions.TypeError):
            protobuf.loads(b, 'not-http')

