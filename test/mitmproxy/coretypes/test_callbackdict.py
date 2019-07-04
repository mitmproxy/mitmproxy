from mitmproxy.coretypes.callbackdict import CallbackDict


class CheckCallback():
    def __init__(self):
        self.called = False

    def callback(self):
        self.called = True


def test_add():
    d = CallbackDict(a="hello", b="mum")
    c = CheckCallback()
    d.callback = c.callback

    d['c'] = "boy"

    assert c.called is True
    assert d == dict(a="hello", b="mum", c="boy")


def test_update():
    d = CallbackDict(a="hello", b="mum")
    c = CheckCallback()
    d.callback = c.callback

    d['b'] = "boy"

    assert c.called is True
    assert d == dict(a="hello", b="boy")


def test_remove():
    d = CallbackDict(a="hello", b="mum")
    c = CheckCallback()
    d.callback = c.callback

    del d['b']

    assert c.called is True
    assert d == dict(a="hello")
