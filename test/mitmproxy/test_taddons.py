import io
from mitmproxy.test import taddons
from mitmproxy.test import tutils
from mitmproxy import ctx


def test_recordingmaster():
    with taddons.context() as tctx:
        assert not tctx.master.has_log("nonexistent")
        assert not tctx.master.has_event("nonexistent")
        ctx.log.error("foo")
        assert not tctx.master.has_log("foo", level="debug")
        assert tctx.master.has_log("foo", level="error")


def test_dumplog():
    with taddons.context() as tctx:
        ctx.log.info("testing")
        s = io.StringIO()
        tctx.master.dump_log(s)
        assert s.getvalue()


def test_load_script():
    with taddons.context() as tctx:
        s = tctx.script(
            tutils.test_data.path(
                "mitmproxy/data/addonscripts/recorder/recorder.py"
            )
        )
        assert s
