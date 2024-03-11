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
    # Use the charset from the header if possible
    parsed_content_type = parse_content_type(content_type)
    enc = parsed_content_type[2].get("charset") if parsed_content_type else None

    # Otherwise, infer the encoding
    if not enc and "json" in content_type:
        enc = "utf8"

    if not enc and "html" in content_type:
        meta_charset = re.search(
            rb"""<meta[^>]+charset=['"]?([^'">]+)""", content, re.IGNORECASE
        )
        if meta_charset:
            enc = meta_charset.group(1).decode("ascii", "ignore")

    if not enc and "text/css" in content_type:
        # @charset rule must be the very first thing.
        css_charset = re.match(rb"""@charset "([^"]+)";""", content, re.IGNORECASE)
        if css_charset:
            enc = css_charset.group(1).decode("ascii", "ignore")

    # Fallback to latin-1
    if not enc:
        enc = "latin-1"

    # Use GB 18030 as the superset of GB2312 and GBK to fix common encoding problems on Chinese websites.
    if enc.lower() in ("gb2312", "gbk"):
        enc = "gb18030"

    return enc
