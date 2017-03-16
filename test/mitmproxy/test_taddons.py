from mitmproxy.test import taddons
from mitmproxy import ctx


def test_recordingmaster():
    with taddons.context() as tctx:
        assert not tctx.master.has_log("nonexistent")
        assert not tctx.master.has_event("nonexistent")
        ctx.log.error("foo")
        assert not tctx.master.has_log("foo", level="debug")
        assert tctx.master.has_log("foo", level="error")
