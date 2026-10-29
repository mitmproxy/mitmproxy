import pytest

from mitmproxy import exceptions
from mitmproxy.addons import mapremote
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestMapRemote:
    def test_configure(self):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            tctx.configure(mr, map_remote=["one/two/three"])
            with pytest.raises(Exception, match="Invalid regular expression"):
                tctx.configure(mr, map_remote=["/foo/+/three"])

    @pytest.mark.parametrize(
        "replacement",
        [r"\2", r"\g<missing>", r"\q", r"\g<", "\\"],
    )
    def test_invalid_replacement(self, replacement):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            with pytest.raises(exceptions.OptionsError, match="Invalid replacement"):
                tctx.configure(mr, map_remote=[f"|example.org|{replacement}"])

    @pytest.mark.parametrize(
        "pattern,replacement,expected",
        [
            (r"(example)\.org", r"\1.com", "https://example.com/path"),
            (
                r"(?P<host>example)\.org",
                r"\g<host>.com",
                "https://example.com/path",
            ),
            (r"/path", "", "https://example.org/"),
            (r"does-not-match", r"\g<0>", "https://example.org/path"),
        ],
    )
    def test_valid_replacement(self, pattern, replacement, expected):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            tctx.configure(mr, map_remote=[f"|{pattern}|{replacement}"])
            f = tflow.tflow()
            f.request.url = "https://example.org/path"
            mr.request(f)
            assert f.request.url == expected

    def test_simple(self):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            tctx.configure(
                mr,
                map_remote=[
                    ":example.org/images/:mitmproxy.org/img/",
                ],
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            mr.request(f)
            assert f.request.url == "https://mitmproxy.org/img/test.jpg"

    def test_host_header(self):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            tctx.configure(mr, map_remote=["|http://[^/]+|http://example.com:4444"])
            f = tflow.tflow()
            f.request.url = b"http://example.org/example"
            f.request.headers["Host"] = "example.org"
            mr.request(f)
            assert f.request.headers.get("Host", "") == "example.com:4444"

    def test_is_killed(self):
        mr = mapremote.MapRemote()
        with taddons.context(mr) as tctx:
            tctx.configure(mr, map_remote=[":example.org:mitmproxy.org"])
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            f.kill()
            mr.request(f)
            assert f.request.url == "https://example.org/images/test.jpg"
