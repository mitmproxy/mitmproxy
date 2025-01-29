import pytest

from mitmproxy.addons import blocklist
from mitmproxy.exceptions import OptionsError
from mitmproxy.test import taddons
from mitmproxy.test import tflow


@pytest.mark.parametrize(
    "filter,err",
    [
        ("/~u index.html/TOOMANY/300", "Invalid number of parameters"),
        (":~d ~d ~d:200", "Invalid filter"),
        ("/~u index.html/abc", "Invalid HTTP status code"),
    ],
)
def test_parse_spec_err(filter, err):
    with pytest.raises(ValueError, match=err):
        blocklist.parse_spec(filter)


class TestBlockList:
    @pytest.mark.parametrize(
        "filter,request_url,status_code",
        [
            (":~u example.org:404", b"https://example.org/images/test.jpg", 404),
            (":~u example.com:404", b"https://example.org/images/test.jpg", None),
            (":~u test:404", b"https://example.org/images/TEST.jpg", 404),
            ("/!jpg/418", b"https://example.org/images/test.jpg", None),
            ("/!png/418", b"https://example.org/images/test.jpg", 418),
            ("|~u /DATA|500", b"https://example.org/DATA", 500),
            ("|~u /ASSETS|501", b"https://example.org/assets", 501),
            ("|~u /ping|201", b"https://example.org/PING", 201),
        ],
    )
    def test_block(self, filter, request_url, status_code):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=[filter])
            f = tflow.tflow()
            f.request.url = request_url
            bl.request(f)
            if status_code is not None:
                assert f.response.status_code == status_code
                assert f.metadata["blocklisted"]
            else:
                assert not f.response

    def test_uppercase_header_values(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=["|~hq Cookie:\\sfoo=BAR|403"])
            f = tflow.tflow()
            f.request.url = "https://example.org/robots.txt"
            f.request.headers["Cookie"] = "foo=BAR; key1=value1"
            bl.request(f)
            assert f.response.status_code == 403
            assert f.metadata["blocklisted"]

    def test_mixedcase_header_names(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=["|~hq User-Agent:\\scurl|401"])
            f = tflow.tflow()
            f.request.url = "https://example.org/products/123"
            f.request.headers["user-agent"] = "curl/8.11.1"
            bl.request(f)
            assert f.response

    def test_special_kill_status_closes_connection(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=[":.*:444"])
            f = tflow.tflow()
            bl.request(f)
            assert f.error.msg == f.error.KILLED_MESSAGE
            assert f.response is None
            assert f.metadata["blocklisted"] is True

    def test_already_handled(self):
        """Test that we don't interfere if another addon already killed this request."""
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=["/.*/404"])
            f = tflow.tflow()
            f.kill()  # done by another addon.
            bl.request(f)
            assert not f.response

    def test_configure_err(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(OptionsError):
                tctx.configure(bl, block_list=["lalelu"])
