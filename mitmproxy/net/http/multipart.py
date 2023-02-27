from __future__ import annotations

import mimetypes
import re
import warnings
from urllib.parse import quote

from mitmproxy.net.http import headers


def encode_multipart(content_type: str, parts: list[tuple[bytes, bytes]]) -> bytes:
    if content_type:
        ct = headers.parse_content_type(content_type)
        if ct is not None:
            try:
                raw_boundary = ct[2]["boundary"].encode("ascii")
                boundary = quote(raw_boundary)
            except (KeyError, UnicodeError):
                return b""
            hdrs = []
            for key, value in parts:
                file_type = (
                    mimetypes.guess_type(str(key))[0] or "text/plain; charset=utf-8"
                )

                if key:
                    hdrs.append(b"--%b" % boundary.encode("utf-8"))
                    disposition = b'form-data; name="%b"' % key
                    hdrs.append(b"Content-Disposition: %b" % disposition)
                    hdrs.append(b"Content-Type: %b" % file_type.encode("utf-8"))
                    hdrs.append(b"")
                    hdrs.append(value)
                hdrs.append(b"")

                if value is not None:
                    # If boundary is found in value then raise ValueError
                    if re.search(
                        rb"^--%b$" % re.escape(boundary.encode("utf-8")), value
                    ):
                        raise ValueError(b"boundary found in encoded string")

            hdrs.append(b"--%b--\r\n" % boundary.encode("utf-8"))
            temp = b"\r\n".join(hdrs)
            return temp
    return b""


def decode_multipart(
    content_type: str | None, content: bytes
) -> list[tuple[bytes, bytes]]:
    """
    Takes a multipart boundary encoded string and returns list of (key, value) tuples.
    """
    if content_type:
        ct = headers.parse_content_type(content_type)
        if not ct:
            return []
        try:
            boundary = ct[2]["boundary"].encode("ascii")
        except (KeyError, UnicodeError):
            return []

        rx = re.compile(rb'\bname="([^"]+)"')
        r = []
        if content is not None:
            for i in content.split(b"--" + boundary):
                parts = i.splitlines()
                if len(parts) > 1 and parts[0][0:2] != b"--":
                    match = rx.search(parts[1])
                    if match:
                        key = match.group(1)
                        value = b"".join(parts[3 + parts[2:].index(b"") :])
                        r.append((key, value))
        return r
    return []


def encode(ct, parts):  # pragma: no cover
    # 2023-02
    warnings.warn(
        "multipart.encode is deprecated, use multipart.encode_multipart instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return encode_multipart(ct, parts)


def decode(ct, content):  # pragma: no cover
    # 2023-02
    warnings.warn(
        "multipart.decode is deprecated, use multipart.decode_multipart instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return encode_multipart(ct, content)
