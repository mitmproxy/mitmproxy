import collections
import re


def parse_content_type(c: str) -> tuple[str, str, dict[str, str]] | None:
    """
    A simple parser for content-type values. Returns a (type, subtype,
    parameters) tuple, where type and subtype are strings, and parameters
    is a dict. If the string could not be parsed, return None.

    E.g. the following string:

        text/html; charset=UTF-8

    Returns:

        ("text", "html", {"charset": "UTF-8"})
    """
    parts = c.split(";", 1)
    ts = parts[0].split("/", 1)
    if len(ts) != 2:
        return None
    d = collections.OrderedDict()
    if len(parts) == 2:
        for i in parts[1].split(";"):
            clause = i.split("=", 1)
            if len(clause) == 2:
                d[clause[0].strip()] = clause[1].strip()
    return ts[0].lower(), ts[1].lower(), d


def assemble_content_type(type, subtype, parameters):
    if not parameters:
        return f"{type}/{subtype}"
    params = "; ".join(f"{k}={v}" for k, v in parameters.items())
    return f"{type}/{subtype}; {params}"


def infer_content_encoding(content_type: str, content: bytes = b"") -> str:
    """
    Infer the encoding of content from the content-type header.
    """
    enc = None

    # BOM has the highest priority
    if content.startswith(b"\x00\x00\xfe\xff"):
        enc = "utf-32be"
    elif content.startswith(b"\xff\xfe\x00\x00"):
        enc = "utf-32le"
    elif content.startswith(b"\xfe\xff"):
        enc = "utf-16be"
    elif content.startswith(b"\xff\xfe"):
        enc = "utf-16le"
    elif content.startswith(b"\xef\xbb\xbf"):
        # 'utf-8-sig' will strip the BOM on decode
        enc = "utf-8-sig"
    elif parsed_content_type := parse_content_type(content_type):
        # Use the charset from the header if possible
        enc = parsed_content_type[2].get("charset")

    # Otherwise, infer the encoding
    if not enc and "json" in content_type:
        enc = "utf8"

    if not enc and "html" in content_type:
        meta_charset = re.search(
            rb"""<meta[^>]+charset=['"]?([^'">]+)""", content, re.IGNORECASE
        )
        if meta_charset:
            enc = meta_charset.group(1).decode("ascii", "ignore")
        else:
            # Fallback to utf8 for html
            # Ref: https://html.spec.whatwg.org/multipage/parsing.html#determining-the-character-encoding
            # > 9. [snip] the comprehensive UTF-8 encoding is suggested.
            enc = "utf8"

    if not enc and "xml" in content_type:
        if xml_encoding := re.search(
            rb"""<\?xml[^\?>]+encoding=['"]([^'"\?>]+)""", content, re.IGNORECASE
        ):
            enc = xml_encoding.group(1).decode("ascii", "ignore")
        else:
            # Fallback to utf8 for xml
            # Ref: https://datatracker.ietf.org/doc/html/rfc7303#section-8.5
            # > the XML processor [snip] to determine an encoding of UTF-8.
            enc = "utf8"

    if not enc and ("javascript" in content_type or "ecmascript" in content_type):
        # Fallback to utf8 for javascript
        # Ref: https://datatracker.ietf.org/doc/html/rfc9239#section-4.2
        # > 3. Else, the character encoding scheme is assumed to be UTF-8
        enc = "utf8"

    if not enc and "text/css" in content_type:
        # @charset rule must be the very first thing.
        css_charset = re.match(rb"""@charset "([^"]+)";""", content, re.IGNORECASE)
        if css_charset:
            enc = css_charset.group(1).decode("ascii", "ignore")
        else:
            # Fallback to utf8 for css
            # Ref: https://drafts.csswg.org/css-syntax/#determine-the-fallback-encoding
            # > 4. Otherwise, return utf-8
            enc = "utf8"

    # Fallback to latin-1
    if not enc:
        enc = "latin-1"

    # Use GB 18030 as the superset of GB2312 and GBK to fix common encoding problems on Chinese websites.
    if enc.lower() in ("gb2312", "gbk"):
        enc = "gb18030"

    return enc
