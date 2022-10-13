from hypothesis import given
from hypothesis.strategies import binary

from mitmproxy.contentviews import json
from . import full_eval


def test_parse_json():
    assert json.parse_json(b'{"foo": 1}')
    assert json.parse_json(b"null") is None
    assert json.parse_json(b"moo") is json.PARSE_ERROR
    assert json.parse_json(
        b'{"foo" : "\xe4\xb8\x96\xe7\x95\x8c"}'
    )  # utf8 with chinese characters
    assert json.parse_json(b'{"foo" : "\xFF"}') is json.PARSE_ERROR


def test_format_json():
    assert list(json.format_json({"data": ["str", 42, True, False, None, {}, []]}))
    assert list(json.format_json({"string": "test"})) == [
        [('text', '{'), ('text', '')],
        [('text', '    '), ('json_key', '"string"'), ('text', ': '), ('json_string', '"test"'), ('text', '')],
        [('text', ''), ('text', '}')]]
    assert list(json.format_json({"num": 4})) == [
        [('text', '{'), ('text', '')],
        [('text', '    '), ('json_key', '"num"'), ('text', ': '), ('json_number', '4'), ('text', '')],
        [('text', ''), ('text', '}')]]
    assert list(json.format_json({"bool": True})) == [
        [('text', '{'), ('text', '')],
        [('text', '    '), ('json_key', '"bool"'), ('text', ': '), ('json_boolean', 'true'), ('text', '')],
        [('text', ''), ('text', '}')]]
    assert list(json.format_json({"object": {"int": 1}})) == [
        [('text', '{'), ('text', '')],
        [('text', '    '), ('json_key', '"object"'), ('text', ': '), ('text', '{'), ('text', '')],
        [('text', '        '), ('json_key', '"int"'), ('text', ': '), ('json_number', '1'), ('text', '')],
        [('text', '    '), ('text', '}'), ('text', '')],
        [('text', ''), ('text', '}')]]
    assert list(json.format_json({"list": ["string", 1, True]})) == [
        [('text', '{'), ('text', '')],
        [('text', '    '), ('json_key', '"list"'), ('text', ': '), ('text', '[')],
        [('json_string', '        "string"'), ('text', ',')],
        [('json_number', '        1'), ('text', ',')],
        [('json_boolean', '        true'), ('text', '')],
        [('text', '    '), ('text', ']'), ('text', '')],
        [('text', ''), ('text', '}')]]


def test_view_json():
    v = full_eval(json.ViewJSON())
    assert v(b"null")
    assert v(b"{}")
    assert not v(b"{")
    assert v(b"[1, 2, 3, 4, 5]")
    assert v(b'{"foo" : 3}')
    assert v(b'{"foo": true, "nullvalue": null}')


@given(binary())
def test_view_json_doesnt_crash(data):
    v = full_eval(json.ViewJSON())
    v(data)


def test_render_priority():
    v = json.ViewJSON()
    assert v.render_priority(b"data", content_type="application/json")
    assert v.render_priority(b"data", content_type="application/json-rpc")
    assert v.render_priority(b"data", content_type="application/vnd.api+json")
    assert v.render_priority(b"data", content_type="application/acme+json")
    assert not v.render_priority(b"data", content_type="text/plain")
    assert not v.render_priority(b"", content_type="application/json")
