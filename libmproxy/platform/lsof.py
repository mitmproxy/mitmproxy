import re

def lookup(address, port, s):
    """
        Parse the pfctl state output s, to look up the destination host
        matching the client (address, port).

        Returns an (address, port) tuple, or None.
    """
    spec = "%s:%s"%(address, port)
    for i in s.split("\n"):
        if "ESTABLISHED" in i and spec in i:
            m = re.match(".* (\S*)->%s" % spec, i)
            if m:
                s = m.group(1).split(":")
                if len(s) == 2:
                    return s[0], int(s[1])
