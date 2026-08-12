from mitmproxy.test import taddons


def test_load_script(tdata):
    with taddons.context() as tctx:
        s = tctx.script(tdata.path("mitmproxy/data/addonscripts/recorder/recorder.py"))
        assert s


def test_configure_calls_addon_configure():
    class TestAddon:
        def load(self, loader):
            loader.add_option("foo", str, "", "test option")

        def configure(self, updated):
            self.configure_was_called = True

    addon = TestAddon()
    with taddons.context(addon) as tctx:
        tctx.configure(addon, foo="bar")
        assert tctx.options.foo == "bar"
        assert addon.configure_was_called