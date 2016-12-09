from mitmproxy.contentviews import xml
from . import full_eval


def test_view_xml():
    v = full_eval(xml.ViewXML())
    assert v(b"<foo></foo>")
    assert not v(b"<foo>")
    s = b"""<?xml version="1.0" encoding="UTF-8"?>
        <?xml-stylesheet title="XSL_formatting"?>
        <rss
            xmlns:media="http://search.yahoo.com/mrss/"
            xmlns:atom="http://www.w3.org/2005/Atom"
            version="2.0">
        </rss>
    """
    assert v(s)
