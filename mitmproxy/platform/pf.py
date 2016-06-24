import sys


def lookup(address, port, s):
    """
        Parse the pfctl state output s, to look up the destination host
        matching the client (address, port).

        Returns an (address, port) tuple, or None.
    """
    s = s.decode()
    spec = "%s:%s" % (address, port)
    for i in s.split("\n"):
        if "ESTABLISHED:ESTABLISHED" in i and spec in i:
            s = i.split()
            if len(s) > 4:
                if sys.platform.startswith("freebsd"):
                    # strip parentheses for FreeBSD pfctl
                    s = s[3][1:-1].split(":")
                else:
                    s = s[4].split(":")

                if len(s) == 2:
                    return s[0], int(s[1])
    raise RuntimeError("Could not resolve original destination.")
