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

from typing import Dict, Optional  # noqa
from typing import List  # noqa
from typing import Tuple  # noqa

from . import (
    auto, raw, hex, json, xml_html, html_outline, wbxml, javascript, css,
    urlencoded, multipart, image, query, protobuf
)
from .base import (
    VIEW_CUTOFF, KEY_MAX, views, content_types_map, view_prompts,
    View, format_text, format_dict, get, get_by_shortcut,
    add, remove, safe_to_print, get_content_view, get_message_content_view
)


# The order in which ContentViews are added is important!
add(auto.ViewAuto())
add(raw.ViewRaw())
add(hex.ViewHex())
add(json.ViewJSON())
add(xml_html.ViewXmlHtml())
add(wbxml.ViewWBXML())
add(html_outline.ViewHTMLOutline())
add(javascript.ViewJavaScript())
add(css.ViewCSS())
add(urlencoded.ViewURLEncoded())
add(multipart.ViewMultipart())
add(image.ViewImage())
add(query.ViewQuery())
add(protobuf.ViewProtobuf())

__all__ = [
    "VIEW_CUTOFF",
    "KEY_MAX",
    "views",
    "content_types_map",
    "view_prompts",
    "View",
    "format_text",
    "format_dict",
    "get",
    "get_by_shortcut",
    "add",
    "remove",
    "safe_to_print",
    "get_content_view",
    "get_message_content_view",
]
