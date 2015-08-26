# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import absolute_import, division, print_function

from enum import Enum

from characteristic import attributes

from construct import Container

from six import BytesIO

from . import _constructs

from .hello_message import (
    ClientHello, ProtocolVersion, ServerHello
)


class ClientCertificateType(Enum):
    RSA_SIGN = 1
    DSS_SIGN = 2
    RSA_FIXED_DH = 3
    DSS_FIXED_DH = 4
    RSA_EPHEMERAL_DH_RESERVED = 5
    DSS_EPHEMERAL_DH_RESERVED = 6
    FORTEZZA_DMS_RESERVED = 20


class HashAlgorithm(Enum):
    NONE = 0
    MD5 = 1
    SHA1 = 2
    SHA224 = 3
    SHA256 = 4
    SHA384 = 5
    SHA512 = 6


class SignatureAlgorithm(Enum):
    ANONYMOUS = 0
    RSA = 1
    DSA = 2
    ECDSA = 3


class HandshakeType(Enum):
    HELLO_REQUEST = 0
    CLIENT_HELLO = 1
    SERVER_HELLO = 2
    CERTIFICATE = 11
    SERVER_KEY_EXCHANGE = 12
    CERTIFICATE_REQUEST = 13
    SERVER_HELLO_DONE = 14
    CERTIFICATE_VERIFY = 15
    CLIENT_KEY_EXCHANGE = 16
    FINISHED = 20


class HelloRequest(object):
    """
    An object representing a HelloRequest struct.
    """
    def as_bytes(self):
        return b''


class ServerHelloDone(object):
    """
    An object representing a ServerHelloDone struct.
    """
    def as_bytes(self):
        return b''


@attributes(['certificate_types', 'supported_signature_algorithms',
             'certificate_authorities'])
class CertificateRequest(object):
    """
    An object representing a CertificateRequest struct.
    """
    def as_bytes(self):
        return _constructs.CertificateRequest.build(Container(
            certificate_types=Container(
                length=len(self.certificate_types),
                certificate_types=[cert_type.value
                                   for cert_type in self.certificate_types]
            ),
            supported_signature_algorithms=Container(
                supported_signature_algorithms_length=2 * len(
                    self.supported_signature_algorithms
                ),
                algorithms=[Container(
                    hash=algorithm.hash.value,
                    signature=algorithm.signature.value,
                )
                    for algorithm in self.supported_signature_algorithms
                ]
            ),
            certificate_authorities=Container(
                length=len(self.certificate_authorities),
                certificate_authorities=self.certificate_authorities
            )
        ))

    @classmethod
    def from_bytes(cls, bytes):
        """
        Parse a ``CertificateRequest`` struct.

        :param bytes: the bytes representing the input.
        :return: CertificateRequest object.
        """
        construct = _constructs.CertificateRequest.parse(bytes)
        return cls(
            certificate_types=[
                ClientCertificateType(cert_type)
                for cert_type in construct.certificate_types.certificate_types
            ],
            supported_signature_algorithms=[
                SignatureAndHashAlgorithm(
                    hash=HashAlgorithm(algorithm.hash),
                    signature=SignatureAlgorithm(algorithm.signature),
                )
                for algorithm in (
                    construct.supported_signature_algorithms.algorithms
                )
            ],
            certificate_authorities=(
                construct.certificate_authorities.certificate_authorities
            )
        )


@attributes(['hash', 'signature'])
class SignatureAndHashAlgorithm(object):
    """
    An object representing a SignatureAndHashAlgorithm struct.
    """


@attributes(['dh_p', 'dh_g', 'dh_Ys'])
class ServerDHParams(object):
    """
    An object representing a ServerDHParams struct.
    """
    @classmethod
    def from_bytes(cls, bytes):
        """
        Parse a ``ServerDHParams`` struct.

        :param bytes: the bytes representing the input.
        :return: ServerDHParams object.
        """
        construct = _constructs.ServerDHParams.parse(bytes)
        return cls(
            dh_p=construct.dh_p,
            dh_g=construct.dh_g,
            dh_Ys=construct.dh_Ys
        )


@attributes(['client_version', 'random'])
class PreMasterSecret(object):
    """
    An object representing a PreMasterSecret struct.
    """
    @classmethod
    def from_bytes(cls, bytes):
        """
        Parse a ``PreMasterSecret`` struct.

        :param bytes: the bytes representing the input.
        :return: CertificateRequest object.
        """
        construct = _constructs.PreMasterSecret.parse(bytes)
        return cls(
            client_version=ProtocolVersion(
                major=construct.version.major,
                minor=construct.version.minor,
            ),
            random=construct.random_bytes,
        )


@attributes(['asn1_cert'])
class ASN1Cert(object):
    """
    An object representing ASN.1 Certificate
    """
    def as_bytes(self):
        return _constructs.ASN1Cert.build(Container(
            length=len(self.asn1_cert),
            asn1_cert=self.asn1_cert
        ))


@attributes(['certificate_list'])
class Certificate(object):
    """
    An object representing a Certificate struct.
    """
    def as_bytes(self):
        return _constructs.Certificate.build(Container(
            certificates_length=sum([4 + len(asn1cert.asn1_cert)
                                     for asn1cert in self.certificate_list]),
            certificates_bytes=b''.join(
                [asn1cert.as_bytes() for asn1cert in self.certificate_list]
            )

        ))

    @classmethod
    def from_bytes(cls, bytes):
        """
        Parse a ``Certificate`` struct.

        :param bytes: the bytes representing the input.
        :return: Certificate object.
        """
        construct = _constructs.Certificate.parse(bytes)
        # XXX: Find a better way to parse an array of variable-length objects
        certificates = []
        certificates_io = BytesIO(construct.certificates_bytes)

        while certificates_io.tell() < construct.certificates_length:
            certificate_construct = _constructs.ASN1Cert.parse_stream(
                certificates_io
            )
            certificates.append(
                ASN1Cert(asn1_cert=certificate_construct.asn1_cert)
            )
        return cls(
            certificate_list=certificates
        )


@attributes(['verify_data'])
class Finished(object):
    def as_bytes(self):
        return self.verify_data


@attributes(['msg_type', 'length', 'body'])
class Handshake(object):
    """
    An object representing a Handshake struct.
    """
    def as_bytes(self):
        if self.msg_type in [
            HandshakeType.SERVER_HELLO, HandshakeType.CLIENT_HELLO,
            HandshakeType.CERTIFICATE, HandshakeType.CERTIFICATE_REQUEST,
            HandshakeType.HELLO_REQUEST, HandshakeType.SERVER_HELLO_DONE,
            HandshakeType.FINISHED
        ]:
            _body_as_bytes = self.body.as_bytes()
        else:
            _body_as_bytes = b''
        return _constructs.Handshake.build(
            Container(
                msg_type=self.msg_type.value,
                length=self.length,
                body=_body_as_bytes
            )
        )

    @classmethod
    def from_bytes(cls, bytes):
        """
        Parse a ``Handshake`` struct.

        :param bytes: the bytes representing the input.
        :return: Handshake object.
        """
        construct = _constructs.Handshake.parse(bytes)
        return cls(
            msg_type=HandshakeType(construct.msg_type),
            length=construct.length,
            body=cls._get_handshake_message(
                HandshakeType(construct.msg_type), construct.body
            ),
        )

    @staticmethod
    def _get_handshake_message(msg_type, body):
        _handshake_message_parser = {
            HandshakeType.CLIENT_HELLO: ClientHello.from_bytes,
            HandshakeType.SERVER_HELLO: ServerHello.from_bytes,
            HandshakeType.CERTIFICATE: Certificate.from_bytes,
            #    12: parse_server_key_exchange,
            HandshakeType.CERTIFICATE_REQUEST: CertificateRequest.from_bytes,
            #    15: parse_certificate_verify,
            #    16: parse_client_key_exchange,
        }

        try:
            if msg_type == HandshakeType.HELLO_REQUEST:
                return HelloRequest()
            elif msg_type == HandshakeType.SERVER_HELLO_DONE:
                return ServerHelloDone()
            elif msg_type == HandshakeType.FINISHED:
                return Finished(verify_data=body)
            elif msg_type in [HandshakeType.SERVER_KEY_EXCHANGE,
                              HandshakeType.CERTIFICATE_VERIFY,
                              HandshakeType.CLIENT_KEY_EXCHANGE,
                              ]:
                raise NotImplementedError
            else:
                return _handshake_message_parser[msg_type](body)
        except NotImplementedError:
            return None     # TODO
