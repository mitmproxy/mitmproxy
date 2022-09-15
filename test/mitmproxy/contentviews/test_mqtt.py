from mitmproxy.contentviews import mqtt
from . import full_eval


def _test_view_mqtt(data, expected_text):
    v = full_eval(mqtt.ViewMQTT())
    content_type, output = v(data)
    assert content_type == "MQTT"
    assert output == [[('text', f"[{expected_text}]")]]


def _test_view_mqtt_unsupported(data, expected_text):
    _test_view_mqtt(data, f"[Packet type {expected_text} is not supported yet!]")


def test_view_mqtt_CONNECT():
    _test_view_mqtt(b"\xC0\x00", '[PINGREQ]')


def test_view_mqtt_PUBLISH():
    _test_view_mqtt(b"\xC0\x00", '[PINGREQ]')


def test_view_mqtt_SUBSCRIBE():
    _test_view_mqtt(b"\xC0\x00", '[PINGREQ]')


def test_view_mqtt_PING():
    _test_view_mqtt(b"\xC0\x00", 'PINGREQ')
    _test_view_mqtt(b"\xD0\x00", 'PINGRESP')


def test_view_mqtt_SUBACK():
    _test_view_mqtt_unsupported(b"\xC0\x00", 'SUBACK')


def test_view_mqtt__UNSUBSCRIBE():
    _test_view_mqtt_unsupported(b"\xC0\x00", 'UNSUBSCRIBE')
