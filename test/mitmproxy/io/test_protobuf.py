import pytest

from mitmproxy import certs
from mitmproxy import http
from mitmproxy.test import tflow, tutils, taddons
from mitmproxy.io import protobuf


class TestProtobuf:

    def test_roundtrip_client(self):
        c = tflow.tclient_conn()
        pc = protobuf._dump_http_client_conn(c)
        lc = protobuf._load_http_client_conn(pc)
        # These do not have to be restored in deserialization, since we don't have a connection anymore
        del c.reply
        c.rfile = None
        c.wfile = None
        assert c.__dict__ == lc.__dict__

    def test_roundtrip_client_cert(self, tdata):
        c = tflow.tclient_conn()
        with open(tdata.path("mitmproxy/net/data/clientcert/client.pem"), "rb") as f:
            d = f.read()
        c.clientcert = certs.Cert.from_pem(d)
        pc = protobuf._dump_http_client_conn(c)
        lc = protobuf._load_http_client_conn(pc)
        del c.reply
        c.rfile = None
        c.wfile = None
        assert c.__dict__ == lc.__dict__

    def test_roundtrip_http_request(self):
        req = http.HTTPRequest.wrap(tutils.treq())
        preq = protobuf._dump_http_request(req)
        lreq = protobuf._load_http_request(preq)
        assert req.__dict__ == lreq.__dict__

    def test_roundtrip_http_response(self):
        res = http.HTTPResponse.wrap(tutils.tresp())
        pres = protobuf._dump_http_response(res)
        lres = protobuf._load_http_response(pres)
        assert res.__dict__ == lres.__dict__



