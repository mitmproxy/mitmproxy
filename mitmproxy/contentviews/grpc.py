from typing import Optional
import typing

from . import base
from mitmproxy.contrib.kaitaistruct.google_protobuf import GoogleProtobuf
from mitmproxy.contrib.kaitaistruct.vlq_base128_le import VlqBase128Le
from mitmproxy import flow, http
from enum import Enum

import struct
import gzip


class ProtoParserFlat:
    def __init__(self, data) -> None:
        self.data: bytes = data
        self.root_message: ProtoParserFlat.Message = ProtoParserFlat.Message(data)

    def to_string(self) -> str:
        return self.root_message.to_string()

    class Message:
        def __init__(self, data: bytes, parent_tags: typing.List[int] = []) -> None:
            self.data: bytes = data
            self.parent_tags: typing.List[int] = parent_tags
            self.parsed: typing.List[ProtoParserFlat.Field] = self.parse_message(data, parent_tags=parent_tags)

        @staticmethod
        def parse_message(message: bytes, parent_tags = []) -> typing.List:
            res: typing.List[ProtoParserFlat.Field] = []

            pb = GoogleProtobuf.from_bytes(message)
            for pair in pb.pairs:
                pair: GoogleProtobuf.Pair = pair
                tag = pair.field_tag
                wt = pair.wire_type
                if wt == GoogleProtobuf.Pair.WireTypes.group_start or wt == GoogleProtobuf.Pair.WireTypes.group_end:
                    # ignore deprecated types without values
                    continue
                v = pair.value  # for WireType bit-32 and bit-64
                decoding = ProtoParserFlat.Field.DecodedTypes.unknown
                # see: https://www.oreilly.com/library/view/grpc-up-and/9781492058328/ch04.html
                if wt == GoogleProtobuf.Pair.WireTypes.len_delimited:
                    v: GoogleProtobuf.DelimitedBytes = v
                    v = v.body
                    decoding = ProtoParserFlat.Field.DecodedTypes.bytes
                if wt == GoogleProtobuf.Pair.WireTypes.varint:
                    v: VlqBase128Le = v
                    v = v.value
                    if int(v).bit_length() > 32:
                        decoding = ProtoParserFlat.Field.DecodedTypes.uint64
                    else:
                        decoding = "uint32"
                if wt == GoogleProtobuf.Pair.WireTypes.bit_64:
                    # exists in Protobuf for efficient encoding, when decoded comes down to uint64
                    decoding = ProtoParserFlat.Field.DecodedTypes.fixed64
                if wt == GoogleProtobuf.Pair.WireTypes.bit_32:
                    # exists in Protobuf for efficient encoding, when decoded comes down to uint32
                    decoding = ProtoParserFlat.Field.DecodedTypes.fixed32

                field = ProtoParserFlat.Field(decoding=decoding, wire_type=wt, tag=tag, value=v, parent_tags=parent_tags)
                res.append(field)
            return res

        def to_string(self) -> str:
            return "\n".join([f.to_string() for f in self.parsed])

    class Field:
        class DecodedTypes(Enum):
            # varint
            int32 = 0
            int64 = 1
            uint32 = 2
            uint64 = 3
            sint32 = 4  # ZigZag encoding
            sint64 = 5  # ZigZag encoding
            bool = 6
            enum = 7
            # bit_32
            fixed32 = 8
            sfixed32 = 9
            float = 10
            # bit_64
            fixed64 = 11
            sfixed64 = 12
            double = 13
            # len_delimited
            string = 14
            bytes = 15
            message = 16
            packed_repeated_field = 17

            unknown = 18

        def __init__(
            self,
            wire_type: GoogleProtobuf.Pair.WireTypes,
            decoding: DecodedTypes,
            tag: int,
            value = None,
            parent_tags: typing.List[int] = [],
        ) -> None:
            self.wire_type: GoogleProtobuf.Pair.WireTypes = wire_type
            self.decoding: ProtoParserFlat.Field.DecodedTypes = decoding
            self.value: any = value
            self.tag: int = tag
            self.parent_tags: typing.Optional[typing.List[int]] = parent_tags

        def _gen_tag_str(self):
            tags = self.parent_tags[:]
            tags.append(self.tag)
            return ".".join([str(tag) for tag in tags])

        @property
        def wire_type_str(self):
            return str(self.wire_type).split(".")[-1]

        @property
        def decoding_str(self):
            return str(self.decoding).split(".")[-1]

        @property
        def value_as_bytes(self) -> bytes:
            if isinstance(self.value, bytes):
                return self.value
            elif isinstance(self.value, int):
                if self.value.bit_length() > 64:
                    # originates from wiretype varint/bit_32/bit64 and should never convert to types >64bit
                    raise ValueError("Value exceeds 64bit, violating protobuf specs")
                elif self.value.bit_length() > 32:
                    # packing uses network byte order (to assure consistent results across architectures)
                    return struct.pack("!Q", self.value)
                else:
                    # packing uses network byte order (to assure consistent results across architectures)
                    return struct.pack("!I", self.value)

        @property
        def value_as_hexstr(self, prefix="0x") -> str:
            return prefix + self.value_as_bytes.hex()

        @property
        def value_as_float(self) -> float:
            # handles double (64bit) and float (32bit)
            # assumes Network Byte Order (big endian)
            # usable for (WireType --> Protobuf Type):
            #   varint --> double/float (not intended by ProtoBuf, but used in the wild)
            #   bit_32 --> float
            #   bit_64 --> double
            #   len_delimited --> 4 bytes: float / 8 bytes: double / other sizes return NaN
            v = self.value_as_bytes
            if len(v) == 4:
                return struct.unpack("!f", v)[0]
            elif len(v) == 8:
                return struct.unpack("!d", v)[0]
            # no need to raise an Exception
            return float("NaN")

        def value_as_utf8(self, escape_invalid=True, escape_newline=True) -> str:
            if isinstance(self.value, bytes):
                res = self.value.decode("utf-8", "backslashreplace") if escape_invalid else self.value.decode("utf-8")
                return res.replace("\n", "\\n") if escape_newline else res
            return str(self.value)

        # ToDo: Test implementation, rework (only acts on string, not data struct)
        @property
        def value_as_message_str(self) -> str:
            # ToDo: Failover strategy
            if self.wire_type == GoogleProtobuf.Pair.WireTypes.len_delimited:
                parent_tags = self.parent_tags[:]
                parent_tags.append(self.tag)
                try:
                    m = ProtoParserFlat.Message(data=self.value, parent_tags=parent_tags)
                    self.decoding = ProtoParserFlat.Field.DecodedTypes.message
                    if len(m.parsed) == 0:
                        return ""
                    return "\n" + m.to_string()
                except:
                    # failed to parse
                    self.decoding = ProtoParserFlat.Field.DecodedTypes.string
                    return self.value_as_utf8()
            else:
                # self.decoding = ProtoParserFlat.Field.DecodedTypes.string
                return self.value_as_utf8()

        def to_string(self):
            v = self.value_as_message_str
            return "{} [{}-->{}]: {}".format(self._gen_tag_str(), self.wire_type_str, self.decoding_str, v)


def grpc_parse_message(data, compression):
    while data:
        try:
            compressed, length = struct.unpack('!?i', data[:5])
            message = struct.unpack('!%is' % length, data[5:5 + length])[0]
            if compressed:
                # assume gzip, actual compression has to be parsed from 'grpc-encoding' header
                # see also: https://www.oreilly.com/library/view/grpc-up-and/9781492058328/ch04.html
                message = gzip.decompress(message)
        except:
            print("Invalid gRPC message: ", (data,))
            break
        # p = ProtoParserFlat(message)
        # ctx.log.info(p.to_string())
        # yield compressed, message
        yield compressed, ProtoParserFlat(message).to_string()
        data = data[5 + length:]


def format_pbuf(message):
    yield [("text", ProtoParserFlat(message).to_string())]


def format_grpc(data, compression="gzip"):
    message_count = 0
    for compressed, pb_str in grpc_parse_message(data, compression):
        headline = 'gRPC message ' + str(message_count) + ' (compressed ' + str(compressed) + ')'

        yield [("text", headline)]
        yield [("text", pb_str)]


class ViewGrpcProtobuf(base.View):
    """Human friendly view of protocol buffers
    The view uses the protoc compiler to decode the binary
    """

    name = "gRPC/Protocol Buffer"
    __content_types_pb = [
        "application/x-protobuf",
        "application/x-protobuffer",
        "application/grpc-proto",
    ]
    __content_types_grpc = [
        "application/grpc",
    ]

    # first value serves as default for compressed messages, if 'grpc-encoding' header is missing
    __valid_grpc_encodings = [
        "gzip",
        "identity",
        "deflate",
    ]

    # Note: result '-> contentviews.TViewResult' does not work at the stage where built-in content views get added
    def __call__(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        flow: Optional[flow.Flow] = None,
        http_message: Optional[http.Message] = None,
        **unknown_metadata,
    ) -> any:
        decoded = None
        format = ""
        if content_type in self.__content_types_grpc:
            # If gRPC messages are flagged to be compressed, the compression algorithm is expressed in the
            # 'grpc-encoding' header.
            try:
                h = http_message.headers["grpc-encoding"]
                grpc_encoding = h if h in self.__valid_grpc_encodings else self.__valid_grpc_encodings[0]
            except:
                grpc_encoding = self.__valid_grpc_encodings[0]

            decoded = format_grpc(data, grpc_encoding)
            format = "gRPC"
        else:
            decoded = format_pbuf(data)
            format = "Protobuf (flattened)"

        if not decoded:
            raise ValueError("Failed to parse input.")

        return format, decoded

    def render_priority(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        flow: Optional[flow.Flow] = None,
        http_message: Optional[http.Message] = None,
        **unknown_metadata,
    ) -> float:
        if bool(data) and content_type in self.__content_types_grpc:
            return 1
        if bool(data) and content_type in self.__content_types_pb:
            # replace existing protobuf renderer preference (adjust by option)
            return 1.5
        else:
            return 0
