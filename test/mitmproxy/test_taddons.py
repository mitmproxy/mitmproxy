from mitmproxy.test import taddons


def test_load_script(tdata):
    with taddons.context() as tctx:
        s = tctx.script(tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py"))
        assert s


def test_configure_calls_configure_on_script_addon(tdata):
    """
    https://github.com/mitmproxy/mitmproxy/issues/3402

    `context.script()` returns an addon that is registered but not part of
    the addon chain, so the `options.changed` broadcast that normally
    triggers `configure()` for chained addons never reaches it.
    `context.configure()` must invoke `configure()` on it directly instead.
    """
    with taddons.context() as tctx:
        addon = tctx.script(
            tdata.path("mitmproxy/data/addonscripts/configure_recorder.py")
        )
        inner = addon.addons[0]
        # `configure()` is always called once at load time, with every
        # currently-set option.
        assert len(inner.call_log) == 1

        tctx.configure(addon, recorder_option="changed")
        assert tctx.options.recorder_option == "changed"
        assert inner.call_log[-1] == {"recorder_option"}
