A = 1
NS = 2
MD = 3
MF = 4
CNAME = 5
SOA = 6
MB = 7
MG = 8
MR = 9
NULL = 10
WKS = 11
PTR = 12
HINFO = 13
MINFO = 14
MX = 15
TXT = 16
RP = 17
AFSDB = 18
X25 = 19
ISDN = 20
RT = 21
NSAP = 22
NSAP_PTR = 23
SIG = 24
KEY = 25
PX = 26
GPOS = 27
AAAA = 28
LOC = 29
NXT = 30
EID = 31
NIMLOC = 32
SRV = 33
ATMA = 34
NAPTR = 35
KX = 36
CERT = 37
A6 = 38
DNAME = 39
SINK = 40
OPT = 41
APL = 42
DS = 43
SSHFP = 44
IPSECKEY = 45
RRSIG = 46
NSEC = 47
DNSKEY = 48
DHCID = 49
NSEC3 = 50
NSEC3PARAM = 51
TLSA = 52
SMIMEA = 53
HIP = 55
NINFO = 56
RKEY = 57
TALINK = 58
CDS = 59
CDNSKEY = 60
OPENPGPKEY = 61
CSYNC = 62
ZONEMD = 63
SVCB = 64
HTTPS = 65
SPF = 99
UINFO = 100
UID = 101
GID = 102
UNSPEC = 103
NID = 104
L32 = 105
L64 = 106
LP = 107
EUI48 = 108
EUI64 = 109
TKEY = 249
TSIG = 250
IXFR = 251
AXFR = 252
MAILB = 253
MAILA = 254
ANY = 255
URI = 256
CAA = 257
AVC = 258
DOA = 259
AMTRELAY = 260
TA = 32768
DLV = 32769

_STRINGS = {
    A: "A",
    NS: "NS",
    MD: "MD",
    MF: "MF",
    CNAME: "CNAME",
    SOA: "SOA",
    MB: "MB",
    MG: "MG",
    MR: "MR",
    NULL: "NULL",
    WKS: "WKS",
    PTR: "PTR",
    HINFO: "HINFO",
    MINFO: "MINFO",
    MX: "MX",
    TXT: "TXT",
    RP: "RP",
    AFSDB: "AFSDB",
    X25: "X25",
    ISDN: "ISDN",
    RT: "RT",
    NSAP: "NSAP",
    NSAP_PTR: "NSAP_PTR",
    SIG: "SIG",
    KEY: "KEY",
    PX: "PX",
    GPOS: "GPOS",
    AAAA: "AAAA",
    LOC: "LOC",
    NXT: "NXT",
    EID: "EID",
    NIMLOC: "NIMLOC",
    SRV: "SRV",
    ATMA: "ATMA",
    NAPTR: "NAPTR",
    KX: "KX",
    CERT: "CERT",
    A6: "A6",
    DNAME: "DNAME",
    SINK: "SINK",
    OPT: "OPT",
    APL: "APL",
    DS: "DS",
    SSHFP: "SSHFP",
    IPSECKEY: "IPSECKEY",
    RRSIG: "RRSIG",
    NSEC: "NSEC",
    DNSKEY: "DNSKEY",
    DHCID: "DHCID",
    NSEC3: "NSEC3",
    NSEC3PARAM: "NSEC3PARAM",
    TLSA: "TLSA",
    SMIMEA: "SMIMEA",
    HIP: "HIP",
    NINFO: "NINFO",
    RKEY: "RKEY",
    TALINK: "TALINK",
    CDS: "CDS",
    CDNSKEY: "CDNSKEY",
    OPENPGPKEY: "OPENPGPKEY",
    CSYNC: "CSYNC",
    ZONEMD: "ZONEMD",
    SVCB: "SVCB",
    HTTPS: "HTTPS",
    SPF: "SPF",
    UINFO: "UINFO",
    UID: "UID",
    GID: "GID",
    UNSPEC: "UNSPEC",
    NID: "NID",
    L32: "L32",
    L64: "L64",
    LP: "LP",
    EUI48: "EUI48",
    EUI64: "EUI64",
    TKEY: "TKEY",
    TSIG: "TSIG",
    IXFR: "IXFR",
    AXFR: "AXFR",
    MAILB: "MAILB",
    MAILA: "MAILA",
    ANY: "ANY",
    URI: "URI",
    CAA: "CAA",
    AVC: "AVC",
    DOA: "DOA",
    AMTRELAY: "AMTRELAY",
    TA: "TA",
    DLV: "DLV",
}
_INTS = {v: k for k, v in _STRINGS.items()}


def to_str(type_: int) -> str:
    return _STRINGS.get(type_, f"TYPE({type_})")


def from_str(type_: str) -> int:
    try:
        return _INTS[type_]
    except KeyError:
        return int(type_.removeprefix("TYPE(").removesuffix(")"))
