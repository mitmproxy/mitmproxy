from mitmproxy.test import taddons


def test_load_script(tdata):
    with taddons.context() as tctx:
        s = tctx.script(tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py"))
        assert s
