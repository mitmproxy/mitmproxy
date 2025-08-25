from mitmproxy.tools.console import overlay


class DummyMaster:
    class Options:
        menu_select_keys = "123456789abcdefghijklmnoprstuvwxyz"

    def __init__(self):
        self.options = DummyMaster.Options()


def dummy_cb(_):
    pass


def test_chooser_list_walker_shortcuts():
    master = DummyMaster()
    walker = overlay.ChooserListWalker(master, ["foo", "bar"], "foo")
    assert walker.shortcuts == master.options.menu_select_keys
    assert isinstance(walker._get(1, False), overlay.Choice)


def test_chooser_sets_walker():
    master = DummyMaster()
    chooser = overlay.Chooser(master, "title", ["foo", "bar"], "foo", dummy_cb)
    assert isinstance(chooser.walker, overlay.ChooserListWalker)
    assert chooser.walker.choices == ["foo", "bar"]
