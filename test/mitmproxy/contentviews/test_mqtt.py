from mitmproxy.contentviews import mqtt
from . import full_eval


def test_view_mqtt_pingreq():
    v = full_eval(mqtt.ViewMQTT())
    data = b"\xC0\x00"  # PINGREQ
    content_type, output = v(data)
    assert content_type == "MQTT"
    assert output == [[('text', '[PINGREQ]')]]
