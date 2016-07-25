from __future__ import absolute_import, print_function, division
from mitmproxy import addons
from mitmproxy import controller
from mitmproxy import options


class TAddon:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Addon(%s)" % self.name


def test_simple():
    o = options.Options()
    m = controller.Master(o)
    a = addons.Addons(m)
    a.add(o, TAddon("one"))
    assert a.has_addon("one")
    assert not a.has_addon("two")
