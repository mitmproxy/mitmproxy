import zlib

import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_zlib import zlib_view


def test_view_zlib():
    meta = Metadata(content_type="application/zlib")
    assert zlib_view.prettify(zlib.compress(b'{"foo": 42}'), meta) == '{"foo": 42}'
    assert zlib_view.prettify(zlib.compress("🫠".encode()), meta) == "🫠"
    assert zlib_view.prettify(zlib.compress(b"\xff"), meta) == r"\xff"
    with pytest.raises(zlib.error):
        zlib_view.prettify(b"not zlib", meta)


def test_render_priority():
    data = zlib.compress(b"data")
    assert (
        zlib_view.render_priority(data, Metadata(content_type="application/zlib"))
        == 1.0
    )
    assert zlib_view.render_priority(data, Metadata(content_type="text/plain")) == 0
    assert (
        zlib_view.render_priority(b"", Metadata(content_type="application/zlib")) == 0
    )
