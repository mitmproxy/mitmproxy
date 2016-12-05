# This file originally comes from https://github.com/pyca/tls/blob/master/tls/_constructs.py.
# Modified by the mitmproxy team.

# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.


from construct import (
    Array,
    Bytes,
    Struct,
    VarInt,
    Int8ub,
    Int16ub,
    Int24ub,
    Int32ub,
    PascalString,
    Embedded,
    Prefixed,
    Range,
    GreedyRange,
    Switch,
    Optional,
)

ProtocolVersion = "version" / Struct(
    "major" / Int8ub,
    "minor" / Int8ub,
)

TLSPlaintext = "TLSPlaintext" / Struct(
    "type" / Int8ub,
    ProtocolVersion,
    "length" / Int16ub,  # TODO: Reject packets with length > 2 ** 14
    "fragment" / Bytes(lambda ctx: ctx.length),
)

TLSCompressed = "TLSCompressed" / Struct(
    "type" / Int8ub,
    ProtocolVersion,
    "length" / Int16ub,  # TODO: Reject packets with length > 2 ** 14 + 1024
    "fragment" / Bytes(lambda ctx: ctx.length),
)

TLSCiphertext = "TLSCiphertext" / Struct(
    "type" / Int8ub,
    ProtocolVersion,
    "length" / Int16ub,  # TODO: Reject packets with length > 2 ** 14 + 2048
    "fragment" / Bytes(lambda ctx: ctx.length),
)

Random = "random" / Struct(
    "gmt_unix_time" / Int32ub,
    "random_bytes" / Bytes(28),
)

SessionID = "session_id" / Struct(
    "length" / Int8ub,
    "session_id" / Bytes(lambda ctx: ctx.length),
)

CipherSuites = "cipher_suites" / Struct(
    "length" / Int16ub,  # TODO: Reject packets of length 0
    Array(lambda ctx: ctx.length // 2, "cipher_suites" / Int16ub),
)

CompressionMethods = "compression_methods" / Struct(
    "length" / Int8ub,  # TODO: Reject packets of length 0
    Array(lambda ctx: ctx.length, "compression_methods" / Int8ub),
)

ServerName = Struct(
    "type" / Int8ub,
    "name" / PascalString("length" / Int16ub),
)

SNIExtension = Prefixed(
    Int16ub,
    Struct(
        Int16ub,
        "server_names" / GreedyRange(
            "server_name" / Struct(
                "name_type" / Int8ub,
                "host_name" / PascalString("length" / Int16ub),
            )
        )
    )
)

ALPNExtension = Prefixed(
    Int16ub,
    Struct(
        Int16ub,
        "alpn_protocols" / GreedyRange(
            "name" / PascalString(Int8ub),
        ),
    )
)

UnknownExtension = Struct(
    "bytes" / PascalString("length" / Int16ub)
)

Extension = "Extension" / Struct(
    "type" / Int16ub,
    Embedded(
        Switch(
            lambda ctx: ctx.type,
            {
                0x00: SNIExtension,
                0x10: ALPNExtension,
            },
            default=UnknownExtension
        )
    )
)

extensions = "extensions" / Optional(
    Struct(
        Int16ub,
        "extensions" / GreedyRange(Extension)
    )
)

ClientHello = "ClientHello" / Struct(
    ProtocolVersion,
    Random,
    SessionID,
    CipherSuites,
    CompressionMethods,
    extensions,
)

ServerHello = "ServerHello" / Struct(
    ProtocolVersion,
    Random,
    SessionID,
    "cipher_suite" / Bytes(2),
    "compression_method" / Int8ub,
    extensions,
)

ClientCertificateType = "certificate_types" / Struct(
    "length" / Int8ub,  # TODO: Reject packets of length 0
    Array(lambda ctx: ctx.length, "certificate_types" / Int8ub),
)

SignatureAndHashAlgorithm = "algorithms" / Struct(
    "hash" / Int8ub,
    "signature" / Int8ub,
)

SupportedSignatureAlgorithms = "supported_signature_algorithms" / Struct(
    "supported_signature_algorithms_length" / Int16ub,
    # TODO: Reject packets of length 0
    Array(
        lambda ctx: ctx.supported_signature_algorithms_length / 2,
        SignatureAndHashAlgorithm,
    ),
)

DistinguishedName = "certificate_authorities" / Struct(
    "length" / Int16ub,
    "certificate_authorities" / Bytes(lambda ctx: ctx.length),
)

CertificateRequest = "CertificateRequest" / Struct(
    ClientCertificateType,
    SupportedSignatureAlgorithms,
    DistinguishedName,
)

ServerDHParams = "ServerDHParams" / Struct(
    "dh_p_length" / Int16ub,
    "dh_p" / Bytes(lambda ctx: ctx.dh_p_length),
    "dh_g_length" / Int16ub,
    "dh_g" / Bytes(lambda ctx: ctx.dh_g_length),
    "dh_Ys_length" / Int16ub,
    "dh_Ys" / Bytes(lambda ctx: ctx.dh_Ys_length),
)

PreMasterSecret = "pre_master_secret" / Struct(
    ProtocolVersion,
    "random_bytes" / Bytes(46),
)

ASN1Cert = "ASN1Cert" / Struct(
    "length" / Int32ub,  # TODO: Reject packets with length not in 1..2^24-1
    "asn1_cert" / Bytes(lambda ctx: ctx.length),
)

Certificate = "Certificate" / Struct(
    # TODO: Reject packets with length > 2 ** 24 - 1
    "certificates_length" / Int32ub,
    "certificates_bytes" / Bytes(lambda ctx: ctx.certificates_length),
)

Handshake = "Handshake" / Struct(
    "msg_type" / Int8ub,
    "length" / Int24ub,
    "body" / Bytes(lambda ctx: ctx.length),
)

Alert = "Alert" / Struct(
    "level" / Int8ub,
    "description" / Int8ub,
)
