
from libpathod import language
from libpathod.language import websockets


def parse_request(s):
    return language.parse_requests(s)[0]


class TestWebsocketFrame:
    def test_spec(self):
        e = websockets.WebsocketFrame.expr()
        wf = e.parseString("wf:b'foo'")
        assert wf

        assert parse_request("wf:b'foo'")

    def test_values(self):
        r = parse_request("wf:b'foo'")
        assert r.values(language.Settings())
