from pathlib import Path

from ruamel.yaml import YAML

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import InteractiveContentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.contentviews._view_raw import raw
from mitmproxy.test import tflow
from mitmproxy_rs.contentviews import _test_inspect_metadata
from mitmproxy_rs.contentviews import msgpack


class ExampleContentview(InteractiveContentview):
    def prettify(self, data: bytes, metadata: Metadata) -> str:
        return data.decode()

    def reencode(self, prettified: str, metadata: Metadata) -> bytes:
        return prettified.encode()


class FailingPrettifyContentview(Contentview):
    def prettify(self, data, metadata):
        raise ValueError("prettify error")

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        return 1


class FailingRenderPriorityContentview(Contentview):
    def prettify(self, data, metadata):
        return data.decode()

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        raise ValueError("render_priority error")


def test_simple():
    view = ExampleContentview()
    assert view.name == "Example"
    assert view.render_priority(b"test", Metadata()) == 0
    assert view.syntax_highlight == "none"
    assert not (view < view)


def test_default_impls():
    t = ExampleContentview()
    assert t.name == "Example"
    assert t.syntax_highlight == "none"
    assert t.render_priority(b"data", Metadata()) == 0
    assert t < raw
    assert not raw < t


class TestRustInterop:
    def test_compare(self):
        assert msgpack < raw
        assert not raw < msgpack
        assert not msgpack < msgpack

    def test_metadata(self):
        """Ensure that metadata roundtrips properly."""
        f = tflow.tflow()
        f.request.headers["HoSt"] = "example.com"
        meta = Metadata(
            content_type="text/html",
            flow=f,
            http_message=f.request,
            protobuf_definitions=Path("example.proto"),
        )

        out = _test_inspect_metadata.prettify(b"", meta)
        actual = YAML(typ="safe", pure=True).load(out)

        assert actual == {
            "content_type": "text/html",
            "headers": {"host": "example.com"},
            "is_http_request": True,
            "path": "/path",
            "protobuf_definitions": "example.proto",
        }
