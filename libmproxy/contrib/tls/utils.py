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
