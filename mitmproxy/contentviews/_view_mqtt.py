import struct

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.utils import strutils

# from https://github.com/nikitastupin/mitmproxy-mqtt-script


class MQTTControlPacket:
    # Packet types
    (
        CONNECT,
        CONNACK,
        PUBLISH,
        PUBACK,
        PUBREC,
        PUBREL,
        PUBCOMP,
        SUBSCRIBE,
        SUBACK,
        UNSUBSCRIBE,
        UNSUBACK,
        PINGREQ,
        PINGRESP,
        DISCONNECT,
    ) = range(1, 15)

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Table_2.1_-
    Names = [
        "reserved",
        "CONNECT",
        "CONNACK",
        "PUBLISH",
        "PUBACK",
        "PUBREC",
        "PUBREL",
        "PUBCOMP",
        "SUBSCRIBE",
        "SUBACK",
        "UNSUBSCRIBE",
        "UNSUBACK",
        "PINGREQ",
        "PINGRESP",
        "DISCONNECT",
        "reserved",
    ]

    PACKETS_WITH_IDENTIFIER = [
        PUBACK,
        PUBREC,
        PUBREL,
        PUBCOMP,
        SUBSCRIBE,
        SUBACK,
        UNSUBSCRIBE,
        UNSUBACK,
    ]

    def __init__(self, packet):
        self._packet = packet
        # Fixed header
        # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718020
        self.packet_type = self._parse_packet_type()
        self.packet_type_human = self.Names[self.packet_type]
        self.dup, self.qos, self.retain = self._parse_flags()
        self.remaining_length = self._parse_remaining_length()
        # Variable header & Payload
        # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718024
        # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718026
        if self.packet_type == self.CONNECT:
            self._parse_connect_variable_headers()
            self._parse_connect_payload()
        elif self.packet_type == self.PUBLISH:
            self._parse_publish_variable_headers()
            self._parse_publish_payload()
        elif self.packet_type == self.SUBSCRIBE:
            self._parse_subscribe_variable_headers()
            self._parse_subscribe_payload()
        elif self.packet_type == self.SUBACK:
            pass
        elif self.packet_type == self.UNSUBSCRIBE:
            pass
        else:
            self.payload = None

    def pprint(self):
        s = f"[{self.Names[self.packet_type]}]"

        if self.packet_type == self.CONNECT:
            assert self.payload
            s += f"""

Client Id: {self.payload["ClientId"]}
Will Topic: {self.payload.get("WillTopic")}
Will Message: {strutils.bytes_to_escaped_str(self.payload.get("WillMessage", b"None"))}
User Name: {self.payload.get("UserName")}
Password: {strutils.bytes_to_escaped_str(self.payload.get("Password", b"None"))}
"""
        elif self.packet_type == self.SUBSCRIBE:
            s += " sent topic filters: "
            s += ", ".join([f"'{tf}'" for tf in self.topic_filters])
        elif self.packet_type == self.PUBLISH:
            assert self.payload
            topic_name = strutils.bytes_to_escaped_str(self.topic_name)
            payload = strutils.bytes_to_escaped_str(self.payload)

            s += f" '{payload}' to topic '{topic_name}'"
        elif self.packet_type in [self.PINGREQ, self.PINGRESP]:
            pass
        else:
            s = f"Packet type {self.Names[self.packet_type]} is not supported yet!"

        return s

    def _parse_length_prefixed_bytes(self, offset):
        field_length_bytes = self._packet[offset : offset + 2]
        field_length = struct.unpack("!H", field_length_bytes)[0]

        field_content_bytes = self._packet[offset + 2 : offset + 2 + field_length]

        return field_length + 2, field_content_bytes

    def _parse_publish_variable_headers(self):
        offset = len(self._packet) - self.remaining_length

        field_length, field_content_bytes = self._parse_length_prefixed_bytes(offset)
        self.topic_name = field_content_bytes

        if self.qos in [0x01, 0x02]:
            offset += field_length
            self.packet_identifier = self._packet[offset : offset + 2]

    def _parse_publish_payload(self):
        fixed_header_length = len(self._packet) - self.remaining_length
        variable_header_length = 2 + len(self.topic_name)

        if self.qos in [0x01, 0x02]:
            variable_header_length += 2

        offset = fixed_header_length + variable_header_length

        self.payload = self._packet[offset:]

    def _parse_subscribe_variable_headers(self):
        self._parse_packet_identifier()

    def _parse_subscribe_payload(self):
        offset = len(self._packet) - self.remaining_length + 2

        self.topic_filters = {}

        while len(self._packet) - offset > 0:
            field_length, topic_filter_bytes = self._parse_length_prefixed_bytes(offset)
            offset += field_length

            qos = self._packet[offset : offset + 1]
            offset += 1

            topic_filter = topic_filter_bytes.decode("utf-8")
            self.topic_filters[topic_filter] = {"qos": qos}

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718030
    def _parse_connect_variable_headers(self):
        offset = len(self._packet) - self.remaining_length

        self.variable_headers = {}
        self.connect_flags = {}

        self.variable_headers["ProtocolName"] = self._packet[offset : offset + 6]
        self.variable_headers["ProtocolLevel"] = self._packet[offset + 6 : offset + 7]
        self.variable_headers["ConnectFlags"] = self._packet[offset + 7 : offset + 8]
        self.variable_headers["KeepAlive"] = self._packet[offset + 8 : offset + 10]
        # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349229
        self.connect_flags["CleanSession"] = bool(
            self.variable_headers["ConnectFlags"][0] & 0x02
        )
        self.connect_flags["Will"] = bool(
            self.variable_headers["ConnectFlags"][0] & 0x04
        )
        self.will_qos = (self.variable_headers["ConnectFlags"][0] >> 3) & 0x03
        self.connect_flags["WillRetain"] = bool(
            self.variable_headers["ConnectFlags"][0] & 0x20
        )
        self.connect_flags["Password"] = bool(
            self.variable_headers["ConnectFlags"][0] & 0x40
        )
        self.connect_flags["UserName"] = bool(
            self.variable_headers["ConnectFlags"][0] & 0x80
        )

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718031
    def _parse_connect_payload(self):
        fields = []
        offset = len(self._packet) - self.remaining_length + 10

        while len(self._packet) - offset > 0:
            field_length, field_content = self._parse_length_prefixed_bytes(offset)
            fields.append(field_content)
            offset += field_length

        self.payload = {}

        for f in fields:
            # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349242
            if "ClientId" not in self.payload:
                self.payload["ClientId"] = f.decode("utf-8")
            # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc385349243
            elif self.connect_flags["Will"] and "WillTopic" not in self.payload:
                self.payload["WillTopic"] = f.decode("utf-8")
            elif self.connect_flags["Will"] and "WillMessage" not in self.payload:
                self.payload["WillMessage"] = f
            elif (
                self.connect_flags["UserName"] and "UserName" not in self.payload
            ):  # pragma: no cover
                self.payload["UserName"] = f.decode("utf-8")
            elif (
                self.connect_flags["Password"] and "Password" not in self.payload
            ):  # pragma: no cover
                self.payload["Password"] = f
            else:
                raise AssertionError(f"Unknown field in CONNECT payload: {f}")

    def _parse_packet_type(self):
        return self._packet[0] >> 4

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Toc398718022
    def _parse_flags(self):
        dup = None
        qos = None
        retain = None

        if self.packet_type == self.PUBLISH:
            dup = (self._packet[0] >> 3) & 0x01
            qos = (self._packet[0] >> 1) & 0x03
            retain = self._packet[0] & 0x01

        return dup, qos, retain

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Table_2.4_Size
    def _parse_remaining_length(self):
        multiplier = 1
        value = 0
        i = 1

        while True:
            encodedByte = self._packet[i]
            value += (encodedByte & 127) * multiplier
            multiplier *= 128

            if multiplier > 128 * 128 * 128:
                raise ValueError("Malformed Remaining Length")

            if encodedByte & 128 == 0:
                break

            i += 1

        return value

    # http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html#_Table_2.5_-
    def _parse_packet_identifier(self):
        offset = len(self._packet) - self.remaining_length
        self.packet_identifier = self._packet[offset : offset + 2]


class MQTTContentview(Contentview):
    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        mqtt_packet = MQTTControlPacket(data)
        return mqtt_packet.pprint()


mqtt = MQTTContentview()
