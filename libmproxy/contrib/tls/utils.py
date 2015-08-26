# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import absolute_import, division, print_function

import construct

import six


class _UBInt24(construct.Adapter):
    def _encode(self, obj, context):
        return (
            six.int2byte((obj & 0xFF0000) >> 16) +
            six.int2byte((obj & 0x00FF00) >> 8) +
            six.int2byte(obj & 0x0000FF)
        )

    def _decode(self, obj, context):
        obj = bytearray(obj)
        return (obj[0] << 16 | obj[1] << 8 | obj[2])


def UBInt24(name):  # noqa
    return _UBInt24(construct.Bytes(name, 3))


def LengthPrefixedArray(subcon, length_field=construct.UBInt8("length")):
    """
    An array prefixed by a byte length field.

    In contrast to construct.macros.PrefixedArray,
    the length field signifies the number of bytes, not the number of elements.
    """
    subcon_with_pos = construct.Struct(
        subcon.name,
        construct.Embed(subcon),
        construct.Anchor("__current_pos")
    )

    return construct.Embed(
        construct.Struct(
            "",
            length_field,
            construct.Anchor("__start_pos"),
            construct.RepeatUntil(
                lambda obj, ctx: obj.__current_pos == ctx.__start_pos + getattr(ctx, length_field.name),
                subcon_with_pos
            ),
        )
    )