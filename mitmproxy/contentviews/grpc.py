from __future__ import annotations

import logging
import struct
from collections.abc import Generator
from collections.abc import Iterable
from collections.abc import Iterator
from dataclasses import dataclass
from dataclasses import field
from enum import Enum

from mitmproxy import contentviews
from mitmproxy import flow
from mitmproxy import flowfilter
from mitmproxy import http
from mitmproxy.contentviews import base
from mitmproxy.net.encoding import decode


class ProtoParser:
    @dataclass
    class ParserRule:
        """
        A parser rule lists Field definitions which are applied if the filter rule matches the flow.

        Matching on flow-level also means, a match applies to request AND response messages.
        To restrict a rule to a requests only use 'ParserRuleRequest', instead.
        To restrict a rule to a responses only use 'ParserRuleResponse', instead.
        """

        field_definitions: list[ProtoParser.ParserFieldDefinition]
        """List of field definitions for this rule """

        name: str = ""
        """Name of this rule, only used for debugging"""

        filter: str = ""
        """
        Flowfilter to select which flows to apply to ('~q' and '~s' can not be used to distinguish
        if the rule should apply to the request or response of a flow. To do so, use ParserRuleRequest
        or ParserRuleResponse. ParserRule always applies to request and response.)
        """

    @dataclass
    class ParserRuleResponse(ParserRule):
        """
        A parser rule lists Field definitions which are applied if the filter rule matches the flow.

        The rule only applies if the processed message is a server response.
        """

    @dataclass
    class ParserRuleRequest(ParserRule):
        """
        A parser rule lists Field definitions which are applied if the filter rule matches the flow.

        The rule only applies if the processed message is a client request.
        """

    @dataclass
    class ParserFieldDefinition:
        """
        Defines how to parse a field (or multiple fields with the same tag) in a protobuf messages.

        This allows to apply an intended decoding (f.e. decode uint64 as double instead) and to assign
        a descriptive name to a field. Field definitions are aggregated into rules, which also holds
        a filter to match selected HTTP messages.

        The most natural way to use this, is to describe known parts of a single protobuf message
        in a set of field descriptors, pack them into a rule and set the filter of the rule in a way,
        that it only applies to proper protobuf messages (f.e. to request traffic against an API endpoint
        matched by an URL flowfilter)
        """

        # A 'tag' could be considered as "absolute path" to match a unique field, yet
        # protobuf allows to uses the same nested message in different positions of the parent message
        # The 'tag_prefixes' parameter allows to apply the field definition to different "leafs nodes"
        # of a message.
        #
        # Example 1: match a single, absolute tag
        # ----------
        # tag = '1.2'
        # tag_prefixes = [] (default)
        #
        # applies to: tag '1.2'
        #
        # Example 2: match multiple tags with same ending
        # ----------
        # tag = '1.3'
        # tag_prefixes = ['1.2.', '2.5.']
        #
        # applies to: tag '1.2.1.3' and tag '2.5.1.3'
        # does not apply to: '1.3', unless tag_prefixes is extended to tag_prefixes = ['1.2', '2.5', '']
        #
        # Example 3: match multiple tags
        # ----------
        # tag = ''
        # tag_prefixes = ['1.2', '2.5']
        #
        # applies to: tag '1.2' and tag '1.5'

        tag: str
        """Field tag for which this description applies (including flattened tag path, f.e. '1.2.2.4')"""

        tag_prefixes: list[str] = field(default_factory=list)
        """List of prefixes for tag matching (f.e. tag_prefixes=['1.2.', '2.2.'] with tag='1' matches '1.2.1' and '2.2.1')"""

        intended_decoding: ProtoParser.DecodedTypes | None = None
        """optional: intended decoding for visualization (parser fails over to alternate decoding if not possible)"""

        name: str | None = None
        """optional: intended field for visualization (parser fails over to alternate decoding if not possible)"""

        as_packed: bool | None = False
        """optional: if set to true, the field is considered to be repeated and packed"""

    @dataclass
    class ParserOptions:
        # output should contain wiretype of fields
        include_wiretype: bool = False

        # output should contain the fields which describe nested messages
        # (the nested messages bodies are always included, but the "header fields" could
        # add unnecessary output overhead)
        exclude_message_headers: bool = False

        # optional: rules
        # rules: List[ProtoParser.ParserRule] = field(default_factory=list)

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

        # helper
        unknown = 17

    @staticmethod
    def _read_base128le(data: bytes) -> tuple[int, int]:
        res = 0
        offset = 0
        while offset < len(data):
            o = data[offset]
            res += (o & 0x7F) << (7 * offset)
            offset += 1
            if o < 0x80:
                # the Kaitai parser for protobuf support base128 le values up
                # to 8 groups (bytes). Due to the nature of the encoding, each
                # group attributes 7bit to the resulting value, which give
                # a 56 bit value at maximum.
                # The values which get encoded into protobuf variable length integers,
                # on the other hand, include full 64bit types (int64, uint64, sint64).
                # This means, the Kaitai encoder can not cover the full range of
                # possible values
                #
                # This decoder puts no limitation on the maximum value of variable
                # length integers. Values exceeding 64bit have to be handled externally
                return offset, res
        raise ValueError("varint exceeds bounds of provided data")

    @staticmethod
    def _read_u32(data: bytes) -> tuple[int, int]:
        return 4, struct.unpack("<I", data[:4])[0]

    @staticmethod
    def _read_u64(data: bytes) -> tuple[int, int]:
        return 8, struct.unpack("<Q", data[:8])[0]

    class WireTypes(Enum):
        varint = 0
        bit_64 = 1
        len_delimited = 2
        group_start = 3
        group_end = 4
        bit_32 = 5

    @staticmethod
    def read_fields(
        wire_data: bytes,
        parent_field: ProtoParser.Field | None,
        options: ProtoParser.ParserOptions,
        rules: list[ProtoParser.ParserRule],
    ) -> list[ProtoParser.Field]:
        res: list[ProtoParser.Field] = []
        pos = 0
        while pos < len(wire_data):
            # read field key (tag and wire_type)
            offset, key = ProtoParser._read_base128le(wire_data[pos:])
            # casting raises exception for invalid WireTypes
            wt = ProtoParser.WireTypes(key & 7)
            tag = key >> 3
            pos += offset

            val: bytes | int
            preferred_decoding: ProtoParser.DecodedTypes
            if wt == ProtoParser.WireTypes.varint:
                offset, val = ProtoParser._read_base128le(wire_data[pos:])
                pos += offset
                bl = val.bit_length()
                if bl > 64:
                    preferred_decoding = ProtoParser.DecodedTypes.unknown
                if bl > 32:
                    preferred_decoding = ProtoParser.DecodedTypes.uint64
                else:
                    preferred_decoding = ProtoParser.DecodedTypes.uint32
            elif wt == ProtoParser.WireTypes.bit_64:
                offset, val = ProtoParser._read_u64(wire_data[pos:])
                pos += offset
                preferred_decoding = ProtoParser.DecodedTypes.fixed64
            elif wt == ProtoParser.WireTypes.len_delimited:
                offset, length = ProtoParser._read_base128le(wire_data[pos:])
                pos += offset
                if length > len(wire_data[pos:]):
                    raise ValueError("length delimited field exceeds data size")
                val = wire_data[pos : pos + length]
                pos += length
                preferred_decoding = ProtoParser.DecodedTypes.message
            elif (
                wt == ProtoParser.WireTypes.group_start
                or wt == ProtoParser.WireTypes.group_end
            ):
                raise ValueError(f"deprecated field: {wt}")
            elif wt == ProtoParser.WireTypes.bit_32:
                offset, val = ProtoParser._read_u32(wire_data[pos:])
                pos += offset
                preferred_decoding = ProtoParser.DecodedTypes.fixed32
            else:
                # not reachable as if-else statements contain all possible WireTypes
                # wrong types raise Exception during typecasting in `wt = ProtoParser.WireTypes((key & 7))`
                raise ValueError("invalid WireType for protobuf messsage field")

            field = ProtoParser.Field(
                wire_type=wt,
                preferred_decoding=preferred_decoding,
                options=options,
                rules=rules,
                tag=tag,
                wire_value=val,
                parent_field=parent_field,
            )
            res.append(field)

        return res

    @staticmethod
    def read_packed_fields(
        packed_field: ProtoParser.Field,
    ) -> list[ProtoParser.Field]:
        if not isinstance(packed_field.wire_value, bytes):
            raise ValueError(
                f"can not unpack field with data other than bytes: {type(packed_field.wire_value)}"
            )
        wire_data: bytes = packed_field.wire_value
        tag: int = packed_field.tag
        options: ProtoParser.ParserOptions = packed_field.options
        rules: list[ProtoParser.ParserRule] = packed_field.rules
        intended_decoding: ProtoParser.DecodedTypes = packed_field.preferred_decoding

        # the packed field has to have WireType length delimited, whereas the contained
        # individual types have to have a different WireType, which is derived from
        # the intended decoding
        if (
            packed_field.wire_type != ProtoParser.WireTypes.len_delimited
            or not isinstance(packed_field.wire_value, bytes)
        ):
            raise ValueError(
                "packed fields have to be embedded in a length delimited message"
            )
        # wiretype to read has to be determined from intended decoding
        packed_wire_type: ProtoParser.WireTypes
        if (
            intended_decoding == ProtoParser.DecodedTypes.int32
            or intended_decoding == ProtoParser.DecodedTypes.int64
            or intended_decoding == ProtoParser.DecodedTypes.uint32
            or intended_decoding == ProtoParser.DecodedTypes.uint64
            or intended_decoding == ProtoParser.DecodedTypes.sint32
            or intended_decoding == ProtoParser.DecodedTypes.sint64
            or intended_decoding == ProtoParser.DecodedTypes.bool
            or intended_decoding == ProtoParser.DecodedTypes.enum
        ):
            packed_wire_type = ProtoParser.WireTypes.varint
        elif (
            intended_decoding == ProtoParser.DecodedTypes.fixed32
            or intended_decoding == ProtoParser.DecodedTypes.sfixed32
            or intended_decoding == ProtoParser.DecodedTypes.float
        ):
            packed_wire_type = ProtoParser.WireTypes.bit_32
        elif (
            intended_decoding == ProtoParser.DecodedTypes.fixed64
            or intended_decoding == ProtoParser.DecodedTypes.sfixed64
            or intended_decoding == ProtoParser.DecodedTypes.double
        ):
            packed_wire_type = ProtoParser.WireTypes.bit_64
        elif (
            intended_decoding == ProtoParser.DecodedTypes.string
            or intended_decoding == ProtoParser.DecodedTypes.bytes
            or intended_decoding == ProtoParser.DecodedTypes.message
        ):
            packed_wire_type = ProtoParser.WireTypes.len_delimited
        else:
            # should never happen, no test
            raise TypeError(
                "Wire type could not be determined from packed decoding type"
            )

        res: list[ProtoParser.Field] = []
        pos = 0
        val: bytes | int
        if packed_wire_type == ProtoParser.WireTypes.varint:
            while pos < len(wire_data):
                offset, val = ProtoParser._read_base128le(wire_data[pos:])
                pos += offset
                res.append(
                    ProtoParser.Field(
                        options=options,
                        preferred_decoding=intended_decoding,
                        rules=rules,
                        tag=tag,
                        wire_type=packed_wire_type,
                        wire_value=val,
                        parent_field=packed_field.parent_field,
                        is_unpacked_children=True,
                    )
                )
        elif packed_wire_type == ProtoParser.WireTypes.bit_64:
            if len(wire_data) % 8 != 0:
                raise ValueError("can not parse as packed bit64")
            while pos < len(wire_data):
                offset, val = ProtoParser._read_u64(wire_data[pos:])
                pos += offset
                res.append(
                    ProtoParser.Field(
                        options=options,
                        preferred_decoding=intended_decoding,
                        rules=rules,
                        tag=tag,
                        wire_type=packed_wire_type,
                        wire_value=val,
                        parent_field=packed_field.parent_field,
                        is_unpacked_children=True,
                    )
                )
        elif packed_wire_type == ProtoParser.WireTypes.len_delimited:
            while pos < len(wire_data):
                offset, length = ProtoParser._read_base128le(wire_data[pos:])
                pos += offset
                val = wire_data[pos : pos + length]
                if length > len(wire_data[pos:]):
                    raise ValueError("packed length delimited field exceeds data size")
                res.append(
                    ProtoParser.Field(
                        options=options,
                        preferred_decoding=intended_decoding,
                        rules=rules,
                        tag=tag,
                        wire_type=packed_wire_type,
                        wire_value=val,
                        parent_field=packed_field.parent_field,
                        is_unpacked_children=True,
                    )
                )
                pos += length
        elif (
            packed_wire_type == ProtoParser.WireTypes.group_start
            or packed_wire_type == ProtoParser.WireTypes.group_end
        ):
            raise ValueError("group tags can not be encoded packed")
        elif packed_wire_type == ProtoParser.WireTypes.bit_32:
            if len(wire_data) % 4 != 0:
                raise ValueError("can not parse as packed bit32")
            while pos < len(wire_data):
                offset, val = ProtoParser._read_u32(wire_data[pos:])
                pos += offset
                res.append(
                    ProtoParser.Field(
                        options=options,
                        preferred_decoding=intended_decoding,
                        rules=rules,
                        tag=tag,
                        wire_type=packed_wire_type,
                        wire_value=val,
                        parent_field=packed_field.parent_field,
                        is_unpacked_children=True,
                    )
                )
        else:
            # should never happen
            raise ValueError("invalid WireType for protobuf messsage field")

        # mark parent field as packed parent (if we got here, unpacking succeeded)
        packed_field.is_packed_parent = True
        return res

    class Field:
        """
        Represents a single field of a protobuf message and handles the varios encodings.

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
                     is handled inside this class.
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
            wire_type: ProtoParser.WireTypes,
            preferred_decoding: ProtoParser.DecodedTypes,
            tag: int,
            parent_field: ProtoParser.Field | None,
            wire_value: int | bytes,
            options: ProtoParser.ParserOptions,
            rules: list[ProtoParser.ParserRule],
            is_unpacked_children: bool = False,
        ) -> None:
            self.wire_type: ProtoParser.WireTypes = wire_type
            self.preferred_decoding: ProtoParser.DecodedTypes = preferred_decoding
            self.wire_value: int | bytes = wire_value
            self.tag: int = tag
            self.options: ProtoParser.ParserOptions = options
            self.name: str = ""
            self.rules: list[ProtoParser.ParserRule] = rules
            self.parent_field: ProtoParser.Field | None = parent_field
            self.is_unpacked_children: bool = (
                is_unpacked_children  # marks field as being a result of unpacking
            )
            self.is_packed_parent: bool = (
                False  # marks field as being parent of successfully unpacked children
            )
            self.parent_tags: list[int] = []
            if self.parent_field is not None:
                self.parent_tags = self.parent_field.parent_tags[:]
                self.parent_tags.append(self.parent_field.tag)
            self.try_unpack = False

            # rules can overwrite self.try_unpack
            self.apply_rules()
            # do not unpack fields which are the result of unpacking
            if parent_field is not None and self.is_unpacked_children:
                self.try_unpack = False

        # no tests for only_first_hit=False, as not user-changable
        def apply_rules(self, only_first_hit=True):
            tag_str = self._gen_tag_str()
            name = None
            decoding = None
            as_packed = False
            try:
                for rule in self.rules:
                    for fd in rule.field_definitions:
                        match = False
                        if len(fd.tag_prefixes) == 0 and fd.tag == tag_str:
                            match = True
                        else:
                            for rt in fd.tag_prefixes:
                                if rt + fd.tag == tag_str:
                                    match = True
                                    break
                        if match:
                            if only_first_hit:
                                # only first match
                                if fd.name is not None:
                                    self.name = fd.name
                                if fd.intended_decoding is not None:
                                    self.preferred_decoding = fd.intended_decoding
                                self.try_unpack = bool(fd.as_packed)
                                return
                            else:
                                # overwrite matches till last rule was inspected
                                # (f.e. allows to define name in one rule and intended_decoding in another one)
                                name = fd.name if fd.name else name
                                decoding = (
                                    fd.intended_decoding
                                    if fd.intended_decoding
                                    else decoding
                                )
                                if fd.as_packed:
                                    as_packed = True

                if name:
                    self.name = name
                if decoding:
                    self.preferred_decoding = decoding
                self.try_unpack = as_packed
            except Exception as e:
                logging.warning(e)

        def _gen_tag_str(self):
            tags = self.parent_tags[:]
            tags.append(self.tag)
            return ".".join([str(tag) for tag in tags])

        def safe_decode_as(
            self,
            intended_decoding: ProtoParser.DecodedTypes,
            try_as_packed: bool = False,
        ) -> tuple[
            ProtoParser.DecodedTypes,
            bool | float | int | bytes | str | list[ProtoParser.Field],
        ]:
            """
            Tries to decode as intended, applies failover, if not possible

            Returns selected decoding and decoded value
            """
            if self.wire_type == ProtoParser.WireTypes.varint:
                try:
                    return intended_decoding, self.decode_as(
                        intended_decoding, try_as_packed
                    )
                except Exception:
                    if int(self.wire_value).bit_length() > 32:
                        # ignore the fact that varint could exceed 64bit (would violate the specs)
                        return ProtoParser.DecodedTypes.uint64, self.wire_value
                    else:
                        return ProtoParser.DecodedTypes.uint32, self.wire_value
            elif self.wire_type == ProtoParser.WireTypes.bit_64:
                try:
                    return intended_decoding, self.decode_as(
                        intended_decoding, try_as_packed
                    )
                except Exception:
                    return ProtoParser.DecodedTypes.fixed64, self.wire_value
            elif self.wire_type == ProtoParser.WireTypes.bit_32:
                try:
                    return intended_decoding, self.decode_as(
                        intended_decoding, try_as_packed
                    )
                except Exception:
                    return ProtoParser.DecodedTypes.fixed32, self.wire_value
            elif self.wire_type == ProtoParser.WireTypes.len_delimited:
                try:
                    return intended_decoding, self.decode_as(
                        intended_decoding, try_as_packed
                    )
                except Exception:
                    # failover strategy: message --> string (valid UTF-8) --> bytes
                    len_delimited_strategy: list[ProtoParser.DecodedTypes] = [
                        ProtoParser.DecodedTypes.message,
                        ProtoParser.DecodedTypes.string,
                        ProtoParser.DecodedTypes.bytes,  # should always work
                    ]
                    for failover_decoding in len_delimited_strategy:
                        if failover_decoding == intended_decoding and not try_as_packed:
                            # don't try same decoding twice, unless first attempt was packed
                            continue
                        try:
                            return failover_decoding, self.decode_as(
                                failover_decoding, False
                            )
                        except Exception:
                            pass

            # we should never get here (could not be added to tests)
            return ProtoParser.DecodedTypes.unknown, self.wire_value

        def decode_as(
            self, intended_decoding: ProtoParser.DecodedTypes, as_packed: bool = False
        ) -> bool | int | float | bytes | str | list[ProtoParser.Field]:
            if as_packed is True:
                return ProtoParser.read_packed_fields(packed_field=self)

            if self.wire_type == ProtoParser.WireTypes.varint:
                assert isinstance(self.wire_value, int)
                if intended_decoding == ProtoParser.DecodedTypes.bool:
                    # clamp result to 64bit
                    return self.wire_value & 0xFFFFFFFFFFFFFFFF != 0
                elif intended_decoding == ProtoParser.DecodedTypes.int32:
                    if self.wire_value.bit_length() > 32:
                        raise TypeError("wire value too large for int32")
                    return struct.unpack("!i", struct.pack("!I", self.wire_value))[0]
                elif intended_decoding == ProtoParser.DecodedTypes.int64:
                    if self.wire_value.bit_length() > 64:
                        raise TypeError("wire value too large for int64")
                    return struct.unpack("!q", struct.pack("!Q", self.wire_value))[0]
                elif intended_decoding == ProtoParser.DecodedTypes.uint32:
                    if self.wire_value.bit_length() > 32:
                        raise TypeError("wire value too large for uint32")
                    return self.wire_value  # already 'int' which was parsed as unsigned
                elif (
                    intended_decoding == ProtoParser.DecodedTypes.uint64
                    or intended_decoding == ProtoParser.DecodedTypes.enum
                ):
                    if self.wire_value.bit_length() > 64:
                        raise TypeError("wire value too large")
                    return self.wire_value  # already 'int' which was parsed as unsigned
                elif intended_decoding == ProtoParser.DecodedTypes.sint32:
                    if self.wire_value.bit_length() > 32:
                        raise TypeError("wire value too large for sint32")
                    return (self.wire_value >> 1) ^ -(
                        self.wire_value & 1
                    )  # zigzag_decode
                elif intended_decoding == ProtoParser.DecodedTypes.sint64:
                    if self.wire_value.bit_length() > 64:
                        raise TypeError("wire value too large for sint64")
                    # ZigZag decode
                    # Ref: https://gist.github.com/mfuerstenau/ba870a29e16536fdbaba
                    return (self.wire_value >> 1) ^ -(self.wire_value & 1)
                elif (
                    intended_decoding == ProtoParser.DecodedTypes.float
                    or intended_decoding == ProtoParser.DecodedTypes.double
                ):
                    # special case, not complying to protobuf specs
                    return self._wire_value_as_float()
            elif self.wire_type == ProtoParser.WireTypes.bit_64:
                if intended_decoding == ProtoParser.DecodedTypes.fixed64:
                    return self.wire_value
                elif intended_decoding == ProtoParser.DecodedTypes.sfixed64:
                    return struct.unpack("!q", struct.pack("!Q", self.wire_value))[0]
                elif intended_decoding == ProtoParser.DecodedTypes.double:
                    return self._wire_value_as_float()
            elif self.wire_type == ProtoParser.WireTypes.bit_32:
                if intended_decoding == ProtoParser.DecodedTypes.fixed32:
                    return self.wire_value
                elif intended_decoding == ProtoParser.DecodedTypes.sfixed32:
                    return struct.unpack("!i", struct.pack("!I", self.wire_value))[0]
                elif intended_decoding == ProtoParser.DecodedTypes.float:
                    return self._wire_value_as_float()
            elif self.wire_type == ProtoParser.WireTypes.len_delimited:
                assert isinstance(self.wire_value, bytes)
                if intended_decoding == ProtoParser.DecodedTypes.string:
                    # According to specs, a protobuf string HAS TO be UTF-8 parsable
                    # throw exception on invalid UTF-8 chars, but escape linebreaks
                    return self.wire_value_as_utf8(escape_newline=True)
                elif intended_decoding == ProtoParser.DecodedTypes.bytes:
                    # always works, assure to hand back a copy
                    return self.wire_value[:]
                elif intended_decoding == ProtoParser.DecodedTypes.message:
                    return ProtoParser.read_fields(
                        wire_data=self.wire_value,
                        parent_field=self,
                        options=self.options,
                        rules=self.rules,
                    )

            # if here, there is no valid decoding
            raise TypeError("intended decoding mismatches wire type")

        def encode_from(inputval, intended_encoding: ProtoParser.DecodedTypes):
            raise NotImplementedError(
                "Future work, needed to manipulate and re-encode protobuf message, with respect to given wire types"
            )

        def _wire_value_as_float(self) -> float:
            """
            Handles double (64bit) and float (32bit).
            Assumes Network Byte Order (big endian).

            Usable for:

               WireType --> Protobuf Type):
               ----------------------------
               varint        --> double/float (not intended by ProtoBuf, but used in the wild)
               bit_32        --> float
               bit_64        --> double
               len_delimited --> 4 bytes: float / 8 bytes: double / other sizes return NaN
            """
            v = self._value_as_bytes()
            if len(v) == 4:
                return struct.unpack("!f", v)[0]
            elif len(v) == 8:
                return struct.unpack("!d", v)[0]
            # no need to raise an Exception
            raise TypeError("can not be converted to floatingpoint representation")

        def _value_as_bytes(self) -> bytes:
            if isinstance(self.wire_value, bytes):
                return self.wire_value
            elif isinstance(self.wire_value, int):
                if self.wire_value.bit_length() > 64:
                    # source for a python int are wiretypes varint/bit_32/bit64 and should never convert to int values 64bit
                    # currently avoided by kaitai decoder (can not be added to tests)
                    raise ValueError("value exceeds 64bit, violating protobuf specs")
                elif self.wire_value.bit_length() > 32:
                    # packing uses network byte order (to assure consistent results across architectures)
                    return struct.pack("!Q", self.wire_value)
                else:
                    # packing uses network byte order (to assure consistent results across architectures)
                    return struct.pack("!I", self.wire_value)
            else:
                # should never happen, no tests
                raise ValueError("can not be converted to bytes")

        def _wire_type_str(self):
            return str(self.wire_type).split(".")[-1]

        def _decoding_str(self, decoding: ProtoParser.DecodedTypes):
            return str(decoding).split(".")[-1]

        def wire_value_as_utf8(self, escape_newline=True) -> str:
            if isinstance(self.wire_value, bytes):
                res = self.wire_value.decode("utf-8")
                return res.replace("\n", "\\n") if escape_newline else res
            return str(self.wire_value)

        def gen_flat_decoded_field_dicts(self) -> Generator[dict, None, None]:
            """
            Returns a generator which passes the field as a dict.

            In order to return the field value it gets decoded (based on a failover strategy and
            provided ParserRules).
            If the field holds a nested message, the fields contained in the message are appended.
            Ultimately this flattens all fields recursively.
            """
            selected_decoding, decoded_val = self.safe_decode_as(
                self.preferred_decoding, self.try_unpack
            )
            field_desc_dict = {
                "tag": self._gen_tag_str(),
                "wireType": self._wire_type_str(),
                "decoding": self._decoding_str(selected_decoding),
                "name": self.name,
            }
            if isinstance(decoded_val, list):
                if (
                    selected_decoding
                    == ProtoParser.DecodedTypes.message  # field is a message with subfields
                    and not self.is_packed_parent  # field is a message, but replaced by packed fields
                ):
                    # Field is a message, not packed, thus include it as message header
                    field_desc_dict["val"] = ""
                    yield field_desc_dict
                # add sub-fields of messages or packed fields
                for f in decoded_val:
                    yield from f.gen_flat_decoded_field_dicts()
            else:
                field_desc_dict["val"] = decoded_val
                yield field_desc_dict

    def __init__(
        self,
        data: bytes,
        rules: list[ProtoParser.ParserRule] | None = None,
        parser_options: ParserOptions | None = None,
    ) -> None:
        self.data: bytes = data
        if parser_options is None:
            parser_options = ProtoParser.ParserOptions()
        self.options = parser_options
        if rules is None:
            rules = []
        self.rules = rules

        try:
            self.root_fields: list[ProtoParser.Field] = ProtoParser.read_fields(
                wire_data=self.data,
                options=self.options,
                parent_field=None,
                rules=self.rules,
            )
        except Exception as e:
            raise ValueError("not a valid protobuf message") from e

    def gen_flat_decoded_field_dicts(self) -> Generator[dict, None, None]:
        for f in self.root_fields:
            yield from f.gen_flat_decoded_field_dicts()

    def gen_str_rows(self) -> Generator[tuple[str, ...], None, None]:
        for field_dict in self.gen_flat_decoded_field_dicts():
            if (
                self.options.exclude_message_headers
                and field_dict["decoding"] == "message"
            ):
                continue

            if self.options.include_wiretype:
                col1 = "[{}->{}]".format(field_dict["wireType"], field_dict["decoding"])
            else:
                col1 = "[{}]".format(field_dict["decoding"])
            col2 = field_dict["name"]  # empty string if not set (consumes no space)
            col3 = field_dict["tag"]
            col4 = str(field_dict["val"])
            yield col1, col2, col3, col4


# Note: all content view formating functionality is kept out of the ProtoParser class, to
#       allow it to be use independently.
#       This function is generic enough, to consider moving it to mitmproxy.contentviews.base
def format_table(
    table_rows: Iterable[tuple[str, ...]],
    max_col_width=100,
) -> Iterator[base.TViewLine]:
    """
    Helper function to render tables with variable column count (move to contentview base, if needed elsewhere)

    Note: The function has to convert generators to a list, as all rows have to be processed twice (to determine
    the column widths first).
    """
    rows: list[tuple[str, ...]] = []
    col_count = 0
    cols_width: list[int] = []
    for row in table_rows:
        col_count = max(col_count, len(row))
        while len(cols_width) < col_count:
            cols_width.append(0)
        for col_num in range(len(row)):
            cols_width[col_num] = max(len(row[col_num]), cols_width[col_num])

        # store row in list
        rows.append(row)

    for i in range(len(cols_width)):
        cols_width[i] = min(cols_width[i], max_col_width)

    for row in rows:
        line: base.TViewLine = []
        for col_num in range(len(row)):
            col_val = row[col_num].ljust(cols_width[col_num] + 2)
            line.append(("text", col_val))
        yield line


def parse_grpc_messages(
    data, compression_scheme
) -> Generator[tuple[bool, bytes], None, None]:
    """Generator iterates over body data and returns a boolean indicating if the messages
    was compressed, along with the raw message data (decompressed) for each gRPC message
    contained in the body data"""
    while data:
        try:
            msg_is_compressed, length = struct.unpack("!?i", data[:5])
            decoded_message = struct.unpack("!%is" % length, data[5 : 5 + length])[0]
        except Exception as e:
            raise ValueError("invalid gRPC message") from e

        if msg_is_compressed:
            try:
                decoded_message = decode(
                    encoded=decoded_message, encoding=compression_scheme
                )
            except Exception as e:
                raise ValueError("Failed to decompress gRPC message with gzip") from e

        yield msg_is_compressed, decoded_message
        data = data[5 + length :]


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
    return list(generator_func)


def format_pbuf(
    message: bytes,
    parser_options: ProtoParser.ParserOptions,
    rules: list[ProtoParser.ParserRule],
):
    yield from format_table(
        ProtoParser(
            data=message, parser_options=parser_options, rules=rules
        ).gen_str_rows()
    )


def format_grpc(
    data: bytes,
    parser_options: ProtoParser.ParserOptions,
    rules: list[ProtoParser.ParserRule],
    compression_scheme="gzip",
):
    message_count = 0
    for compressed, pb_message in parse_grpc_messages(
        data=data, compression_scheme=compression_scheme
    ):
        headline = (
            "gRPC message "
            + str(message_count)
            + " (compressed "
            + str(compression_scheme if compressed else compressed)
            + ")"
        )

        yield [("text", headline)]
        yield from format_pbuf(
            message=pb_message, parser_options=parser_options, rules=rules
        )


@dataclass
class ViewConfig:
    parser_options: ProtoParser.ParserOptions = field(
        default_factory=ProtoParser.ParserOptions
    )
    parser_rules: list[ProtoParser.ParserRule] = field(default_factory=list)


class ViewGrpcProtobuf(base.View):
    """Human friendly view of protocol buffers"""

    name = "gRPC/Protocol Buffer"
    __content_types_pb = [
        "application/x-protobuf",
        "application/x-protobuffer",
        "application/grpc-proto",
    ]
    __content_types_grpc = [
        "application/grpc",
        # seems specific to chromium infra tooling
        # https://chromium.googlesource.com/infra/luci/luci-go/+/refs/heads/main/grpc/prpc/
        "application/prpc",
    ]

    # first value serves as default algorithm for compressed messages, if 'grpc-encoding' header is missing
    __valid_grpc_encodings = [
        "gzip",
        "identity",
        "deflate",
        "zstd",
    ]

    # allows to take external ParserOptions object. goes with defaults otherwise
    def __init__(self, config: ViewConfig | None = None) -> None:
        super().__init__()
        if config is None:
            config = ViewConfig()
        self.config = config

    def _matching_rules(
        self,
        rules: list[ProtoParser.ParserRule],
        message: http.Message | None,
        flow: flow.Flow | None,
    ) -> list[ProtoParser.ParserRule]:
        """
        Checks which of the give rules applies and returns a List only containing those rules

        Each rule defines a flow filter in rule.filter which is usually matched against a flow.
        When it comes to protobuf parsing, in most cases request messages differ from response messages.
        Thus, it has to be possible to apply a rule to a http.Request or a http.Response, only.

        As the name flowfilter suggests, filters are working on a flow-level, not on message-level.
        This means:

        - the filter expression '~q' matches all flows with a request, but no response
        - the filter expression '~s' matches all flows with a response

        In result, for complete flows (with a gRPC message in the request and the response), ParserRules would
        either be applied to request and response at the same time ('~s') or neither would match request, nor
        response (~q).

        To distinguish between rules which should be applied to response messages, request messages or both
        (while being applied to the whole flow), different classes with same behavior are used to wrap rules:

            - ParserRule: applies to requests and responses
            - ParserRuleRequest: applies to requests only
            - ParserRuleResponse: applies to responses only
        """
        res: list[ProtoParser.ParserRule] = []
        if not flow:
            return res
        is_request = isinstance(message, http.Request)
        for rule in rules:
            # message based rule matching
            if is_request and isinstance(rule, ProtoParser.ParserRuleResponse):
                continue
            elif not is_request and isinstance(rule, ProtoParser.ParserRuleRequest):
                continue
            # flow based rule matching
            if flowfilter.match(rule.filter, flow=flow):
                res.append(rule)
        return res

    def __call__(
        self,
        data: bytes,
        *,
        content_type: str | None = None,
        flow: flow.Flow | None = None,
        http_message: http.Message | None = None,
        **unknown_metadata,
    ) -> contentviews.TViewResult:
        applicabble_rules = self._matching_rules(
            rules=self.config.parser_rules, flow=flow, message=http_message
        )
        if content_type in self.__content_types_grpc:
            # If gRPC messages are flagged to be compressed, the compression algorithm is expressed in the
            # 'grpc-encoding' header.
            #
            # The following code tries to determine the compression algorithm base on this header.
            # If the header is not present or contains an unsupported compression, the logic falls back to
            # 'gzip'.
            #
            # If a compressed gRPC message is found in the body data (compressed flag set), the information
            # on the compression scheme is needed (even if not set by a header), in order to process the message.
            # Thus we assure there is always an encoding selected. An encoding of 'Identity' would not make
            # sense, if a message is flagged as being compressed, that's why a default is chosen.
            try:
                assert http_message is not None
                h = http_message.headers["grpc-encoding"]
                grpc_encoding = (
                    h
                    if h in self.__valid_grpc_encodings
                    else self.__valid_grpc_encodings[0]
                )
            except Exception:
                grpc_encoding = self.__valid_grpc_encodings[0]

            text_iter = format_grpc(
                data=data,
                parser_options=self.config.parser_options,
                compression_scheme=grpc_encoding,
                rules=applicabble_rules,
            )
            title = "gRPC"
        else:
            text_iter = format_pbuf(
                message=data,
                parser_options=self.config.parser_options,
                rules=applicabble_rules,
            )
            title = "Protobuf (flattened)"

        # hacky bugfix, see description above generator functions format_pbuf/format_grpc
        try:
            text_iter = hack_generator_to_list(text_iter)
        except Exception as e:
            # hook to log exception tracebacks on iterators

            # import traceback
            # logging.warning("gRPC contentview: {}".format(traceback.format_exc()))
            raise e

        return title, text_iter

    def render_priority(
        self,
        data: bytes,
        *,
        content_type: str | None = None,
        flow: flow.Flow | None = None,
        http_message: http.Message | None = None,
        **unknown_metadata,
    ) -> float:
        if bool(data) and content_type in self.__content_types_grpc:
            return 1
        if bool(data) and content_type in self.__content_types_pb:
            # replace existing protobuf renderer preference (adjust by option)
            return 1.5
        else:
            return 0
