from mitmproxy.contentviews import mqtt
from . import full_eval


def _test_view_mqtt(data, expected_text):
    """ testing helper for single line messages """
    v = full_eval(mqtt.ViewMQTT())
    content_type, output = v(data)
    assert content_type == "MQTT"
    assert output == [[('text', expected_text)]]


def _test_view_mqtt_multiline(data, expected_texts):
    """ testing helper for multiline messages """
    v = full_eval(mqtt.ViewMQTT())
    content_type, output = v(data)
    assert content_type == "MQTT"

    expected_outputs = list(map(lambda text: [('text', text)], expected_texts))
    assert output == expected_outputs


def _test_view_mqtt_unsupported(data, type):
    _test_view_mqtt(data, f"Packet type {type} is not supported yet!")


def test_view_mqtt_CONNECT():
    data = b"""\x10\xba\x01\x00\x04MQTT\x04\x06\x00\x1e\x00\x1156:6F:5E:6A:01:05\x00-xxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/out\x00l{"body":{"parameters":null},"header":{"from":"56:6F:5E:6A:01:05","messageId":"disconnected","type":"event"}}"""
    expected_texts = ["[CONNECT]", "",
                      "Client Id: 56:6F:5E:6A:01:05",
                      "Will Topic: xxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/out",
                      """Will Message: {"body":{"parameters":null},"header":{"from":"56:6F:5E:6A:01:05","messageId":"disconnected","type":"event"}}""",
                      "User Name: None", "Password: None"]
    _test_view_mqtt_multiline(data, expected_texts)


def test_view_mqtt_PUBLISH():
    data = b"""\x32\x9a\x01\x00\x2dxxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/out\x00\x04{"body":{"parameters":null},"header":{"from":"56:6F:5E:6A:01:05","messageId":"connected","type":"event"}}"""
    expected_text = """[PUBLISH] '{"body":{"parameters":null},"header":{"from":"56:6F:5E:6A:01:05","messageId":"connected","type":"event"}}' to topic 'xxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/out'"""
    _test_view_mqtt(data, expected_text)


def test_view_mqtt_SUBSCRIBE():
    _test_view_mqtt(
        b"\x82\x31\x00\x03\x00\x2cxxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/in\x01",
        "[SUBSCRIBE] sent topic filters: 'xxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/in'")


def test_view_mqtt_SUBACK():
    _test_view_mqtt_unsupported(b"\x90\x00", 'SUBACK')


def test_view_mqtt__UNSUBSCRIBE():
    _test_view_mqtt_unsupported(b"\xA0\x00", 'UNSUBSCRIBE')


def test_view_mqtt_PING():
    _test_view_mqtt(b"\xC0\x00", '[PINGREQ]')
    _test_view_mqtt(b"\xD0\x00", '[PINGRESP]')

