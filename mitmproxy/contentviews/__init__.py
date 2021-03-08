"""
Mitmproxy Content Views
=======================

mitmproxy includes a set of content views which can be used to
format/decode/highlight data. While they are mostly used for HTTP message
bodies, the may be used in other contexts, e.g. to decode WebSocket messages.

Thus, the View API is very minimalistic. The only arguments are `data` and
`**metadata`, where `data` is the actual content (as bytes). The contents on
metadata depend on the protocol in use. Known attributes can be found in
`base.View`.
"""
import traceback
from typing import List, Union
from typing import Optional

from mitmproxy import flow
from mitmproxy import http
from mitmproxy.utils import strutils
from . import (
    auto, raw, hex, json, xml_html, wbxml, javascript, css,
    urlencoded, multipart, image, query, protobuf, msgpack, graphql
)
from .base import View, KEY_MAX, format_text, format_dict, TViewResult
from ..http import HTTPFlow
from ..tcp import TCPMessage, TCPFlow
from ..websocket import WebSocketMessage

views: List[View] = []


def get(name: str) -> Optional[View]:
    for i in views:
        if i.name.lower() == name.lower():
            return i
    return None


def add(view: View) -> None:
    # TODO: auto-select a different name (append an integer?)
    for i in views:
        if i.name == view.name:
            raise ValueError("Duplicate view: " + view.name)

    views.append(view)


def remove(view: View) -> None:
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


def get_message_content_view(
    viewname: str,
    message: Union[http.Message, TCPMessage, WebSocketMessage],
    flow: Union[HTTPFlow, TCPFlow],
):
    """
    Like get_content_view, but also handles message encoding.
    """
    viewmode = get(viewname)
    if not viewmode:
        viewmode = get("auto")
    assert viewmode

    content: Optional[bytes]
    try:
        content = message.content
    except ValueError:
        assert isinstance(message, http.Message)
        content = message.raw_content
        enc = "[cannot decode]"
    else:
        if isinstance(message, http.Message) and content != message.raw_content:
            enc = "[decoded {}]".format(
                message.headers.get("content-encoding")
            )
        else:
            enc = ""

    if content is None:
        return "", iter([[("error", "content missing")]]), None

    content_type = None
    http_message = None
    if isinstance(message, http.Message):
        http_message = message
        if ctype := message.headers.get("content-type"):
            if ct := http.parse_content_type(ctype):
                content_type = f"{ct[0]}/{ct[1]}"

    description, lines, error = get_content_view(
        viewmode, content,
        content_type=content_type,
        flow=flow,
        http_message=http_message,
    )

    if enc:
        description = f"{enc} {description}"

    return description, lines, error


def get_tcp_content_view(
    viewname: str,
    data: bytes,
    flow: TCPFlow,
):
    viewmode = get(viewname)
    if not viewmode:
        viewmode = get("auto")

    # https://github.com/mitmproxy/mitmproxy/pull/3970#issuecomment-623024447
    assert viewmode

    description, lines, error = get_content_view(viewmode, data, flow=flow)

    return description, lines, error


def get_content_view(
    viewmode: View,
    data: bytes,
    *,
    content_type: Optional[str] = None,
    flow: Optional[flow.Flow] = None,
    http_message: Optional[http.Message] = None,
):
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
        ret = viewmode(data, content_type=content_type, flow=flow, http_message=http_message)
        if ret is None:
            ret = "Couldn't parse: falling back to Raw", get("Raw")(
                data, content_type=content_type, flow=flow, http_message=http_message
            )[1]
        desc, content = ret
        error = None
    # Third-party viewers can fail in unexpected ways...
    except Exception:
        desc = "Couldn't parse: falling back to Raw"
        raw = get("Raw")
        assert raw
        content = raw(data, content_type=content_type, flow=flow, http_message=http_message)[1]
        error = f"{getattr(viewmode, 'name')} content viewer failed: \n{traceback.format_exc()}"

    return desc, safe_to_print(content), error


# The order in which ContentViews are added is important!
add(auto.ViewAuto())
add(raw.ViewRaw())
add(hex.ViewHex())
add(graphql.ViewGraphQL())
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
add(msgpack.ViewMsgPack())

__all__ = [
    "View", "KEY_MAX", "format_text", "format_dict", "TViewResult",
    "get", "add", "remove", "get_content_view", "get_message_content_view",
]
