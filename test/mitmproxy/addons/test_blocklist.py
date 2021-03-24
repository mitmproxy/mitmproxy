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
                tctx.configure(bl, block_list=[":~d ~d asdfsad sdsdsssdd mysite.com:200"])

    def test_good_configure(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=[":mysite.com:200"])

    def test_invalid_parameters_length(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(OptionsError, match="Invalid number of parameters"):
                tctx.configure(bl, block_list=["/~u index.html/TOOMANY/300"])

    def test_configure_bad_http_status_code(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(OptionsError, match="Invalid HTTP status code"):
                tctx.configure(bl, block_list=["/~u index.html/999"])

    def test_configure_invalid_status_code(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            with pytest.raises(OptionsError, match="Cannot parse block_list option"):
                tctx.configure(bl, block_list=[":mysite.com:NOT_A_STATUS_CODE"])

    def test_special_kill_status_closes_connection(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ':~u jpg:444',
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
                    ':~u example.org:200',
                ]
            )
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert f.response.status_code == 200

    def test_negated_filter_allows_passing_traffic(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ':!jpg:404',
                ]
            )
            f = tflow.tflow(resp=True)
            f.request.url = b"https://foo.org/images/test.jpg"
            bl.request(f)
            assert f.response.status_code == 200

    def negated_filter_blocks_non_matching_traffic(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(
                bl,
                block_list=[
                    ':!~u .png:404',
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
                    ':~u .jpg:404',
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
                    ':~u .png:404',
                ]
            )
            f = tflow.tflow(resp=True)
            f.request.url = b"https://foo.org/images/test.jpg"
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

    def test_blocked_response_has_no_content(self):
        bl = blocklist.BlockList()
        with taddons.context(bl) as tctx:
            tctx.configure(bl, block_list=[":example.org:204"])
            f = tflow.tflow()
            f.request.url = b"https://example.org/images/test.jpg"
            bl.request(f)
            assert f.response.content == b""