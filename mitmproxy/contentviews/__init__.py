"""
Mitmproxy Content Views
=======================

mitmproxy includes a set of content views which can be used to
format/decode/highlight data. While they are currently used for HTTP message
bodies only, the may be used in other contexts in the future, e.g. to decode
protobuf messages sent as WebSocket frames.

Thus, the View API is very minimalistic. The only arguments are `data` and
`**metadata`, where `data` is the actual content (as bytes). The contents on
metadata depend on the protocol in use. For HTTP, the message headers are
passed as the ``headers`` keyword argument. For HTTP requests, the query
parameters are passed as the ``query`` keyword argument.
"""
import traceback
from typing import Dict, Optional  # noqa
from typing import List  # noqa

from mitmproxy import exceptions
from mitmproxy.net import http
from mitmproxy.utils import strutils
from . import (
    auto, raw, hex, json, xml_html, wbxml, javascript, css,
    urlencoded, multipart, image, query, protobuf
)
from .base import View, KEY_MAX, format_text, format_dict, TViewResult

views: List[View] = []
content_types_map: Dict[str, List[View]] = {}


def get(name: str) -> Optional[View]:
    for i in views:
        if i.name.lower() == name.lower():
            return i
    return None


def add(view: View) -> None:
    # TODO: auto-select a different name (append an integer?)
    for i in views:
        if i.name == view.name:
            raise exceptions.ContentViewException("Duplicate view: " + view.name)

    views.append(view)

    for ct in view.content_types:
        l = content_types_map.setdefault(ct, [])
        l.append(view)


def remove(view: View) -> None:
    for ct in view.content_types:
        l = content_types_map.setdefault(ct, [])
        l.remove(view)

        if not len(l):
            del content_types_map[ct]

    views.remove(view)


def safe_to_print(lines, encoding="utf8"):
    """
    Wraps a content generator so that each text portion is a *safe to print* unicode string.
    """
    for line in lines:
        clean_line = []
        for (style, text) in line:
            if isinstance(text, bytes):
                text = text.decode(encoding, "replace")
            text = strutils.escape_control_characters(text)
            clean_line.append((style, text))
        yield clean_line


def get_message_content_view(viewname, message, flow):
    """
    Like get_content_view, but also handles message encoding.
    """
    viewmode = get(viewname)
    if not viewmode:
        viewmode = get("auto")
    try:
        content = message.content
    except ValueError:
        content = message.raw_content
        enc = "[cannot decode]"
    else:
        if isinstance(message, http.Message) and content != message.raw_content:
            enc = "[decoded {}]".format(
                message.headers.get("content-encoding")
            )
        else:
            enc = None

    if content is None:
        return "", iter([[("error", "content missing")]]), None

    metadata = {}
    if isinstance(message, http.Request):
        metadata["query"] = message.query
    if isinstance(message, http.Message):
        metadata["headers"] = message.headers
    metadata["message"] = message
    metadata["flow"] = flow

    description, lines, error = get_content_view(
        viewmode, content, **metadata
    )

    if enc:
        description = "{} {}".format(enc, description)

    return description, lines, error


def get_tcp_content_view(viewname: str, data: bytes):
    viewmode = get(viewname)
    if not viewmode:
        viewmode = get("auto")

    # https://github.com/mitmproxy/mitmproxy/pull/3970#issuecomment-623024447
    assert viewmode

    description, lines, error = get_content_view(viewmode, data)

    return description, lines, error


def get_content_view(viewmode: View, data: bytes, **metadata):
    """
        Args:
            viewmode: the view to use.
            data, **metadata: arguments passed to View instance.

        Returns:
            A (description, content generator, error) tuple.
            If the content view raised an exception generating the view,
            the exception is returned in error and the flow is formatted in raw mode.
            In contrast to calling the views directly, text is always safe-to-print unicode.
    """
    try:
        ret = viewmode(data, **metadata)
        if ret is None:
            ret = "Couldn't parse: falling back to Raw", get("Raw")(data, **metadata)[1]
        desc, content = ret
        error = None
    # Third-party viewers can fail in unexpected ways...
    except Exception:
        desc = "Couldn't parse: falling back to Raw"
        raw = get("Raw")
        assert raw
        content = raw(data, **metadata)[1]
        error = "{} Content viewer failed: \n{}".format(
            getattr(viewmode, "name"),
            traceback.format_exc()
        )

    return desc, safe_to_print(content), error


# The order in which ContentViews are added is important!
add(auto.ViewAuto())
add(raw.ViewRaw())
add(hex.ViewHex())
add(json.ViewJSON())
add(xml_html.ViewXmlHtml())
add(wbxml.ViewWBXML())
add(javascript.ViewJavaScript())
add(css.ViewCSS())
add(urlencoded.ViewURLEncoded())
add(multipart.ViewMultipart())
add(image.ViewImage())
add(query.ViewQuery())
add(protobuf.ViewProtobuf())

__all__ = [
    "View", "KEY_MAX", "format_text", "format_dict", "TViewResult",
    "get", "add", "remove", "get_content_view", "get_message_content_view",
]
