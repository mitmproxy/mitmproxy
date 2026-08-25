import datetime
import functools
import ipaddress
import time

SIZE_UNITS = {
    "b": 1024**0,
    "k": 1024**1,
    "m": 1024**2,
    "g": 1024**3,
    "t": 1024**4,
}


def pretty_size(size: int) -> str:
    """Convert a number of bytes into a human-readable string.

    len(return value) <= 5 always holds true.
    """
    s: float = size  # type cast for mypy
    if s < 1024:
        return f"{s}b"
    for suffix in ["k", "m", "g", "t"]:
        s /= 1024
        if s < 99.95:
            return f"{s:.1f}{suffix}"
        if s < 1024 or suffix == "t":
            return f"{s:.0f}{suffix}"
    raise AssertionError


@functools.lru_cache
def parse_size(s: str | None) -> int | None:
    """
    Parse a size with an optional k/m/... suffix.
    Invalid values raise a ValueError. For added convenience, passing `None` returns `None`.
    """
    if s is None:
        return None
    try:
        return int(s)
    except ValueError:
        pass
    for i in SIZE_UNITS.keys():
        if s.endswith(i):
            try:
                return int(s[:-1]) * SIZE_UNITS[i]
            except ValueError:
                break
    raise ValueError("Invalid size specification.")


def pretty_duration(secs: float | None) -> str:
    formatters = [
        (100, "{:.0f}s"),
        (10, "{:2.1f}s"),
        (1, "{:1.2f}s"),
    ]
    if secs is None:
        return ""

    for limit, formatter in formatters:
        if secs >= limit:
            return formatter.format(secs)
    # less than 1 sec
    return f"{secs * 1000:.0f}ms"


def format_timestamp(s):
    s = time.localtime(s)
    d = datetime.datetime.fromtimestamp(time.mktime(s))
    return d.strftime("%Y-%m-%d %H:%M:%S")


def format_timestamp_with_milli(s):
    d = datetime.datetime.fromtimestamp(s)
    return d.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


@functools.lru_cache
def format_address(address: tuple | None) -> str:
    """
    This function accepts IPv4/IPv6 tuples and
    returns the formatted address string with port number
    """
    if address is None:
        return "<no address>"
    try:
        host = ipaddress.ip_address(address[0])
        if host.is_unspecified:
            return f"*:{address[1]}"
        if isinstance(host, ipaddress.IPv4Address):
            return f"{host}:{address[1]}"
        # If IPv6 is mapped to IPv4
        elif host.ipv4_mapped:
            return f"{host.ipv4_mapped}:{address[1]}"
        return f"[{host}]:{address[1]}"
    except ValueError:
        return f"{address[0]}:{address[1]}"
