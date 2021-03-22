import pytest

from mitmproxy.exceptions import OptionsError
from mitmproxy.addons import blocklist
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestBlockList:

    def test_invalid_filter_pattern(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(OptionsError, match="Invalid filter"):
                tctx.configure(bl, block_list=[":~d ~d asdfsad sdsdsssdd mysite.com:allow-only:200"])

    def test_good_configure(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=[":mysite.com:allow-only:200"])

    def test_invalid_parameters_length(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(OptionsError, match="Invalid number of parameters"):
                tctx.configure(bl, block_list=["/~u index.html/300"])

    def test_configure_bad_http_status_code(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(OptionsError, match="Invalid HTTP status code"):
                tctx.configure(bl, block_list=["/~u index.html/block/999"])

    def test_configure_invalid_status_code(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(OptionsError, match="Cannot parse block_list option"):
                tctx.configure(bl, block_list=[":mysite.com:block:NOT_A_STATUS_CODE"])

    def test_configure_bad_allow_block_option(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(OptionsError, match="Invalid block type"):
                tctx.configure(bl, block_list=[":mysite.com:notright:400"])

    def test_special_kill_status_closes_connection(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ':~u jpg:block:444',
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert (f.error.msg == f.error.KILLED_MESSAGE)
            assert (f.response is None)

    def test_simple(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ':~u example.org:block:200',
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert f.response.status_code == 200

    def test_allowonly_allows_matches_through(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ':jpg:allow-only:404',
                ]
            )
            f = tflow.tflow(resp=True)
            f.request.url = b"https://foo.org/images/test.jpg"
            bl.request(f)
            assert f.response.status_code == 200

    def test_allowonly_blocks_non_match(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ':~u .png:allow-only:404',
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://foo.org/images/test.jpg"
            bl.request(f)
            assert f.response.status_code == 404

    def test_block_blocks_matching_flow(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ':~u .jpg:block:404',
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert f.response.status_code == 404

    def block_ignores_non_match(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ':~u .png:block:404',
                ]
            )
            f = tflow.tflow(resp=True)
            f.request.url = b"https://foo.org/images/test.jpg"
            bl.request(f)
            assert f.response.status_code == 200

    def test_has_guessed_content_type(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=[":example.org:block:204"])
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert f.response.headers['Content-Type'] == 'image/jpeg'

    def test_blocked_response_has_no_content(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=[":example.org:block:204"])
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert f.response.content == b""