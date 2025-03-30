"""
mitmproxy includes a set of content views which can be used to
format/decode/highlight/reencode data. While they are mostly used for HTTP message
bodies, the may be used in other contexts, e.g. to decode WebSocket messages.

See "Custom Contentviews" in the mitmproxy documentation for more information.
"""

import traceback
from typing import overload, cast
from warnings import deprecated
import mitmproxy_rs.contentviews

from ._compat import LegacyContentview
from ..tcp import TCPMessage
from ..tools.main import mitmproxy
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
from . import socketio
from . import urlencoded
from . import wbxml
from . import xml_html
from .base import format_dict
from .base import format_text
from .base import KEY_MAX
from .base import TViewResult
from .base import View
from .api import Contentview
from .api import InteractiveContentview
from .api import Metadata
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import udp
from mitmproxy.utils import signals
from mitmproxy.utils import strutils

views: list[Contentview] = []


def _update(view: Contentview) -> None: ...


on_add = signals.SyncSignal(_update)
"""A new contentview has been added."""
on_remove = signals.SyncSignal(_update)
"""A contentview has been removed."""

def get(name: str) -> Contentview | None:
    for i in views:
        if i.name.lower() == name.lower():
            return i
    return None


@overload
@deprecated("Use `mitmproxy.contentviews.Contentview` instead.")
def add(view: View) -> None:
    ...

@overload
def add(view: Contentview) -> None:
    ...

def add(view) -> None:

    if not isinstance(view, (Contentview, mitmproxy_rs.contentviews.Contentview)):
        view = LegacyContentview(view)

    # TODO: auto-select a different name (append an integer?)
    for i in views:
        if i.name == view.name:
            raise ValueError("Duplicate view: " + view.name)

    views.append(view)
    on_add.send(view)


@overload
@deprecated("Use `mitmproxy.contentviews.Contentview` instead.")
def remove(view: View) -> None:
    ...

@overload
def remove(view: Contentview) -> None:
    ...


def remove(view):
    if isinstance(view, View):
        view = next(
            v
            for v in views
            if isinstance(v, LegacyContentview) and v.contentview == view
        )
    assert isinstance(view, Contentview)
    views.remove(view)
    on_remove.send(view)



def get_message_content_view(
    viewname: str,
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
    flow: flow.Flow,
) -> tuple[str, str, str | None]:
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
        return "", "content missing", None


    metadata = Metadata(flow=flow)

    if isinstance(message, http.Message):
        metadata.http_message = message
        if ctype := message.headers.get("content-type"):
            if ct := http.parse_content_type(ctype):
                metadata.content_type = f"{ct[0]}/{ct[1]}"

    if isinstance(message, TCPMessage):
        metadata.tcp_message = message

    if isinstance(message, UDPMessage):
        metadata.udp_message = message

    if isinstance(message, WebSocketMessage):
        metadata.websocket_message = message

    description, lines, error = get_content_view(
        viewmode,
        content,
        metadata=metadata,
    )

    if enc:
        description = f"{enc} {description}"

    return description, lines, error


def get_content_view(
    viewmode: Contentview,
    data: bytes,
    metadata: Metadata
):
    """
    Args:
        viewmode: the view to use.
        data, **metadata: arguments passed to View instance.

    Returns:
        A (description, content, error) tuple.
        If the content view raised an exception generating the view,
        the exception is returned in error and the flow is formatted in raw mode.
        In contrast to calling the views directly, text is always safe-to-print unicode.
    """
    try:
        ret = viewmode.prettify(
            data,
            metadata
        )
        if ret is None:
            ret = (
                "Couldn't parse: falling back to Raw",
                get("Raw").prettify(data, metadata),
            )
        content = ret
        desc = viewmode.name
        error = None
    # Third-party viewers can fail in unexpected ways...
    except Exception as e:
        desc = "Couldn't parse: falling back to Raw"
        raw = get("Raw")
        assert raw
        content = raw.prettify(data, metadata)
        error = f"{getattr(viewmode, 'name')} content viewer failed: \n{traceback.format_exc()}"

    content = strutils.escape_control_characters(content)

    return desc, content, error


# The order in which ContentViews are added is important!
add(auto.ViewAuto())
add(raw.ViewRaw())
# FIXME remove add(hex.ViewHexStream())
# FIXME remove add(hex.ViewHexDump())
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
# FIXME remove add(protobuf.ViewProtobuf())
# FIXME remove add(msgpack.ViewMsgPack())
add(grpc.ViewGrpcProtobuf())
add(mqtt.ViewMQTT())
add(http3.ViewHttp3())
add(dns.ViewDns())
add(socketio.ViewSocketIO())

for name in mitmproxy_rs.contentviews.__all__:
    cv = cast(Contentview, getattr(mitmproxy_rs.contentviews, name))
    add(cv)


__all__ = [
    "Contentview",
    "InteractiveContentview",
    "Metadata",
    "add",
    "remove",
]
