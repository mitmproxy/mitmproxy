import socket


def isascii(s):
    try:
        s.decode("ascii")
    except ValueError:
        return False
    return True


def cleanBin(s, fixspacing=False):
    """
        Cleans binary data to make it safe to display. If fixspacing is True,
        tabs, newlines and so forth will be maintained, if not, they will be
        replaced with a placeholder.
    """
    parts = []
    for i in s:
        o = ord(i)
        if (o > 31 and o < 127):
            parts.append(i)
        elif i in "\n\t" and not fixspacing:
            parts.append(i)
        else:
            parts.append(".")
    return "".join(parts)


def hexdump(s):
    """
        Returns a set of tuples:
            (offset, hex, str)
    """
    parts = []
    for i in range(0, len(s), 16):
        o = "%.10x" % i
        part = s[i:i + 16]
        x = " ".join("%.2x" % ord(i) for i in part)
        if len(part) < 16:
            x += " "
            x += " ".join("  " for i in range(16 - len(part)))
        parts.append(
            (o, x, cleanBin(part, True))
        )
    return parts


def inet_ntop(address_family, packed_ip):
    if hasattr(socket, "inet_ntop"):
        return socket.inet_ntop(address_family, packed_ip)
    # Windows Fallbacks
    if address_family == socket.AF_INET:
        return socket.inet_ntoa(packed_ip)
    if address_family == socket.AF_INET6:
        ip = packed_ip.encode("hex")
        return ":".join([ip[i:i + 4] for i in range(0, len(ip), 4)])


def inet_pton(address_family, ip_string):
    if hasattr(socket, "inet_pton"):
        return socket.inet_pton(address_family, ip_string)
    # Windows Fallbacks
    if address_family == socket.AF_INET:
        return socket.inet_aton(ip_string)
    if address_family == socket.AF_INET6:
        return ip_string.replace(":", "").decode("hex")