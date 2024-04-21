from __future__ import annotations

import socket


def get_local_ip(reachable: str = "8.8.8.8") -> str | None:
    """
    Get the default local outgoing IPv4 address without sending any packets.
    This will fail if the target address is known to be unreachable.
    We use Google DNS's IPv4 address as the default.
    """
    # https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((reachable, 80))
        return s.getsockname()[0]  # pragma: no cover
    except OSError:
        return None  # pragma: no cover
    finally:
        s.close()


def get_local_ip6(reachable: str = "2001:4860:4860::8888") -> str | None:
    """
    Get the default local outgoing IPv6 address without sending any packets.
    This will fail if the target address is known to be unreachable.
    We use Google DNS's IPv6 address as the default.
    """
    s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    try:
        s.connect((reachable, 80))
        return s.getsockname()[0]  # pragma: no cover
    except OSError:
        return None  # pragma: no cover
    finally:
        s.close()
