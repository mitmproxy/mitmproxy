import re
import sys


def lookup(address, port, s):
    """
    Parse the pfctl state output s, to look up the destination host
    matching the client (address, port).

    Returns an (address, port) tuple, or None.
    """
    # We may get an ipv4-mapped ipv6 address here, e.g. ::ffff:127.0.0.1.
    # Those still appear as "127.0.0.1" in the table, so we need to strip the prefix.
    address = re.sub(r"^::ffff:(?=\d+.\d+.\d+.\d+$)", "", address)
    s = s.decode()

    # ALL tcp 192.168.1.13:57474 -> 23.205.82.58:443       ESTABLISHED:ESTABLISHED
    specv4 = f"{address}:{port}"

    # ALL tcp 2a01:e35:8bae:50f0:9d9b:ef0d:2de3:b733[58505] -> 2606:4700:30::681f:4ad0[443]       ESTABLISHED:ESTABLISHED
    specv6 = f"{address}[{port}]"

    for i in s.split("\n"):
        if "ESTABLISHED:ESTABLISHED" in i and specv4 in i:
            s = i.split()
            if len(s) > 4:
                if sys.platform.startswith("freebsd"):
                    # strip parentheses for FreeBSD pfctl
                    s = s[3][1:-1].split(":")
                else:
                    s = s[4].split(":")

                if len(s) == 2:
                    return s[0], int(s[1])
        elif "ESTABLISHED:ESTABLISHED" in i and specv6 in i:
            s = i.split()
            if len(s) > 4:
                s = s[4].split("[")
                port = s[1].split("]")
                port = port[0]
                return s[0], int(port)
    raise RuntimeError("Could not resolve original destination.")
