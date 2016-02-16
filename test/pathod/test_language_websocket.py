
from pathod import language
from pathod.language import websockets
import netlib.websockets
import tutils


def parse_request(s):
    return language.parse_pathoc(s).next()


class TestWebsocketFrame:

    def _test_messages(self, specs, message_klass):
        for i in specs:
            wf = parse_request(i)
            assert isinstance(wf, message_klass)
            assert wf
            assert wf.values(language.Settings())
            assert wf.resolve(language.Settings())

            spec = wf.spec()
            wf2 = parse_request(spec)
            assert wf2.spec() == spec

    def test_server_values(self):
        specs = [
            "wf",
            "wf:dr",
            "wf:b'foo'",
            "wf:mask:r'foo'",
            "wf:l1024:b'foo'",
            "wf:cbinary",
            "wf:c1",
            "wf:mask:knone",
            "wf:fin",
            "wf:fin:rsv1:rsv2:rsv3:mask",
            "wf:-fin:-rsv1:-rsv2:-rsv3:-mask",
            "wf:k@4",
            "wf:x10",
        ]
        self._test_messages(specs, websockets.WebsocketFrame)

    def test_parse_websocket_frames(self):
        wf = language.parse_websocket_frame("wf:x10")
        assert len(list(wf)) == 10
        tutils.raises(
            language.ParseException,
            language.parse_websocket_frame,
            "wf:x"
        )

    def test_client_values(self):
        specs = [
            "wf:f'wf'",
        ]
        self._test_messages(specs, websockets.WebsocketClientFrame)

    def test_nested_frame(self):
        wf = parse_request("wf:f'wf'")
        assert wf.nested_frame

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

    def fr(self, spec, **kwargs):
        settings = language.base.Settings(**kwargs)
        wf = parse_request(spec)
        return netlib.websockets.Frame.from_bytes(tutils.render(wf, settings))

    def test_construction(self):
        assert self.fr("wf:c1").header.opcode == 1
        assert self.fr("wf:c0").header.opcode == 0
        assert self.fr("wf:cbinary").header.opcode ==\
            netlib.websockets.OPCODE.BINARY
        assert self.fr("wf:ctext").header.opcode ==\
            netlib.websockets.OPCODE.TEXT

    def test_rawbody(self):
        frm = self.fr("wf:mask:r'foo'")
        assert len(frm.payload) == 3
        assert frm.payload != "foo"

        assert self.fr("wf:r'foo'").payload == "foo"

    def test_construction(self):
        # Simple server frame
        frm = self.fr("wf:b'foo'")
        assert not frm.header.mask
        assert not frm.header.masking_key

        # Simple client frame
        frm = self.fr("wf:b'foo'", is_client=True)
        assert frm.header.mask
        assert frm.header.masking_key
        frm = self.fr("wf:b'foo':k'abcd'", is_client=True)
        assert frm.header.mask
        assert frm.header.masking_key == 'abcd'

        # Server frame, mask explicitly set
        frm = self.fr("wf:b'foo':mask")
        assert frm.header.mask
        assert frm.header.masking_key
        frm = self.fr("wf:b'foo':k'abcd'")
        assert frm.header.mask
        assert frm.header.masking_key == 'abcd'

        # Client frame, mask explicitly unset
        frm = self.fr("wf:b'foo':-mask", is_client=True)
        assert not frm.header.mask
        assert not frm.header.masking_key

        frm = self.fr("wf:b'foo':-mask:k'abcd'", is_client=True)
        assert not frm.header.mask
        # We're reading back a corrupted frame - the first 3 characters of the
        # mask is mis-interpreted as the payload
        assert frm.payload == "abc"

    def test_knone(self):
        with tutils.raises("expected 4 bytes"):
            self.fr("wf:b'foo':mask:knone")

    def test_length(self):
        assert self.fr("wf:l3:b'foo'").header.payload_length == 3
        frm = self.fr("wf:l2:b'foo'")
        assert frm.header.payload_length == 2
        assert frm.payload == "fo"
        tutils.raises("expected 1024 bytes", self.fr, "wf:l1024:b'foo'")
