import re

from mitmproxy.net.http import headers


def decode(hdrs, content):
    """
        Takes a multipart boundary encoded string and returns list of (key, value) tuples.
    """
    v = hdrs.get("content-type")
    if v:
        v = headers.parse_content_type(v)
        if not v:
            return []
        try:
            boundary = v[2]["boundary"].encode("ascii")
        except (KeyError, UnicodeError):
            return []

        rx = re.compile(br'\bname="([^"]+)"')
        r = []

        for i in content.split(b"--" + boundary):
            parts = i.splitlines()
            if len(parts) > 1 and parts[0][0:2] != b"--":
                match = rx.search(parts[1])
                if match:
                    key = match.group(1)
                    value = b"".join(parts[3 + parts[2:].index(b""):])
                    r.append((key, value))
        return r
    return []
