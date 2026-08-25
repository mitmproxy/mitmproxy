import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_mqtt import mqtt


@pytest.mark.parametrize(
    "data,expected_text",
    [
        pytest.param(b"\xc0\x00", "[PINGREQ]", id="PINGREQ"),
        pytest.param(b"\xd0\x00", "[PINGRESP]", id="PINGRESP"),
        pytest.param(
            b"\x90\x00", "Packet type SUBACK is not supported yet!", id="SUBACK"
        ),
        pytest.param(
            b"\xa0\x00",
            "Packet type UNSUBSCRIBE is not supported yet!",
            id="UNSUBSCRIBE",
        ),
        pytest.param(
            b"\x82\x31\x00\x03\x00\x2cxxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/in\x01",
            "[SUBSCRIBE] sent topic filters: 'xxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/in'",
            id="SUBSCRIBE",
        ),
        pytest.param(
            b"""\x32\x9a\x01\x00\x2dxxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/out\x00\x04"""
            b"""{"body":{"parameters":null},"header":{"from":"56:6F:5E:6A:01:05","messageId":"connected","type":"event"}}""",
            """[PUBLISH] '{"body":{"parameters":null},"header":{"from":"56:6F:5E:6A:01:05","""
            """"messageId":"connected","type":"event"}}' to topic 'xxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/out'""",
            id="PUBLISH",
        ),
        pytest.param(
            b"""\x10\xba\x01\x00\x04MQTT\x04\x06\x00\x1e\x00\x1156:6F:5E:6A:01:05\x00-"""
            b"""xxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/out"""
            b"""\x00l{"body":{"parameters":null},"header":{"from":"56:6F:5E:6A:01:05","messageId":"disconnected","type":"event"}}""",
            (
                "[CONNECT]\n"
                "\n"
                "Client Id: 56:6F:5E:6A:01:05\n"
                "Will Topic: xxxx/yy/zzzzzz/56:6F:5E:6A:01:05/messages/out\n"
                "Will Message: "
                '{"body":{"parameters":null},"header":{"from":"56:6F:5E:6A:01:05","messageId":"disconnected","type":"event"}}\n'
                "User Name: None\n"
                "Password: None\n"
            ),
            id="CONNECT",
        ),
    ],
)
def test_view_mqtt(data, expected_text):
    """testing helper for single line messages"""
    assert mqtt.prettify(data, Metadata()) == expected_text


@pytest.mark.parametrize("data", [b"\xc0\xff\xff\xff\xff"])
def test_mqtt_malformed(data):
    with pytest.raises(Exception):
        mqtt.prettify(data, Metadata())
