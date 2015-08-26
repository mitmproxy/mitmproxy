# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import absolute_import, division, print_function

from enum import Enum

from characteristic import attributes

from construct import Container

from . import _constructs


@attributes(['major', 'minor'])
class ProtocolVersion(object):
    """
    An object representing a ProtocolVersion struct.
    """


@attributes(['type', 'version', 'fragment'])
class TLSPlaintext(object):
    """
    An object representing a TLSPlaintext struct.
    """
    def as_bytes(self):
        return _constructs.TLSPlaintext.build(
            Container(
                type=self.type.value,
                version=Container(major=self.version.major,
                                  minor=self.version.minor),
                length=len(self.fragment),
                fragment=self.fragment
            )
        )

    @classmethod
    def from_bytes(cls, bytes):
        """
        Parse a ``TLSPlaintext`` struct.

        :param bytes: the bytes representing the input.
        :return: TLSPlaintext object.
        """
        construct = _constructs.TLSPlaintext.parse(bytes)
        return cls(
            type=ContentType(construct.type),
            version=ProtocolVersion(
                major=construct.version.major,
                minor=construct.version.minor
            ),
            fragment=construct.fragment
        )


@attributes(['type', 'version', 'fragment'])
class TLSCompressed(object):
    """
    An object representing a TLSCompressed struct.
    """
    @classmethod
    def from_bytes(cls, bytes):
        """
        Parse a ``TLSCompressed`` struct.

        :param bytes: the bytes representing the input.
        :return: TLSCompressed object.
        """
        construct = _constructs.TLSCompressed.parse(bytes)
        return cls(
            type=ContentType(construct.type),
            version=ProtocolVersion(
                major=construct.version.major,
                minor=construct.version.minor
            ),
            fragment=construct.fragment
        )


@attributes(['type', 'version', 'fragment'])
class TLSCiphertext(object):
    """
    An object representing a TLSCiphertext struct.
    """
    @classmethod
    def from_bytes(cls, bytes):
        """
        Parse a ``TLSCiphertext`` struct.

        :param bytes: the bytes representing the input.
        :return: TLSCiphertext object.
        """
        construct = _constructs.TLSCiphertext.parse(bytes)
        return cls(
            type=ContentType(construct.type),
            version=ProtocolVersion(
                major=construct.version.major,
                minor=construct.version.minor
            ),
            fragment=construct.fragment
        )


class ContentType(Enum):
    CHANGE_CIPHER_SPEC = 20
    ALERT = 21
    HANDSHAKE = 22
    APPLICATION_DATA = 23
