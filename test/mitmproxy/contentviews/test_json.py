from mitmproxy.contentviews import json
from . import full_eval


def test_pretty_json():
    assert json.pretty_json(b'{"foo": 1}')
    assert not json.pretty_json(b"moo")
    assert json.pretty_json(b'{"foo" : "\xe4\xb8\x96\xe7\x95\x8c"}')  # utf8 with chinese characters
    assert not json.pretty_json(b'{"foo" : "\xFF"}')


def test_view_json():
    v = full_eval(json.ViewJSON())
    assert v(b"{}")
    assert not v(b"{")
    assert v(b"[1, 2, 3, 4, 5]")
