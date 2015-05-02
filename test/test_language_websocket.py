
from libpathod import language
from libpathod.language import websockets


def parse_request(s):
    return language.parse_requests(s)[0]


class TestWebsocketFrame:
    def test_values(self):
        specs = [
            "wf",
            "wf:b'foo'"
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
