
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
            "wf:dr",
            "wf:b'foo'",
            "wf:cbinary",
            "wf:c1",
            "wf:r",
            "wf:fin",
            "wf:fin:rsv1:rsv2:rsv3:mask",
            "wf:-fin:-rsv1:-rsv2:-rsv3:-mask",
            "wf:k@4",
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

    def test_raw(self):
        pass

    def test_flags(self):
        wf = parse_request("wf:fin:mask:rsv1:rsv2:rsv3")
        frm = netlib.websockets.Frame.from_bytes(tutils.render(wf))
        assert frm.header.fin
        assert frm.header.mask
        assert frm.header.rsv1
        assert frm.header.rsv2
        assert frm.header.rsv3

        wf = parse_request("wf:-fin:-mask:-rsv1:-rsv2:-rsv3")
        frm = netlib.websockets.Frame.from_bytes(tutils.render(wf))
        assert not frm.header.fin
        assert not frm.header.mask
        assert not frm.header.rsv1
        assert not frm.header.rsv2
        assert not frm.header.rsv3

    def test_construction(self):
        wf = parse_request("wf:c1")
        frm = netlib.websockets.Frame.from_bytes(tutils.render(wf))
        assert wf.opcode.value == 1 == frm.header.opcode

        wf = parse_request("wf:cbinary")
        frm = netlib.websockets.Frame.from_bytes(tutils.render(wf))
        assert wf.opcode.value == frm.header.opcode
        assert wf.opcode.value == netlib.websockets.OPCODE.BINARY

    def test_auto_raw(self):
        wf = parse_request("wf:b'foo':mask")
        frm = netlib.websockets.Frame.from_bytes(tutils.render(wf))
        print frm.human_readable()
