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

    Preserves all \\n and \\r characters within the body content, unlike the
    previous implementation which used splitlines() and lost those bytes.
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
            for part in content.split(b"--" + boundary):
                # Strip leading newline(s) that follow the boundary delimiter
                if part.startswith(b"\r\n"):
                    part = part[2:]
                elif part.startswith(b"\n"):
                    part = part[1:]

                # Skip empty parts and closing boundary (--)
                if not part or part.startswith(b"--"):
                    continue

                # Find the header/body separator
                # RFC 2046 uses \r\n\r\n, but some clients send \n\n
                sep_idx = part.find(b"\r\n\r\n")
                if sep_idx != -1:
                    header_section = part[:sep_idx]
                    body = part[sep_idx + 4:]
                else:
                    sep_idx = part.find(b"\n\n")
                    if sep_idx != -1:
                        header_section = part[:sep_idx]
                        body = part[sep_idx + 2:]
                    else:
                        continue

                match = rx.search(header_section)
                if match:
                    key = match.group(1)
                    # Strip trailing CRLF/LF which belongs to the boundary delimiter
                    # (per RFC 2046, the CRLF before a boundary is not part of the data)
                    if body.endswith(b"\r\n"):
                        body = body[:-2]
                    elif body.endswith(b"\n"):
                        body = body[:-1]
                    r.append((key, body))
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
