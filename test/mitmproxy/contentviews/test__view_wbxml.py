import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_wbxml import wbxml

datadir = "mitmproxy/contentviews/test_wbxml_data/"


def test_wbxml(tdata):
    assert wbxml.prettify(b"\x03\x01\x6a\x00", Metadata()) == '<?xml version="1.0" ?>\n'
    with pytest.raises(Exception):
        wbxml.prettify(b"foo", Metadata())

    # File taken from https://github.com/davidpshaw/PyWBXMLDecoder/tree/master/wbxml_samples
    path = tdata.path(datadir + "data.wbxml")
    with open(path, "rb") as f:
        input = f.read()
    with open("-formatted.".join(path.rsplit(".", 1))) as f:
        expected = f.read()

    assert wbxml.prettify(input, Metadata()) == expected


def test_render_priority():
    assert wbxml.render_priority(
        b"data", Metadata(content_type="application/vnd.wap.wbxml")
    )
    assert wbxml.render_priority(
        b"data", Metadata(content_type="application/vnd.ms-sync.wbxml")
    )
    assert not wbxml.render_priority(b"data", Metadata(content_type="text/plain"))
