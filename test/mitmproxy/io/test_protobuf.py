import pytest

from mitmproxy import certs
from mitmproxy.test import tflow, tutils, taddons
from mitmproxy.io import protobuf

"""
IDEAS: 
TEST INCREMENTALLY DIFFICULT FLOWS.
FIRST SIMPLE FLOWS, THEN ADD MORE THINGS.
INSPECT POINTS OF FAILURES.
WHAT WE EXPECT FROM TESTS:
F = FLOW()
D = F.DUMPS()
L = F.LOADS()
ASSERT F == L

F = FLOW(INVALID)
D = F.DUMPS() => RAISES EXCEPTION

D = MALFORMED_DUMP
L = F.LOADS => RAISES EXCEPTION 

TO OBTAIN THIS WE MIGHT NEED TO STRIP OFF STATEOBJECT ATTRIBUTES.
THIS APART, THIS SHOULD WORK. WE'LL SEE.

Classes of equivalence:

- Presence of response and/or error in HTTPFlow
- TLS in client/server Connection
- via in Server Connection
- TLS extensions in Server Connection
- Content / No Content, Headers / No Headers

OR

- I could - Should test differently for all the methods! And THEN I can do it as a whole.

-> Client Connection EC : certs, tls_extensions, address

"""


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
        c = tutils.treq()


