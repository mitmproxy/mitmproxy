# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import absolute_import, division, print_function

from construct import (Array, Bytes, Struct, UBInt16, UBInt32, UBInt8, PascalString, Embed, TunnelAdapter, GreedyRange,
                       Switch, OptionalGreedyRange, Optional)

from .utils import UBInt24

ProtocolVersion = Struct(
    "version",
    UBInt8("major"),
    UBInt8("minor"),
)

TLSPlaintext = Struct(
    "TLSPlaintext",
    UBInt8("type"),
    ProtocolVersion,
    UBInt16("length"),  # TODO: Reject packets with length > 2 ** 14
    Bytes("fragment", lambda ctx: ctx.length),
)

TLSCompressed = Struct(
    "TLSCompressed",
    UBInt8("type"),
    ProtocolVersion,
    UBInt16("length"),  # TODO: Reject packets with length > 2 ** 14 + 1024
    Bytes("fragment", lambda ctx: ctx.length),
)

TLSCiphertext = Struct(
    "TLSCiphertext",
    UBInt8("type"),
    ProtocolVersion,
    UBInt16("length"),  # TODO: Reject packets with length > 2 ** 14 + 2048
    Bytes("fragment", lambda ctx: ctx.length),
)

Random = Struct(
    "random",
    UBInt32("gmt_unix_time"),
    Bytes("random_bytes", 28),
)

SessionID = Struct(
    "session_id",
    UBInt8("length"),
    Bytes("session_id", lambda ctx: ctx.length),
)

CipherSuites = Struct(
    "cipher_suites",
    UBInt16("length"),  # TODO: Reject packets of length 0
    Array(lambda ctx: ctx.length // 2, UBInt16("cipher_suites")),
)

CompressionMethods = Struct(
    "compression_methods",
    UBInt8("length"),  # TODO: Reject packets of length 0
    Array(lambda ctx: ctx.length, UBInt8("compression_methods")),
)

ServerName = Struct(
    "",
    UBInt8("type"),
    PascalString("name", length_field=UBInt16("length")),
)

SNIExtension = Struct(
    "",
    TunnelAdapter(
        PascalString("server_names", length_field=UBInt16("length")),
        TunnelAdapter(
            PascalString("", length_field=UBInt16("length")),
            GreedyRange(ServerName)
        ),
    ),
)

ALPNExtension = Struct(
    "",
    TunnelAdapter(
        PascalString("alpn_protocols", length_field=UBInt16("length")),
        TunnelAdapter(
            PascalString("", length_field=UBInt16("length")),
            GreedyRange(PascalString("name"))
        ),
    ),
)

UnknownExtension = Struct(
    "",
    PascalString("bytes", length_field=UBInt16("extensions_length"))
)

Extension = Struct(
    "Extension",
    UBInt16("type"),
    Embed(
        Switch(
            "", lambda ctx: ctx.type,
            {
                0x00: SNIExtension,
                0x10: ALPNExtension
            },
            default=UnknownExtension
        )
    )
)

extensions = TunnelAdapter(
    Optional(PascalString("extensions", length_field=UBInt16("extensions_length"))),
    OptionalGreedyRange(Extension)
)

ClientHello = Struct(
    "ClientHello",
    ProtocolVersion,
    Random,
    SessionID,
    CipherSuites,
    CompressionMethods,
    extensions,
)

ServerHello = Struct(
    "ServerHello",
    ProtocolVersion,
    Random,
    SessionID,
    Bytes("cipher_suite", 2),
    UBInt8("compression_method"),
    extensions,
)

ClientCertificateType = Struct(
    "certificate_types",
    UBInt8("length"),  # TODO: Reject packets of length 0
    Array(lambda ctx: ctx.length, UBInt8("certificate_types")),
)

SignatureAndHashAlgorithm = Struct(
    "algorithms",
    UBInt8("hash"),
    UBInt8("signature"),
)

SupportedSignatureAlgorithms = Struct(
    "supported_signature_algorithms",
    UBInt16("supported_signature_algorithms_length"),
    # TODO: Reject packets of length 0
    Array(
        lambda ctx: ctx.supported_signature_algorithms_length / 2,
        SignatureAndHashAlgorithm,
    ),
)

DistinguishedName = Struct(
    "certificate_authorities",
    UBInt16("length"),
    Bytes("certificate_authorities", lambda ctx: ctx.length),
)

CertificateRequest = Struct(
    "CertificateRequest",
    ClientCertificateType,
    SupportedSignatureAlgorithms,
    DistinguishedName,
)

ServerDHParams = Struct(
    "ServerDHParams",
    UBInt16("dh_p_length"),
    Bytes("dh_p", lambda ctx: ctx.dh_p_length),
    UBInt16("dh_g_length"),
    Bytes("dh_g", lambda ctx: ctx.dh_g_length),
    UBInt16("dh_Ys_length"),
    Bytes("dh_Ys", lambda ctx: ctx.dh_Ys_length),
)

PreMasterSecret = Struct(
    "pre_master_secret",
    ProtocolVersion,
    Bytes("random_bytes", 46),
)

ASN1Cert = Struct(
    "ASN1Cert",
    UBInt32("length"),  # TODO: Reject packets with length not in 1..2^24-1
    Bytes("asn1_cert", lambda ctx: ctx.length),
)

Certificate = Struct(
    "Certificate",  # TODO: Reject packets with length > 2 ** 24 - 1
    UBInt32("certificates_length"),
    Bytes("certificates_bytes", lambda ctx: ctx.certificates_length),
)

Handshake = Struct(
    "Handshake",
    UBInt8("msg_type"),
    UBInt24("length"),
    Bytes("body", lambda ctx: ctx.length),
)

Alert = Struct(
    "Alert",
    UBInt8("level"),
    UBInt8("description"),
)
