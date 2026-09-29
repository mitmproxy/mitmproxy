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

        delimiter = b"--" + boundary

        # A boundary delimiter must begin at the start of the body or
        # immediately after a CRLF/LF. It must then be followed by either:
        #   - CRLF
        #   - LF
        #   - "--" (closing boundary)
        #   - end of input
        boundary_rx = re.compile(
            rb"(?:^|(?<=\r\n)|(?<=\n))" + re.escape(delimiter) + rb"(?=--|\r\n|\n|$)"
        )

        matches = list(boundary_rx.finditer(content))
        if not matches:
            return []

        rx = re.compile(rb'\bname="([^"]+)"')
        r = []

        for index, match in enumerate(matches):
            delimiter_end = match.end()

            # This is the closing boundary: --boundary--
            if content[delimiter_end : delimiter_end + 2] == b"--":
                break

            # The next boundary marks the end of this part.
            if index + 1 < len(matches):
                next_boundary_start = matches[index + 1].start()
                chunk = content[delimiter_end:next_boundary_start]
            else:
                chunk = content[delimiter_end:]

            # Remove the newline immediately following the boundary.
            if chunk.startswith(b"\r\n"):
                chunk = chunk[2:]
            elif chunk.startswith(b"\n"):
                chunk = chunk[1:]

            # Separate headers from value.
            header_end = chunk.find(b"\r\n\r\n")
            delimiter_len = 4

            if header_end == -1:
                header_end = chunk.find(b"\n\n")
                delimiter_len = 2

            if header_end == -1:
                continue

            headers_part = chunk[:header_end]
            value = chunk[header_end + delimiter_len :]

            name_match = rx.search(headers_part)
            if not name_match:
                continue

            key = name_match.group(1)

            # Remove the structural newline immediately before the next
            # boundary. Preserve the existing encode_multipart() behavior.
            if value.endswith(b"\r\n\r\n"):
                value = value[:-4]
            elif value.endswith(b"\r\n"):
                value = value[:-2]
            elif value.endswith(b"\n"):
                value = value[:-1]

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
