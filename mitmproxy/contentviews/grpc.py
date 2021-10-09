from __future__ import annotations  # for typing with forward declarations
from typing import Optional
import typing

from . import base
from mitmproxy.contrib.kaitaistruct.google_protobuf import GoogleProtobuf
from mitmproxy.contrib.kaitaistruct.vlq_base128_le import VlqBase128Le
from mitmproxy import flow, http
from enum import Enum

import struct
import gzip


class ProtoParser:
    def __init__(self, data) -> None:
        self.data: bytes = data
        self.root_message: ProtoParser.Message = ProtoParser.Message(data)

    def gen_string(self) -> typing.Generator[str]:
        for f in self.root_message.gen_string():
            yield f

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
        # helper
        unknown = 18

    class Message:
        def __init__(self, data: bytes, parent_tags: typing.List[int] = []) -> None:
            self.data: bytes = data
            self.parent_tags: typing.List[int] = parent_tags
            self.fields: typing.List[ProtoParser.Field] = self.parse_message_fields(data, parent_tags=parent_tags)

        @staticmethod
        def parse_message_fields(message: bytes, parent_tags = []) -> typing.List:
            res: typing.List[ProtoParser.Field] = []

            pb = GoogleProtobuf.from_bytes(message)
            for pair in pb.pairs:
                pair: GoogleProtobuf.Pair = pair
                tag = pair.field_tag
                wt = pair.wire_type
                if wt == GoogleProtobuf.Pair.WireTypes.group_start or wt == GoogleProtobuf.Pair.WireTypes.group_end:
                    # ignore deprecated types without values
                    continue
                v = pair.value  # for WireType bit-32 and bit-64
                decoding = ProtoParser.DecodedTypes.unknown
                # see: https://www.oreilly.com/library/view/grpc-up-and/9781492058328/ch04.html
                if wt == GoogleProtobuf.Pair.WireTypes.len_delimited:
                    v: GoogleProtobuf.DelimitedBytes = v
                    v = v.body
                    decoding = ProtoParser.DecodedTypes.bytes
                if wt == GoogleProtobuf.Pair.WireTypes.varint:
                    v: VlqBase128Le = v
                    v = v.value
                    if int(v).bit_length() > 32:
                        decoding = ProtoParser.DecodedTypes.uint64
                    else:
                        decoding = ProtoParser.DecodedTypes.uint32
                if wt == GoogleProtobuf.Pair.WireTypes.bit_64:
                    # exists in Protobuf for efficient encoding, when decoded comes down to uint64
                    decoding = ProtoParser.DecodedTypes.fixed64
                if wt == GoogleProtobuf.Pair.WireTypes.bit_32:
                    # exists in Protobuf for efficient encoding, when decoded comes down to uint32
                    decoding = ProtoParser.DecodedTypes.fixed32

                field = ProtoParser.Field(decoded_as=decoding, wire_type=wt, tag=tag, wire_value=v, parent_tags=parent_tags)
                res.append(field)
            return res

        # def to_string(self) -> str:
        #     return "\n".join([f.to_string() for f in self.fields])

        def gen_list(self) -> typing.Generator[typing.Dict]:
            for f in self.fields:
                for field_val in f.gen_list():
                    yield field_val

        def gen_string(self, include_wiretype=False, exclude_message_headers=True) -> typing.Generator[typing.String]:
            # Excluding fields containing message headers simplifies the view, but without
            # knowing the message tags, they can not be used in a custom definition, in order
            # to declare a different interpretation for the message (the message is a length-delimeted
            # field value, which could alternatively be parsed as 'str' or 'bytes' if the field tag
            # is known)
            for field_dict in self.gen_list():
                if exclude_message_headers and field_dict["decoding"] == "message":
                    continue

                if include_wiretype:
                    yield "{} [{}->{}]: {}".format(
                        field_dict["tag"],
                        field_dict["wireType"],
                        field_dict["decoding"],
                        field_dict["val"],
                    )
                else:
                    yield "{} [{}]: {}".format(
                        field_dict["tag"],
                        field_dict["decoding"],
                        field_dict["val"],
                    )

    class Field:
        """represents a single field of a protobuf message and handles the varios encodings.

        As mitmproxy sees the data passing by as raw protobuf message, it only knows the
        WireTypes. Each of the WireTypes could represent different Protobuf field types.
        The exact Protobuf field type can not be determined from the wire format, thus different
        options for decoding have to be supported.
        In addition the parsed WireTypes are (intermediary) stored in Python types, which adds
        some additional overhead type conversions.

        WireType            represented Protobuf Types                 Python type (intermediary)

        0: varint           int32, int64, uint32, uint64, enum,        int (*)
                            sint32, sint64 (both ZigZag encoded),      int
                            bool                                       bool
                                                                       float (**)

        1: bit_64           fixed64, sfixed64,                         int (*)
                            double                                     float

        2: len_delimited    string,                                    str
                            message,                                   class 'Message'
                            bytes,                                     bytes (*)
                            packed_repeated_field                      class 'Message' (fields with same tag)

        3: group_start      unused (deprecated)                        -
        4: group_end        unused (deprecated)                        -

        5: bit_32           fixed32, sfixed32,                         int (*)
                            float                                      float

        (*) Note 1:  Conversion between WireType and intermediary python representation
                     is handled by Kaitai protobuf decoder and always uses the python
                     representation marked with (*). Converting to alternative representations
                     is handled by this class.
        (**) Note 2: Varint is not used to represent floating point values, but some applications
                     store native floats in uint32 protobuf types (or native double in uint64).
                     Thus we allow conversion of varint to floating point values for convenience
                     (A well known APIs "hide" GPS latitude and longitude values in varint types,
                     much easier to spot such things when rendered as float)

        Ref: - https://developers.google.com/protocol-buffers/docs/proto3
             - https://developers.google.com/protocol-buffers/docs/encoding
        """

        def __init__(
            self,
            wire_type: GoogleProtobuf.Pair.WireTypes,
            decoded_as: ProtoParser.DecodedTypes,
            tag: int,
            wire_value: GoogleProtobuf.Pair.WireTypes,
            parent_tags: typing.List[int] = [],
        ) -> None:
            self.wire_type: GoogleProtobuf.Pair.WireTypes = wire_type
            self.decoded_as: ProtoParser.DecodedTypes = decoded_as
            self.wire_value: any = wire_value
            self.tag: int = tag
            self.parent_tags: typing.List[int] = parent_tags

        def safe_decode_as(
            self,
            intended_decoding: ProtoParser.DecodedTypes
        ) -> typing.Tuple[ProtoParser.DecodedTypes, any]:
            """Tries to decode as intended, applies failover, if not possible

            Returns selected decoding and decoded value"""
            if self.wire_type == GoogleProtobuf.Pair.WireTypes.varint:
                try:
                    return intended_decoding, self.decode_as(intended_decoding)
                except:
                    if int(self.wire_value).bit_length() > 32:
                        # ignore the fact that varint could exceed 64bit (would violate the specs)
                        return ProtoParser.DecodedTypes.uint64, self.wire_value
                    else:
                        return ProtoParser.DecodedTypes.uint32, self.wire_value
            elif self.wire_type == GoogleProtobuf.Pair.WireTypes.bit_64:
                try:
                    return intended_decoding, self.decode_as(intended_decoding)
                except:
                    return ProtoParser.DecodedTypes.fixed64, self.wire_value
            elif self.wire_type == GoogleProtobuf.Pair.WireTypes.bit_32:
                try:
                    return intended_decoding, self.decode_as(intended_decoding)
                except:
                    return ProtoParser.DecodedTypes.fixed32, self.wire_value
            elif self.wire_type == GoogleProtobuf.Pair.WireTypes.len_delimited:
                try:
                    return intended_decoding, self.decode_as(intended_decoding)
                except:
                    # failover strategy: message --> string (valid UTF-8) --> bytes
                    len_delimited_strategy: typing.List[ProtoParser.DecodedTypes] = [
                        ProtoParser.DecodedTypes.message,
                        ProtoParser.DecodedTypes.string,
                        ProtoParser.DecodedTypes.bytes  # should always work
                    ]
                    for failover_decoding in len_delimited_strategy:
                        try:
                            return failover_decoding, self.decode_as(failover_decoding)
                        except:
                            pass

            # we should never get here
            return ProtoParser.DecodedTypes.unknown, self.wire_value

        def decode_as(self, intended_decoding: ProtoParser.DecodedTypes):
            if self.wire_type == GoogleProtobuf.Pair.WireTypes.varint:
                if intended_decoding == ProtoParser.DecodedTypes.bool:
                    return self.wire_value != 0
                elif intended_decoding == ProtoParser.DecodedTypes.int32:
                    if self.wire_value.bit_length() > 32:
                        raise TypeError("wire value too large for int32")
                    return struct.unpack("!i", struct.pack("!I", self.wire_value))[0]
                elif intended_decoding == ProtoParser.DecodedTypes.int64:
                    if self.wire_value.bit_length() > 64:
                        raise TypeError("wire value too large for int64")
                    return struct.unpack("!q", struct.pack("!Q", self.wire_value))[0]
                elif (
                    intended_decoding == ProtoParser.DecodedTypes.uint32 or
                    intended_decoding == ProtoParser.DecodedTypes.uint64 or
                    intended_decoding == ProtoParser.DecodedTypes.enum
                ):
                    if self.wire_value.bit_length() > 64:
                        raise TypeError("wire value too large")
                    return self.wire_value  # already 'int' which was parsed as unsigned
                elif intended_decoding == ProtoParser.DecodedTypes.sint32:
                    if self.wire_value.bit_length() > 32:
                        raise TypeError("wire value too large for sint32")
                    return (self.wire_value >> 1) ^ -(self.wire_value & 1)  # zigzag_decode
                elif intended_decoding == ProtoParser.DecodedTypes.sint64:
                    if self.wire_value.bit_length() > 64:
                        raise TypeError("wire value too large for sint64")
                    # ZigZag decode
                    # Ref: https://gist.github.com/mfuerstenau/ba870a29e16536fdbaba
                    return (self.wire_value >> 1) ^ -(self.wire_value & 1)
                elif (
                    intended_decoding == ProtoParser.DecodedTypes.float or
                    intended_decoding == ProtoParser.DecodedTypes.double
                ):
                    # special case, not complying to protobuf specs
                    return self._wire_value_as_float()
            elif self.wire_type == GoogleProtobuf.Pair.WireTypes.bit_64:
                if intended_decoding == ProtoParser.DecodedTypes.fixed64:
                    return self.wire_value
                elif intended_decoding == ProtoParser.DecodedTypes.sfixed64:
                    return struct.unpack("!q", struct.pack("!Q", self.wire_value))[0]
                elif intended_decoding == ProtoParser.DecodedTypes.double:
                    return self._wire_value_as_float()
            elif self.wire_type == GoogleProtobuf.Pair.WireTypes.bit_32:
                if intended_decoding == ProtoParser.DecodedTypes.fixed32:
                    return self.wire_value
                elif intended_decoding == ProtoParser.DecodedTypes.sfixed32:
                    return struct.unpack("!i", struct.pack("!I", self.wire_value))[0]
                elif intended_decoding == ProtoParser.DecodedTypes.float:
                    return self._wire_value_as_float()
            elif self.wire_type == GoogleProtobuf.Pair.WireTypes.len_delimited:
                if intended_decoding == ProtoParser.DecodedTypes.string:
                    # According to specs, a protobuf string HAS TO be UTF-8 parsable
                    # throw exception on invalid UTF-8 chars, but escape linebreaks
                    return self.wire_value_as_utf8(escape_invalid=False, escape_newline=True)
                elif intended_decoding == ProtoParser.DecodedTypes.bytes:
                    # always works, assure to hand back a copy
                    return self.wire_value[:]
                elif intended_decoding == ProtoParser.DecodedTypes.packed_repeated_field:
                    raise NotImplementedError("currently not needed")
                elif intended_decoding == ProtoParser.DecodedTypes.message:
                    inheriting_tags = self.parent_tags[:]
                    inheriting_tags.append(self.tag)
                    return ProtoParser.Message(data=self.wire_value, parent_tags=inheriting_tags)

            # if here, there is no valid decoding
            raise TypeError("intended decoding mismatches wire type")

        def encode_from(inputval, intended_encoding: ProtoParser.DecodedTypes):
            raise NotImplementedError("Future work, needed to manipulate and re-encode protobuf message, with respect to given wire types")

        def _wire_value_as_float(self) -> float:
            # handles double (64bit) and float (32bit)
            # assumes Network Byte Order (big endian)
            # usable for (WireType --> Protobuf Type):
            #   varint --> double/float (not intended by ProtoBuf, but used in the wild)
            #   bit_32 --> float
            #   bit_64 --> double
            #   len_delimited --> 4 bytes: float / 8 bytes: double / other sizes return NaN
            v = self._value_as_bytes
            if len(v) == 4:
                return struct.unpack("!f", v)[0]
            elif len(v) == 8:
                return struct.unpack("!d", v)[0]
            # no need to raise an Exception
            raise TypeError()

        def _value_as_bytes(self) -> bytes:
            if isinstance(self.wire_value, bytes):
                return self.wire_value
            elif isinstance(self.wire_value, int):
                if self.wire_value.bit_length() > 64:
                    # originates from wiretype varint/bit_32/bit64 and should never convert to types >64bit
                    raise ValueError("Value exceeds 64bit, violating protobuf specs")
                elif self.wire_value.bit_length() > 32:
                    # packing uses network byte order (to assure consistent results across architectures)
                    return struct.pack("!Q", self.wire_value)
                else:
                    # packing uses network byte order (to assure consistent results across architectures)
                    return struct.pack("!I", self.wire_value)

        def _gen_tag_str(self):
            tags = self.parent_tags[:]
            tags.append(self.tag)
            return ".".join([str(tag) for tag in tags])

        def _wire_type_str(self):
            return str(self.wire_type).split(".")[-1]

        def _decoding_str(self, decoding: ProtoParser.DecodedTypes):
            return str(decoding).split(".")[-1]

        @property
        def wire_value_as_hexstr(self, prefix="0x") -> str:
            return prefix + self._value_as_bytes.hex()

        def wire_value_as_utf8(self, escape_invalid=True, escape_newline=True) -> str:
            if isinstance(self.wire_value, bytes):
                res = self.wire_value.decode("utf-8", "backslashreplace") if escape_invalid else self.wire_value.decode("utf-8")
                return res.replace("\n", "\\n") if escape_newline else res
            return str(self.wire_value)

        def value_as_dict(self):
            selected_decoding, decoded_val = self.safe_decode_as(self.decode_as)
            return {
                "tag": self._gen_tag_str(),
                "wireType": self._wire_type_str(),
                "decoding": self._decoding_str(selected_decoding),
                "val": str(decoded_val)
            }

        def gen_list(self):
            selected_decoding, decoded_val = self.safe_decode_as(self.decode_as)
            if isinstance(decoded_val, ProtoParser.Message):
                yield {
                        "tag": self._gen_tag_str(),
                        "wireType": self._wire_type_str(),
                        "decoding": self._decoding_str(selected_decoding),
                        "val": ""
                }
                for field_dict in decoded_val.gen_list():
                    yield field_dict
            else:
                yield {
                    "tag": self._gen_tag_str(),
                    "wireType": self._wire_type_str(),
                    "decoding": self._decoding_str(selected_decoding),
                    "val": str(decoded_val)
                }


def parse_grpc_messages(data, compression) -> typing.Generator[typing.Tuple[bool, ProtoParser]]:
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

        pb_msg_parser = ProtoParser(message)
        yield compressed, pb_msg_parser
        data = data[5 + length:]


def format_pbuf(message):
    for line in ProtoParser(message).gen_string():
        yield [("text", line)]


def format_grpc(data, compression="gzip"):
    message_count = 0
    for compressed, pb_message in parse_grpc_messages(data, compression):
        headline = 'gRPC message ' + str(message_count) + ' (compressed ' + str(compressed) + ')'

        yield [("text", headline)]
        for line in pb_message.gen_string():
            yield [("text", line)]


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
