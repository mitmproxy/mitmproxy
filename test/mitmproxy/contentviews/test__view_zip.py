import io
import zipfile

from mitmproxy import http
from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_zip import zip


def meta(content_type: str) -> Metadata:
    return Metadata(
        content_type=content_type.split(";")[0],
        http_message=http.Request.make(
            "POST", "https://example.com/", headers={"content-type": content_type}
        ),
    )


def test_view_zip():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name in [
            "normal.txt",
            "with spaces.txt",
            "dir/nested.txt",
            "file\nwith\nnewlines.txt",
            "unicode_文件.txt",
            "café.txt",
        ]:
            zf.writestr(name, b"content")
    result = zip.prettify(buffer.getvalue(), meta("application/zip"))
    for name in [
        "normal.txt",
        "with spaces.txt",
        "dir/nested.txt",
        "newlines",
        "文件",
        "café",
    ]:
        assert name in result
    assert zip.syntax_highlight == "yaml"


def test_view_zip_empty():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w"):
        pass
    assert (
        zip.prettify(buffer.getvalue(), meta("application/zip")) == "(empty zip file)"
    )


def test_render_priority():
    assert zip.render_priority(b"data", Metadata(content_type="application/zip")) == 1.0
    assert zip.render_priority(b"data", Metadata(content_type="text/plain")) == 0
    assert zip.render_priority(b"", Metadata(content_type="application/zip")) == 0
