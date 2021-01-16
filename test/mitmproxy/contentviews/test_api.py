from unittest import mock

import pytest

from mitmproxy import contentviews
from mitmproxy.test import tflow
from mitmproxy.test import tutils


class TestContentView(contentviews.View):
    name = "test"

    def __call__(self, *args, **kwargs):
        pass

    def should_render(self, content_type):
        return content_type == "test/123"


def test_add_remove():
    tcv = TestContentView()
    contentviews.add(tcv)
    assert tcv in contentviews.views

    # repeated addition causes exception
    with pytest.raises(ValueError, match="Duplicate view"):
        contentviews.add(tcv)

    contentviews.remove(tcv)
    assert tcv not in contentviews.views


def test_get_content_view():
    desc, lines, err = contentviews.get_content_view(
        contentviews.get("Raw"),
        b"[1, 2, 3]",
    )
    assert "Raw" in desc
    assert list(lines)
    assert not err

    desc, lines, err = contentviews.get_content_view(
        contentviews.get("Auto"),
        b"[1, 2, 3]",
        content_type="application/json",
    )
    assert desc == "JSON"
    assert list(lines)

    desc, lines, err = contentviews.get_content_view(
        contentviews.get("JSON"),
        b"[1, 2",
    )
    assert "Couldn't parse" in desc

    with mock.patch("mitmproxy.contentviews.auto.ViewAuto.__call__") as view_auto:
        view_auto.side_effect = ValueError

        desc, lines, err = contentviews.get_content_view(
            contentviews.get("Auto"),
            b"[1, 2",
        )
        assert err
        assert "Couldn't parse" in desc


def test_get_message_content_view():
    f = tflow.tflow()
    r = tutils.treq()
    desc, lines, err = contentviews.get_message_content_view("raw", r, f)
    assert desc == "Raw"

    desc, lines, err = contentviews.get_message_content_view("unknown", r, f)
    assert desc == "Raw"

    r.encode("gzip")
    desc, lines, err = contentviews.get_message_content_view("raw", r, f)
    assert desc == "[decoded gzip] Raw"

    r.headers["content-encoding"] = "deflate"
    desc, lines, err = contentviews.get_message_content_view("raw", r, f)
    assert desc == "[cannot decode] Raw"

    r.content = None
    desc, lines, err = contentviews.get_message_content_view("raw", r, f)
    assert list(lines) == [[("error", "content missing")]]
