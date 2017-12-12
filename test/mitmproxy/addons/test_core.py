from mitmproxy.addons import core
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy import exceptions
import pytest


def test_set():
    sa = core.Core()
    with taddons.context() as tctx:
        tctx.master.addons.add(sa)

        assert not tctx.master.options.anticomp
        tctx.command(sa.set, "anticomp")
        assert tctx.master.options.anticomp

        with pytest.raises(exceptions.CommandError):
            tctx.command(sa.set, "nonexistent")


def test_resume():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow()
        assert not sa.resume([f])
        f.intercept()
        sa.resume([f])
        assert not f.reply.state == "taken"


def test_mark():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow()
        assert not f.marked
        sa.mark([f], True)
        assert f.marked

        sa.mark_toggle([f])
        assert not f.marked
        sa.mark_toggle([f])
        assert f.marked


def test_kill():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow()
        f.intercept()
        assert f.killable
        sa.kill([f])
        assert not f.killable


def test_revert():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow()
        f.backup()
        f.request.content = b"bar"
        assert f.modified()
        sa.revert([f])
        assert not f.modified()


def test_flow_set():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow(resp=True)
        assert sa.flow_set_options()

        assert f.request.method != "post"
        sa.flow_set([f], "method", "post")
        assert f.request.method == "POST"

        assert f.request.host != "testhost"
        sa.flow_set([f], "host", "testhost")
        assert f.request.host == "testhost"

        assert f.request.path != "/test/path"
        sa.flow_set([f], "path", "/test/path")
        assert f.request.path == "/test/path"

        assert f.request.url != "http://foo.com/bar"
        sa.flow_set([f], "url", "http://foo.com/bar")
        assert f.request.url == "http://foo.com/bar"
        with pytest.raises(exceptions.CommandError):
            sa.flow_set([f], "url", "oink")

        assert f.response.status_code != 404
        sa.flow_set([f], "status_code", "404")
        assert f.response.status_code == 404
        assert f.response.reason == "Not Found"
        with pytest.raises(exceptions.CommandError):
            sa.flow_set([f], "status_code", "oink")

        assert f.response.reason != "foo"
        sa.flow_set([f], "reason", "foo")
        assert f.response.reason == "foo"


def test_encoding():
    sa = core.Core()
    with taddons.context():
        f = tflow.tflow()
        assert sa.encode_options()
        sa.encode([f], "request", "deflate")
        assert f.request.headers["content-encoding"] == "deflate"

        sa.encode([f], "request", "br")
        assert f.request.headers["content-encoding"] == "deflate"

        sa.decode([f], "request")
        assert "content-encoding" not in f.request.headers

        sa.encode([f], "request", "br")
        assert f.request.headers["content-encoding"] == "br"

        sa.encode_toggle([f], "request")
        assert "content-encoding" not in f.request.headers
        sa.encode_toggle([f], "request")
        assert f.request.headers["content-encoding"] == "deflate"
        sa.encode_toggle([f], "request")
        assert "content-encoding" not in f.request.headers


def test_options(tmpdir):
    p = str(tmpdir.join("path"))
    sa = core.Core()
    with taddons.context() as tctx:
        tctx.options.stickycookie = "foo"
        assert tctx.options.stickycookie == "foo"
        sa.options_reset()
        assert tctx.options.stickycookie is None

        tctx.options.stickycookie = "foo"
        tctx.options.stickyauth = "bar"
        sa.options_reset_one("stickycookie")
        assert tctx.options.stickycookie is None
        assert tctx.options.stickyauth == "bar"

        with pytest.raises(exceptions.CommandError):
            sa.options_reset_one("unknown")

        sa.options_save(p)
        with pytest.raises(exceptions.CommandError):
            sa.options_save("/")

        sa.options_reset()
        assert tctx.options.stickyauth is None
        sa.options_load(p)
        assert tctx.options.stickyauth == "bar"

        sa.options_load("/nonexistent")

        with open(p, 'a') as f:
            f.write("'''")
        with pytest.raises(exceptions.CommandError):
            sa.options_load(p)
