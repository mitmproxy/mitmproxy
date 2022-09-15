from hypothesis import given
from hypothesis.strategies import binary

from mitmproxy.contentviews import mqtt
from . import full_eval

@given(binary())
def test_view_mqtt_doesnt_crash(data):
    v = full_eval(mqtt.ViewMQTT())
    v(data)
