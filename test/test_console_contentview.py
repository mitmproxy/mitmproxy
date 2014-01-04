import os
from nose.plugins.skip import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")

import sys
import libmproxy.console.contentview as cv
from libmproxy import utils, flow, encoding
import tutils

try:
    import pyamf
except ImportError:
    pyamf = None

try:
    import cssutils
except:
    cssutils = None


class TestContentView:
    def test_trailer(self):
        txt = []
        cv.trailer(5, txt, 1000)
        assert not txt
        cv.trailer(cv.VIEW_CUTOFF + 10, txt, cv.VIEW_CUTOFF)
        assert txt

    def test_view_auto(self):
        v = cv.ViewAuto()
        f = v(
                flow.ODictCaseless(),
                "foo",
                1000
              )
        assert f[0] == "Raw"

        f = v(
                flow.ODictCaseless(
                    [["content-type", "text/html"]],
                ),
                "<html></html>",
                1000
              )
        assert f[0] == "HTML"

        f = v(
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "foo",
                1000
              )
        assert f[0] == "Raw"

        f = v(
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "<xml></xml>",
                1000
              )
        assert f[0].startswith("XML")


    def test_view_urlencoded(self):
        d = utils.urlencode([("one", "two"), ("three", "four")])
        v = cv.ViewURLEncoded()
        assert v([], d, 100)
        d = utils.urlencode([("adsfa", "")])
        v = cv.ViewURLEncoded()
        assert v([], d, 100)

    def test_view_html(self):
        v = cv.ViewHTML()
        s = "<html><br><br></br><p>one</p></html>"
        assert v([], s, 1000)

        s = "gobbledygook"
        assert not v([], s, 1000)

    def test_view_html_outline(self):
        v = cv.ViewHTMLOutline()
        s = "<html><br><br></br><p>one</p></html>"
        assert v([], s, 1000)

    def test_view_json(self):
        cv.VIEW_CUTOFF = 100
        v = cv.ViewJSON()
        assert v([], "{}", 1000)
        assert not v([], "{", 1000)
        assert v([], "[" + ",".join(["0"]*cv.VIEW_CUTOFF) + "]", 1000)
        assert v([], "[1, 2, 3, 4, 5]", 5)

    def test_view_xml(self):
        v = cv.ViewXML()
        assert v([], "<foo></foo>", 1000)
        assert not v([], "<foo>", 1000)
        s = """<?xml version="1.0" encoding="UTF-8"?>
            <?xml-stylesheet title="XSL_formatting"?>
            <rss
                xmlns:media="http://search.yahoo.com/mrss/"
                xmlns:atom="http://www.w3.org/2005/Atom"
                version="2.0">
            </rss>
        """
        assert v([], s, 1000)

    def test_view_raw(self):
        v = cv.ViewRaw()
        assert v([], "foo", 1000)

    def test_view_javascript(self):
        v = cv.ViewJavaScript()
        assert v([], "[1, 2, 3]", 100)
        assert v([], "[1, 2, 3", 100)
        assert v([], "function(a){[1, 2, 3]}", 100)

    def test_view_css(self):
        v = cv.ViewCSS()

        with open('./test/data/1.css', 'r') as fp:
            fixture_1 = fp.read()

        result = v([], 'a', 100)

        if cssutils:
            assert len(result[1]) == 0
        else:
            assert len(result[1]) == 1

        result = v([], fixture_1, 100)

        if cssutils:
            assert len(result[1]) > 1
        else:
            assert len(result[1]) == 1

    def test_view_hex(self):
        v = cv.ViewHex()
        assert v([], "foo", 1000)

    def test_view_image(self):
        v = cv.ViewImage()
        p = tutils.test_data.path("data/image.png")
        assert v([], file(p,"rb").read(), sys.maxint)

        p = tutils.test_data.path("data/image.gif")
        assert v([], file(p,"rb").read(), sys.maxint)

        p = tutils.test_data.path("data/image-err1.jpg")
        assert v([], file(p,"rb").read(), sys.maxint)

        p = tutils.test_data.path("data/image.ico")
        assert v([], file(p,"rb").read(), sys.maxint)

        assert not v([], "flibble", sys.maxint)

    def test_view_multipart(self):
        view = cv.ViewMultipart()
        v = """
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
        """.strip()
        h = flow.ODictCaseless(
            [("Content-Type", "multipart/form-data; boundary=AaB03x")]
        )
        assert view(h, v, 1000)

        h = flow.ODictCaseless()
        assert not view(h, v, 1000)

        h = flow.ODictCaseless(
            [("Content-Type", "multipart/form-data")]
        )
        assert not view(h, v, 1000)

        h = flow.ODictCaseless(
            [("Content-Type", "unparseable")]
        )
        assert not view(h, v, 1000)

    def test_get_content_view(self):
        r = cv.get_content_view(
                cv.get("Raw"),
                [["content-type", "application/json"]],
                "[1, 2, 3]",
                1000,
                lambda x: None
              )
        assert "Raw" in r[0]

        r = cv.get_content_view(
                cv.get("Auto"),
                [["content-type", "application/json"]],
                "[1, 2, 3]",
                1000,
                lambda x: None
              )
        assert r[0] == "JSON"

        r = cv.get_content_view(
                cv.get("Auto"),
                [["content-type", "application/json"]],
                "[1, 2",
                1000,
                lambda x: None
              )
        assert "Raw" in r[0]

        r = cv.get_content_view(
                cv.get("AMF"),
                [],
                "[1, 2",
                1000,
                lambda x: None
              )
        assert "Raw" in r[0]


        r = cv.get_content_view(
                cv.get("Auto"),
                [
                    ["content-type", "application/json"],
                    ["content-encoding", "gzip"]
                ],
                encoding.encode('gzip', "[1, 2, 3]"),
                1000,
                lambda x: None
              )
        assert "decoded gzip" in r[0]
        assert "JSON" in r[0]

        r = cv.get_content_view(
                cv.get("XML"),
                [
                    ["content-type", "application/json"],
                    ["content-encoding", "gzip"]
                ],
                encoding.encode('gzip', "[1, 2, 3]"),
                1000,
                lambda x: None
              )
        assert "decoded gzip" in r[0]
        assert "Raw" in r[0]


if pyamf:
    def test_view_amf_request():
        v = cv.ViewAMF()

        p = tutils.test_data.path("data/amf01")
        assert v([], file(p,"rb").read(), sys.maxint)

        p = tutils.test_data.path("data/amf02")
        assert v([], file(p,"rb").read(), sys.maxint)

    def test_view_amf_response():
        v = cv.ViewAMF()
        p = tutils.test_data.path("data/amf03")
        assert v([], file(p,"rb").read(), sys.maxint)

if cv.ViewProtobuf.is_available():
    def test_view_protobuf_request():
        v = cv.ViewProtobuf()

        p = tutils.test_data.path("data/protobuf01")
        content_type, output = v([], file(p,"rb").read(), sys.maxint)
        assert content_type == "Protobuf"
        assert output[0].text == '1: "3bbc333c-e61c-433b-819a-0b9a8cc103b8"'

def test_get_by_shortcut():
    assert cv.get_by_shortcut("h")

def test_search_highlights():
    # Default text in requests is content. We will search for nt once, and
    # expect the first bit to be highlighted. We will do it again and expect the
    # second to be.
    f = tutils.tflowview()

    f.search("nt")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('content', [(None, 2), (f.highlight_color, 2)])

    f.search("nt")
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('content', [(None, 5), (f.highlight_color, 2)])

def test_search_returns_useful_messages():
    f = tutils.tflowview()

    # original string is content. this string should not be in there.
    response = f.search("oranges and other fruit.")
    assert response == "no matches for 'oranges and other fruit.'"

def test_search_highlights_clears_prev():
    f = tutils.tflowview(request_contents="this is string\nstring is string")

    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])

    # search again, it should not be highlighted again.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() != ('this is string', [(None, 8), (f.highlight_color, 6)])

def test_search_highlights_multi_line():
    f = tutils.tflowview(request_contents="this is string\nstring is string")

    # should highlight the first line.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])

    # should highlight second line, first appearance of string.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('string is string', [(None, 0), (f.highlight_color, 6)])

    # should highlight third line, second appearance of string.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert text_object.get_text() == ('string is string', [(None, 10), (f.highlight_color, 6)])

def test_search_loops():
    f = tutils.tflowview(request_contents="this is string\nstring is string")

    # get to the end.
    f.search("string")
    f.search("string")
    f.search("string")

    # should highlight the first line.
    message = f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 0)
    assert text_object.get_text() == ('this is string', [(None, 8), (f.highlight_color, 6)])
    assert message == "search hit BOTTOM, continuing at TOP"

def test_search_focuses():
    f = tutils.tflowview(request_contents="this is string\nstring is string")

    # should highlight the first line.
    f.search("string")

    # should be focusing on the 2nd text line.
    f.search("string")
    text_object = tutils.get_body_line(f.last_displayed_body, 1)
    assert f.last_displayed_body.focus == text_object

def test_search_does_not_crash_on_bad():
    """
        this used to crash, kept for reference.
    """

    f = tutils.tflowview(request_contents="this is string\nstring is string\n"+("A" * cv.VIEW_CUTOFF)+"AFTERCUTOFF")
    f.search("AFTERCUTOFF")

    # pretend F
    f.state.add_flow_setting(
        f.flow,
        (f.state.view_flow_mode, "fullcontents"),
        True
    )
    f.master.refresh_flow(f.flow)

    # text changed, now this string will exist. can happen when user presses F
    # for full text view
    f.search("AFTERCUTOFF")


