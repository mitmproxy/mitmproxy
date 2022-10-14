from hypothesis import given
from hypothesis.strategies import binary

from msgpack import packb

from mitmproxy.contentviews import msgpack
from . import full_eval


def msgpack_encode(content):
    return packb(content, use_bin_type=True)


def test_parse_msgpack():
    assert msgpack.parse_msgpack(msgpack_encode({"foo": 1}))
    assert msgpack.parse_msgpack(b"aoesuteoahu") is msgpack.PARSE_ERROR
    assert msgpack.parse_msgpack(msgpack_encode({"foo": "\xe4\xb8\x96\xe7\x95\x8c"}))


def test_format_msgpack():
    assert list(msgpack.format_msgpack({"string": "test", "int": 1, "float": 1.44, "bool": True})) == [
        [('text', '{')],
        [('text', ''), ('text', '    '), ('msgpack_key', '"string"'), ('text', ': '), ('msgpack_string', '"test"'), ('text', ',')],
        [('text', ''), ('text', '    '), ('msgpack_key', '"int"'), ('text', ': '), ('msgpack_number', '1'), ('text', ',')],
        [('text', ''), ('text', '    '), ('msgpack_key', '"float"'), ('text', ': '), ('msgpack_number', '1.44'), ('text', ',')],
        [('text', ''), ('text', '    '), ('msgpack_key', '"bool"'), ('text', ': '), ('msgpack_boolean', 'True')],
        [('text', ''), ('text', '}')]
    ]

    assert list(msgpack.format_msgpack({"object": {"key": "value"}, "list": [1]})) == [
        [('text', '{')],
        [('text', ''), ('text', '    '), ('msgpack_key', '"object"'), ('text', ': '), ('text', '{')],
        [('text', '    '), ('text', '    '), ('msgpack_key', '"key"'), ('text', ': '), ('msgpack_string', '"value"')],
        [('text', '    '), ('text', '}'), ('text', ',')],
        [('text', ''), ('text', '    '), ('msgpack_key', '"list"'), ('text', ': '), ('text', '[')],
        [('text', '    '), ('text', '    '), ('msgpack_number', '1')],
        [('text', '    '), ('text', ']')],
        [('text', ''), ('text', '}')]]


def test_view_msgpack():
    v = full_eval(msgpack.ViewMsgPack())
    assert v(msgpack_encode({}))
    assert not v(b"aoesuteoahu")
    assert v(msgpack_encode([1, 2, 3, 4, 5]))
    assert v(msgpack_encode({"foo": 3}))
    assert v(msgpack_encode({"foo": True, "nullvalue": None}))


@given(binary())
def test_view_msgpack_doesnt_crash(data):
    v = full_eval(msgpack.ViewMsgPack())
    v(data)


def test_render_priority():
    v = msgpack.ViewMsgPack()
    assert v.render_priority(b"data", content_type="application/msgpack")
    assert v.render_priority(b"data", content_type="application/x-msgpack")
    assert not v.render_priority(b"data", content_type="text/plain")
