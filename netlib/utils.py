import re


def setbit(byte, offset, value):
    """
        Set a bit in a byte to 1 if value is truthy, 0 if not.
    """
    if value:
        return byte | (1 << offset)
    else:
        return byte & ~(1 << offset)


def getbit(byte, offset):
    mask = 1 << offset
    return bool(byte & mask)


_label_valid = re.compile(b"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)


def is_valid_host(host: bytes) -> bool:
    """
        Checks if a hostname is valid.
    """
    try:
        host.decode("idna")
    except ValueError:
        return False
    if len(host) > 255:
        return False
    if host and host[-1:] == b".":
        host = host[:-1]
    return all(_label_valid.match(x) for x in host.split(b"."))


def is_valid_port(port):
    return 0 <= port <= 65535
