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

from ..tcp import TCPMessage
from ..udp import UDPMessage
from ..websocket import WebSocketMessage
from . import auto
from . import css
from . import dns
from . import graphql
from . import grpc
from . import hex
from . import http3
from . import image
from . import javascript
from . import json
from . import mqtt
from . import msgpack
from . import multipart
from . import protobuf
from . import query
from . import raw
from . import urlencoded
from . import wbxml
from . import xml_html
from .base import format_dict
from .base import format_text
from .base import KEY_MAX
from .base import TViewResult
from .base import View
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import udp
from mitmproxy.utils import signals
from mitmproxy.utils import strutils

views: list[View] = []


def _update(view: View) -> None: ...


on_add = signals.SyncSignal(_update)
"""A new contentview has been added."""
on_remove = signals.SyncSignal(_update)
"""A contentview has been removed."""


def get(name: str) -> View | None:
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
    on_add.send(view)


def remove(view: View) -> None:
    views.remove(view)
    on_remove.send(view)


def safe_to_print(lines, encoding="utf8"):
    """
    Wraps a content generator so that each text portion is a *safe to print* unicode string.
    """
    for line in lines:
        clean_line = []
        for style, text in line:
            if isinstance(text, bytes):
                text = text.decode(encoding, "replace")
            text = strutils.escape_control_characters(text)
            clean_line.append((style, text))
        yield clean_line


def get_message_content_view(
    viewname: str,
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
    flow: flow.Flow,
):
    """
    Like get_content_view, but also handles message encoding.
    """
    viewmode = get(viewname)
    if not viewmode:
        viewmode = get("auto")
    assert viewmode

    content: bytes | None
    try:
        content = message.content
    except ValueError:
        assert isinstance(message, http.Message)
        content = message.raw_content
        enc = "[cannot decode]"
    else:
        if isinstance(message, http.Message) and content != message.raw_content:
            enc = "[decoded {}]".format(message.headers.get("content-encoding"))
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

    tcp_message = None
    if isinstance(message, TCPMessage):
        tcp_message = message

    udp_message = None
    if isinstance(message, UDPMessage):
        udp_message = message

    description, lines, error = get_content_view(
        viewmode,
        content,
        content_type=content_type,
        flow=flow,
        http_message=http_message,
        tcp_message=tcp_message,
        udp_message=udp_message,
    )

    if enc:
        description = f"{enc} {description}"

    return description, lines, error


def get_content_view(
    viewmode: View,
    data: bytes,
    *,
    content_type: str | None = None,
    flow: flow.Flow | None = None,
    http_message: http.Message | None = None,
    tcp_message: tcp.TCPMessage | None = None,
    udp_message: udp.UDPMessage | None = None,
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
        ret = viewmode(
            data,
            content_type=content_type,
            flow=flow,
            http_message=http_message,
            tcp_message=tcp_message,
            udp_message=udp_message,
        )
        if ret is None:
            ret = (
                "Couldn't parse: falling back to Raw",
                get("Raw")(
                    data,
                    content_type=content_type,
                    flow=flow,
                    http_message=http_message,
                    tcp_message=tcp_message,
                    udp_message=udp_message,
                )[1],
            )
        desc, content = ret
        error = None
    # Third-party viewers can fail in unexpected ways...
    except Exception:
        desc = "Couldn't parse: falling back to Raw"
        raw = get("Raw")
        assert raw
        content = raw(
            data,
            content_type=content_type,
            flow=flow,
            http_message=http_message,
            tcp_message=tcp_message,
            udp_message=udp_message,
        )[1]
        error = f"{getattr(viewmode, 'name')} content viewer failed: \n{traceback.format_exc()}"

    return desc, safe_to_print(content), error


# The order in which ContentViews are added is important!
add(auto.ViewAuto())
add(raw.ViewRaw())
add(hex.ViewHexStream())
add(hex.ViewHexDump())
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
add(grpc.ViewGrpcProtobuf())
add(mqtt.ViewMQTT())
add(http3.ViewHttp3())
add(dns.ViewDns())

__all__ = [
    "View",
    "KEY_MAX",
    "format_text",
    "format_dict",
    "TViewResult",
    "get",
    "add",
    "remove",
    "get_content_view",
    "get_message_content_view",
]
