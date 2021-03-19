import pytest

from mitmproxy.addons import blocklist
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestBlockList:
    def test_good_three_part_configure(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=["/one/two/200"])

    def test_good_two_part_configure(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=["/one/200"])

    def test_invalid_regex(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(Exception, match="Invalid regular expression"):
                tctx.configure(bl, block_list=["/foo/+/200"])

    def test_configure_invalid_status_code(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(Exception, match="Invalid HTTP status code"):
                tctx.configure(bl, block_list=["/foo/.*/NOT_A_STATUS_CODE"])

    def test_simple(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ":example.org:images:200",
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert f.response.status_code == 200

    def test_has_guessed_content_type(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=[":example.org:204"])
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert f.response.headers['Content-Type'] == 'image/jpeg'

    def test_has_no_content(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=[":example.org:204"])
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert f.response.content == b""