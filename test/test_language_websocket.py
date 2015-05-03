
from libpathod import language
from libpathod.language import websockets
import netlib.websockets
import tutils


def parse_request(s):
    return language.parse_requests(s)[0]


class TestWebsocketFrame:
    def test_values(self):
        specs = [
            "wf",
            "wf:b'foo'",
            "wf:cbinary",
            "wf:c1"
        ]
        for i in specs:
            wf = parse_request(i)
            assert isinstance(wf, websockets.WebsocketFrame)
            assert wf
            assert wf.values(language.Settings())
            assert wf.resolve(language.Settings())

            spec = wf.spec()
            wf2 = parse_request(spec)
            assert wf2.spec() == spec

    def test_construction(self):
        wf = parse_request("wf:c1")
        frm = netlib.websockets.Frame.from_bytes(tutils.render(wf))
        assert wf.code.value == 1 == frm.header.opcode

        wf = parse_request("wf:cbinary")
        frm = netlib.websockets.Frame.from_bytes(tutils.render(wf))
        assert wf.code.value == frm.header.opcode
        assert wf.code.value == netlib.websockets.OPCODE.BINARY
