from hypothesis import given
from hypothesis.strategies import binary

from mitmproxy.contentviews import mqtt
from . import full_eval


def test_render_priority():
    v = mqtt.ViewMQTT()
    assert 2 == v.render_priority(
        b"""{"query": "query P { \\n }"}""", content_type="application/json"
    )
    assert 2 == v.render_priority(
        b"""[{"query": "query P { \\n }"}]""", content_type="application/json"
    )
    assert 0 == v.render_priority(
        b"""[{"query": "query P { \\n }"}]""", content_type="text/html"
    )
    assert 0 == v.render_priority(
        b"""[{"xquery": "query P { \\n }"}]""", content_type="application/json"
    )
    assert 0 == v.render_priority(b"}", content_type="application/json")


def test_format_mqtt():
    assert mqtt.format_mqtt({"query": "query P { \\n }"})


def test_format_query_list():
    assert mqtt.format_query_list([{"query": "query P { \\n }"}])


def test_view_mqtt():
    v = mqtt.ViewMQTT()
    assert v(b"""{"query": "query P { \\n }"}""", content_type="application/json")
    assert v(b"""[{"query": "query P { \\n }"}]""", content_type="application/json")


@given(binary())
def test_view_mqtt_doesnt_crash(data):
    v = full_eval(mqtt.ViewMQTT())
    v(data)
