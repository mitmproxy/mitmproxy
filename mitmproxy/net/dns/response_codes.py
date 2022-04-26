NOERROR = 0
FORMERR = 1
SERVFAIL = 2
NXDOMAIN = 3
NOTIMP = 4
REFUSED = 5
YXDOMAIN = 6
YXRRSET = 7
NXRRSET = 8
NOTAUTH = 9
NOTZONE = 10
DSOTYPENI = 11

_CODES = {
    NOERROR: 200,
    FORMERR: 400,
    SERVFAIL: 500,
    NXDOMAIN: 404,
    NOTIMP: 501,
    REFUSED: 403,
    YXDOMAIN: 409,
    YXRRSET: 409,
    NXRRSET: 410,
    NOTAUTH: 401,
    NOTZONE: 404,
    DSOTYPENI: 501,
}

_STRINGS = {
    NOERROR: "NOERROR",
    FORMERR: "FORMERR",
    SERVFAIL: "SERVFAIL",
    NXDOMAIN: "NXDOMAIN",
    NOTIMP: "NOTIMP",
    REFUSED: "REFUSED",
    YXDOMAIN: "YXDOMAIN",
    YXRRSET: "YXRRSET",
    NXRRSET: "NXRRSET",
    NOTAUTH: "NOTAUTH",
    NOTZONE: "NOTZONE",
    DSOTYPENI: "DSOTYPENI",
}


def http_equiv_status_code(response_code: int) -> int:
    return _CODES.get(response_code, 500)


def to_str(response_code: int) -> str:
    return _STRINGS.get(response_code, f"RCODE({response_code})")
