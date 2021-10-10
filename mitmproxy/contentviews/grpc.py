from __future__ import annotations  # for typing with forward declarations
from dataclasses import dataclass, field
from typing import Optional
import typing

from . import base
from mitmproxy.contrib.kaitaistruct.google_protobuf import GoogleProtobuf
from mitmproxy.contrib.kaitaistruct.vlq_base128_le import VlqBase128Le
from mitmproxy import flow, http, contentviews, ctx, flowfilter
from enum import Enum

import struct
import gzip


class ProtoParser:
    @dataclass
    class ParserRule:
        field_definitions: typing.List[ProtoParser.ParserFieldDefinition]
        name: str = ""
        description: str = ""
        # rule is only applied if flow filter matches
        filter: str = ""
        # should rule be applied to request messages
        apply_request: bool = True
        # should rule be applied to response messages
        apply_response: bool = False
        # only used internally
        _applies: bool = False

    @dataclass
    class ParserFieldDefinition:
        # the tag of the field to apply the definition to
        # while a field tag is a single number, this parameter takes the "full qualified" tag
        # to uniquely identify a message field (f.e. '1.2.1.3')
        tag: str

        # the 'field_tag' could be considered as "absolute path" to match a unique field, yet
        # protobuf allows to uses the same nested message in different positions of the parent message
        # The 'root_tag' parameter allows to apply the field definition to different "leafs nodes"
        # of a message.
        #
        # Example 1:
        # ----------
        # tag = '1.2'
        # root_tags = [] (default)
        #
        # applies to: tag '1.2'
        #
        # Example 2:
        # ----------
        # tag = '1.3'
        # root_tags = ['1.2', '2.5']
        #
        # applies to: tag '1.2.1.3' and tag '2.5.1.3'
        # does not apply to: '1.3', unless root_tag is extended to root_tag = ['1.2', '2.5', '']
        root_tags: typing.List[str] = field(default_factory=list)

        # optional: intended decoding for visualization (parser fails over to alternate decoding if not possible)
        intended_decoding: ProtoParser.DecodedTypes = None

        # optional: intended decoding for visualization (parser fails over to alternate decoding if not possible)
        name: ProtoParser.DecodedTypes = None

    @dataclass
    class ParserOptions:
        # output should contain wiretype of fields
        include_wiretype: bool = False

        # output should contain the fields which describe nested messages
        # (the nested messages bodies are always included, but the "header fields" could
        # add unnecessary output overhead)
        exclude_message_headers: bool = False

        # optional: rules
        rules: typing.List[ProtoParser.ParserRule] = field(default_factory=list)

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
        def __init__(
            self,
            data: bytes,
            options: ProtoParser.ParserOptions,
            parent_field: ProtoParser.Field = None,
        ) -> None:
            self.data: bytes = data
            self.parent_field: ProtoParser.Field = parent_field
            self.options: ProtoParser.ParserOptions = options
            try:
                self.fields: typing.List[ProtoParser.Field] = self.parse_message_fields(data)
            except:
                raise ValueError("not a valid protobuf message")

        @property
        def is_root_message(self):
            return False if self.parent_field else True

        @property
        def root_message(self):
            if self.is_root_message:
                return self
            else:
                return self.parent_field.root_message

        @property
        def tag_history(self):
            if self.is_root_message:
                return []
            else:
                tags = self.parent_field.tag_history()[:]
                return tags

        def parse_message_fields(self, message: bytes) -> typing.List:
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
                preferred_decoding = ProtoParser.DecodedTypes.unknown
                # see: https://www.oreilly.com/library/view/grpc-up-and/9781492058328/ch04.html
                if wt == GoogleProtobuf.Pair.WireTypes.len_delimited:
                    v: GoogleProtobuf.DelimitedBytes = v
                    v = v.body
                    # always try to parse length delimited data as nested protobuf message
                    preferred_decoding = ProtoParser.DecodedTypes.message
                if wt == GoogleProtobuf.Pair.WireTypes.varint:
                    v: VlqBase128Le = v
                    v = v.value
                    if int(v).bit_length() > 32:
                        preferred_decoding = ProtoParser.DecodedTypes.uint64
                    else:
                        preferred_decoding = ProtoParser.DecodedTypes.uint32
                if wt == GoogleProtobuf.Pair.WireTypes.bit_64:
                    # exists in Protobuf for efficient encoding, when decoded comes down to uint64
                    preferred_decoding = ProtoParser.DecodedTypes.fixed64
                if wt == GoogleProtobuf.Pair.WireTypes.bit_32:
                    # exists in Protobuf for efficient encoding, when decoded comes down to uint32
                    preferred_decoding = ProtoParser.DecodedTypes.fixed32

                field = ProtoParser.Field(
                    preferred_decoding=preferred_decoding,
                    wire_type=wt,
                    tag=tag,
                    wire_value=v,
                    owning_message=self,
                    options=self.options
                )
                res.append(field)
            return res

        def gen_list(self) -> typing.Generator[typing.Dict]:
            for f in self.fields:
                for field_val in f.gen_list():
                    yield field_val

        def gen_string_lines(self) -> typing.Generator[str]:
            # Excluding fields containing message headers simplifies the view, but without
            # knowing the message tags, they can not be used in a custom definition, in order
            # to declare a different interpretation for the message (the message is a length-delimeted
            # field value, which could alternatively be parsed as 'str' or 'bytes' if the field tag
            # is known)
            for field_dict in self.gen_list():
                if self.options.exclude_message_headers and field_dict["decoding"] == "message":
                    continue

                if self.options.include_wiretype:
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

        def gen_string_rows(self) -> typing.Generator[typing.Tuple[str, ...]]:
            # Excluding fields containing message headers simplifies the view, but without
            # knowing the message tags, they can not be used in a custom definition, in order
            # to declare a different interpretation for the message (the message is a length-delimeted
            # field value, which could alternatively be parsed as 'str' or 'bytes' if the field tag
            # is known)
            for field_dict in self.gen_list():
                if self.options.exclude_message_headers and field_dict["decoding"] == "message":
                    continue

                if self.options.include_wiretype:
                    col1 = "[{}->{}]".format(field_dict["wireType"], field_dict["decoding"])
                else:
                    col1 = "[{}]".format(field_dict["decoding"])
                col2 = field_dict["name"]  # empty string if not set (consumes no space)
                col3 = field_dict["tag"]
                col4 = field_dict["val"]
                yield col1, col2, col3, col4

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
            preferred_decoding: ProtoParser.DecodedTypes,
            tag: int,
            wire_value: GoogleProtobuf.Pair.WireTypes,
            owning_message: ProtoParser.Message,
            options: ProtoParser.ParserOptions,
        ) -> None:
            self.wire_type: GoogleProtobuf.Pair.WireTypes = wire_type
            self.preferred_decoding: ProtoParser.DecodedTypes = preferred_decoding
            self.wire_value: any = wire_value
            self.tag: int = tag
            self.owning_message: ProtoParser.Message = owning_message
            self.options: ProtoParser.ParserOptions = options
            self.name: str = ""
            if self.owning_message.is_root_message:
                self.parent_tags = []
            else:
                self.parent_tags = self.owning_message.parent_field.parent_tags[:]
                self.parent_tags.append(self.owning_message.parent_field.tag)

            self.apply_rules()

        def apply_rules(self, only_first_hit=True):
            tag_str = self._gen_tag_str()
            name = None
            decoding = None

            try:
                for rule in self.options.rules:
                    if not rule._applies:
                        continue
                    for fd in rule.field_definitions:
                        match = False
                        if len(fd.root_tags) == 0 and fd.tag == tag_str:
                            match = True
                        else:
                            for rt in fd.root_tags:
                                if rt + fd.tag == tag_str:
                                    match = True
                                    break
                        if match:
                            if only_first_hit:
                                # only first match
                                self.name = fd.name
                                self.preferred_decoding = fd.intended_decoding
                                return
                            else:
                                # overwrite matches till last rule was inspected
                                # (f.e. allows to define name in one rule and intended_decoding in another one)
                                name = fd.name if fd.name else name
                                decoding = fd.intended_decoding if fd.intended_decoding else decoding

                if name:
                    self.name = name
                if decoding:
                    self.preferred_decoding = decoding
            except Exception as e:
                ctx.log.warn(e)

        def _gen_tag_str(self):
            tags = self.parent_tags[:]
            tags.append(self.tag)
            return ".".join([str(tag) for tag in tags])

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
                        if failover_decoding == intended_decoding:
                            continue  # don't try it twice
                        try:
                            return failover_decoding, self.decode_as(failover_decoding)
                        except:
                            # move on with next
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
                    return ProtoParser.Message(
                        data=self.wire_value,
                        options=self.options,
                        parent_field=self
                    )

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
            v = self._value_as_bytes()
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

        def _wire_type_str(self):
            return str(self.wire_type).split(".")[-1]

        def _decoding_str(self, decoding: ProtoParser.DecodedTypes):
            return str(decoding).split(".")[-1]

        def wire_value_as_utf8(self, escape_invalid=True, escape_newline=True) -> str:
            if isinstance(self.wire_value, bytes):
                res = self.wire_value.decode("utf-8", "backslashreplace") if escape_invalid else self.wire_value.decode("utf-8")
                return res.replace("\n", "\\n") if escape_newline else res
            return str(self.wire_value)

        def value_as_dict(self):
            selected_decoding, decoded_val = self.safe_decode_as(self.preferred_decoding)
            return {
                "tag": self._gen_tag_str(),
                "wireType": self._wire_type_str(),
                "decoding": self._decoding_str(selected_decoding),
                "name": self.name,
                "val": str(decoded_val)
            }

        def gen_list(self):
            selected_decoding, decoded_val = self.safe_decode_as(self.preferred_decoding)
            if isinstance(decoded_val, ProtoParser.Message):
                yield {
                        "tag": self._gen_tag_str(),
                        "wireType": self._wire_type_str(),
                        "decoding": self._decoding_str(selected_decoding),
                        "name": self.name,
                        "val": ""
                }
                for field_dict in decoded_val.gen_list():
                    yield field_dict
            else:
                yield {
                    "tag": self._gen_tag_str(),
                    "wireType": self._wire_type_str(),
                    "decoding": self._decoding_str(selected_decoding),
                    "name": self.name,
                    "val": str(decoded_val)
                }

    def __init__(self, data: bytes, parser_options=ParserOptions()) -> None:
        self.data: bytes = data
        self.options = parser_options
        self.root_message: ProtoParser.Message = ProtoParser.Message(data, options=self.options)

    def gen_str_lines(self) -> typing.Generator[str]:
        for f in self.root_message.gen_string_lines():
            yield f

    def gen_str_rows(self) -> typing.Generator[str]:
        for f in self.root_message.gen_string_rows():
            yield f


# Note: all content view formating functionality is kept out of the ProtoParser class, to
#       allow it to be use independently
def format_table(
    table_rows: typing.Iterable[typing.Tuple[str, ...]]
) -> typing.Iterator[base.TViewLine]:
    """
    Helper function to render tables with variable column count (move to contentview base, if needed elsewhere)

    Note: The function has to copy all values from a generator to a list, as the list of rows has to be
          processed twice (to determin the column widths first). The same is true for 'base.format_pairs'.
    """
    rows: typing.List[typing.Tuple[str, ...]] = []
    col_count = 0
    cols_width: typing.List[int] = []
    for row in table_rows:
        col_count = max(col_count, len(row))
        while len(cols_width) < col_count:
            cols_width.append(0)
        for col_num in range(len(row)):
            cols_width[col_num] = max(len(row[col_num]), cols_width[col_num])

        # store row in list
        rows.append(row)

    # ToDo: width of contentview has to be fetched to limit the width of columns to a usable value
    for i in range(len(cols_width)):
        cols_width[i] = min(cols_width[i], 100)

    for row in rows:
        line: base.TViewLine = []
        for col_num in range(len(row)):
            col_val = row[col_num].ljust(cols_width[col_num] + 2)
            line.append(("text", col_val))
        yield line


def parse_grpc_messages(data, compression_scheme) -> typing.Generator[typing.Tuple[bool, bytes]]:
    """Generator iterates over body data and returns a boolean indicating if the messages
    was compressed, along with the raw message data (decompressed) for each gRPC message
    contained in the body data"""
    while data:
        try:
            msg_is_compressed, length = struct.unpack('!?i', data[:5])
            decoded_message = struct.unpack('!%is' % length, data[5:5 + length])[0]
        except Exception as e:
            raise ValueError("invalid gRPC message") from e

        if msg_is_compressed:
            if compression_scheme == "gzip":
                try:
                    decoded_message = gzip.decompress(decoded_message)
                except:
                    raise ValueError("Failed to decompress gRPC message with gzip")
            elif compression_scheme == "deflate":
                raise NotImplementedError("no real-world example to test with, yet")
            else:
                raise NotImplementedError("unknown/invalid compression algorithm: " + compression_scheme)

        yield msg_is_compressed, decoded_message
        data = data[5 + length:]


# hacky fix for mitmproxy issue:
#
# mitmproxy handles Exceptions in the contenview's __call__ function, by
# failing over to 'Raw' view. The intention was to use this behavior to
# pass up Exceptions thrown inside the generator function ('format_pbuf'
# and 'format_grpc') to the __call__ function.
# This usually works fine if the contentview is initialized on a flow
# with invalid data.
# When the flow data gets invalidated in the edit mode, mitmproxy re-calls
# the generator functions outside the contentviews '__call__' method.
#
# This happens in the 'safe_to_print' function of 'mitmproxy/contentvies/__init__.py'
#
#  def safe_to_print(lines, encoding="utf8"):
#    """
#    Wraps a content generator so that each text portion is a *safe to print* unicode string.
#    """
#    for line in lines:  # <------ this code re-iterates lines and thus calls generators, without using the views __call__ function
#        clean_line = []
#        for (style, text) in line:
#            if isinstance(text, bytes):
#                text = text.decode(encoding, "replace")
#            text = strutils.escape_control_characters(text)
#            clean_line.append((style, text))
#        yield clean_line
#
# In result, mitmproxy crashes if the generator functions raise Exception to indicate
# data parsing errors.
# To deal with this, the generator function gets converted into a list inside the
# __call__ function. Ultimately, exceptions are raised directly from within __call__
# instead in cases where the generator is accessed externally without exception handling.
def hack_generator_to_list(generator_func):
    return [x for x in generator_func]


def format_pbuf(message, parser_options: ProtoParser.ParserOptions):
    for l in format_table(ProtoParser(message, parser_options).gen_str_rows()):
        yield l


def format_grpc(data, parser_options: ProtoParser.ParserOptions, compression_scheme="gzip"):
    message_count = 0
    for compressed, pb_message in parse_grpc_messages(data, compression_scheme):
        headline = 'gRPC message ' + str(message_count) + ' (compressed ' + str(compressed) + ')'

        yield [("text", headline)]
        for l in format_pbuf(pb_message, parser_options):
            yield l


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

    # first value serves as default algorithm for compressed messages, if 'grpc-encoding' header is missing
    __valid_grpc_encodings = [
        "gzip",
        "identity",
        "deflate",
    ]

    # allows to take external ParserOptions object. goes with defaults otherwise
    def __init__(self, parser_options: ProtoParser.ParserOptions=None) -> None:
        super().__init__()
        self.parser_options = parser_options if parser_options else ProtoParser.ParserOptions()
        self.test()

    # ToDo: remove me
    def test(self):
        # overwrites options handed in to view
        rules = [
            ProtoParser.ParserRule(
                name = "Google reverse Geo coordinate lookup request",
                filter = "geomobileservices-pa.googleapis.com/google.internal.maps.geomobileservices.geocoding.v3mobile.GeocodingService/ReverseGeocode",  # noqa: E501
                apply_request=True,
                apply_response=False,
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(tag="1", name="position"),
                    ProtoParser.ParserFieldDefinition(tag="1.1", name="latitude", intended_decoding=ProtoParser.DecodedTypes.double),
                    ProtoParser.ParserFieldDefinition(tag="1.2", name="longitude", intended_decoding=ProtoParser.DecodedTypes.double),
                    ProtoParser.ParserFieldDefinition(tag="3", name="country"),
                    ProtoParser.ParserFieldDefinition(tag="7", name="app"),
                ]
            ),
            ProtoParser.ParserRule(
                name = "Google reverse Geo coordinate lookup response",
                filter = "geomobileservices-pa.googleapis.com/google.internal.maps.geomobileservices.geocoding.v3mobile.GeocodingService/ReverseGeocode",  # noqa: E501
                apply_request=False,
                apply_response=True,
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(tag="1.2", name="address"),
                    ProtoParser.ParserFieldDefinition(tag="1.3", name="address array element"),
                    ProtoParser.ParserFieldDefinition(tag="1.3.2", name="element value long"),
                    ProtoParser.ParserFieldDefinition(tag="1.3.3", name="element value short"),
                    ProtoParser.ParserFieldDefinition(tag="", root_tags=["1.5.1", "1.5.3", "1.5.4", "1.5.5", "1.5.6"], name="position"),
                    ProtoParser.ParserFieldDefinition(tag=".1", root_tags=["1.5.1", "1.5.3", "1.5.4", "1.5.5", "1.5.6"], name="latitude", intended_decoding=ProtoParser.DecodedTypes.double),  # noqa: E501
                    ProtoParser.ParserFieldDefinition(tag=".2", root_tags=["1.5.1", "1.5.3", "1.5.4", "1.5.5", "1.5.6"], name="longitude", intended_decoding=ProtoParser.DecodedTypes.double),  # noqa: E501
                    ProtoParser.ParserFieldDefinition(tag="7", name="app"),
                ]
            ),
            ProtoParser.ParserRule(
                name = "Snapchat targeting query request",
                filter = "api.snapchat.com/snapchat.cdp.cof.CircumstancesService/targetingQuery",
                apply_request=True,
                apply_response=False,
                field_definitions=[
                    ProtoParser.ParserFieldDefinition(tag="", root_tags=["5", "8"], name="res_x"),
                    ProtoParser.ParserFieldDefinition(tag="", root_tags=["6", "9"], name="res_y"),
                    ProtoParser.ParserFieldDefinition(tag="16", name="guid"),
                    ProtoParser.ParserFieldDefinition(tag="24", name="source lib"),
                    ProtoParser.ParserFieldDefinition(tag="29", name="timestamp"),
                ]
            ),
        ]

        self.parser_options.rules = rules

    def __call__(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        flow: Optional[flow.Flow] = None,
        http_message: Optional[http.Message] = None,
        **unknown_metadata,
    ) -> contentviews.TViewResult:
        # activate / deactivate rules depending on flowfilter
        # not optimal, as this acts on an global options instance, but only used by a single view at a given time
        is_request = isinstance(http_message, http.Request)
        for rule in self.parser_options.rules:
            if is_request and not rule.apply_request:
                rule._applies = False
                continue
            if not is_request and not rule.apply_response:
                rule._applies = False
                continue
            if flowfilter.match(rule.filter, flow=flow):
                ctx.log.info("match: " + rule.name)
                rule._applies = True
            else:
                ctx.log.info("no match: " + rule.name + " for " + flow.id)
                rule._applies = False

        if content_type in self.__content_types_grpc:
            # If gRPC messages are flagged to be compressed, the compression algorithm is expressed in the
            # 'grpc-encoding' header.
            # Try to find select compression algorithm base on head 'grpc-encoding' header.
            # If the header is not present or contains an unsupported compression, fall back to
            # 'gzip' (__valid_grpc_encodings[0]).
            # The compression scheme is only used if a gRPC message is flagged to be compressed, but
            # 'format_grpc' expects it to be always set (compression scheme could no be determined based
            # on the body data, unless additional logic gets added to analyse magic numbers of the message
            # blob)
            try:
                h = http_message.headers["grpc-encoding"]
                grpc_encoding = h if h in self.__valid_grpc_encodings else self.__valid_grpc_encodings[0]
            except:
                grpc_encoding = self.__valid_grpc_encodings[0]

            text_iter = format_grpc(
                data=data,
                parser_options=self.parser_options,
                compression_scheme=grpc_encoding
            )
            title = "gRPC"
        else:
            text_iter = format_pbuf(data, self.parser_options)
            title = "Protobuf (flattened)"

        # hacky bugfix, see description above generator functions format_pbuf/format_grpc
        try:
            text_iter = hack_generator_to_list(text_iter)
        except Exception as e:
            ctx.log.warn("gRPC contentview: {}".format(e))
            raise e

        return title, text_iter

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
