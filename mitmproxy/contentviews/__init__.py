"""
mitmproxy includes a set of content views which can be used to
format/decode/highlight/reencode data. While they are mostly used for HTTP message
bodies, the may be used in other contexts, e.g. to decode WebSocket messages.

See "Custom Contentviews" in the mitmproxy documentation for more information.
"""
import logging
import traceback
import warnings
from dataclasses import dataclass
from typing import overload, cast
from warnings import deprecated
import mitmproxy_rs.contentviews

from ._compat import LegacyContentview, get, add, remove
from ..flow import Flow
from ..tcp import TCPMessage
from ..tools.main import mitmproxy
from ..udp import UDPMessage
from ..websocket import WebSocketMessage
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
from ._api import Contentview, SyntaxHighlight
from ._api import InteractiveContentview
from ._api import Metadata
from ._registry import ContentviewRegistry
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import tcp
from mitmproxy import udp
from mitmproxy.utils import signals
from mitmproxy.utils import strutils


logger = logging.getLogger(__name__)

@dataclass
class ContentviewResult:
    prettified: str | None
    syntax_highlight: SyntaxHighlight
    view_name: str | None
    description: str


def _make_metadata(
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
    flow: Flow,
) -> Metadata:
    metadata = Metadata(flow=flow)

    match message:
        case http.Message():
            metadata.http_message = message
            if ctype := message.headers.get("content-type"):
                if ct := http.parse_content_type(ctype):
                    metadata.content_type = f"{ct[0]}/{ct[1]}"
        case TCPMessage():
            metadata.tcp_message = message
        case UDPMessage():
            metadata.udp_message = message
        case WebSocketMessage():
            metadata.websocket_message = message

    return metadata


def _get_view(
    data: bytes,
    metadata: Metadata,
    view_name: str | None
) -> Contentview:
    if view_name:
        try:
            return registry[view_name.lower()]
        except KeyError:
            logger.warning(f"Unknown contentview {view_name!r}, falling back to `auto`.")

    return max(
        registry,
        key=lambda cv: cv.render_priority(data, metadata)
    )

def _get_data(
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
) -> tuple[bytes | None, str]:
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

    return content, enc


def prettify_message(
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
    flow: flow.Flow,
    view_name: str | None,
) -> ContentviewResult:
    if view_name == "auto":
        warnings.warn(
            "The 'auto' view is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )
        view_name = None

    data, enc = _get_data(message)
    if data is None:
        return ContentviewResult(
            prettified="Content is missing.",
            syntax_highlight="error",
            description="",
            view_name=None,
        )

    # Determine the correct view
    metadata = _make_metadata(message, flow)
    view = _get_view(data, metadata, view_name)

    # Finally, we can pretty-print!
    try:
        ret = ContentviewResult(
            prettified=view.prettify(data, metadata),
            syntax_highlight=view.syntax_highlight,
            view_name=view.name,
            description=enc,
        )
    except Exception as e:
        logger.warning(f"Contentview failed: {e}", exc_info=True)
        if view_name:
            # If the contentview has been set explicitly, we display a hard error.
            ret = ContentviewResult(
                prettified=f"Couldn't parse as {view.name}:\n{traceback.format_exc()}",
                syntax_highlight="error",
                view_name=view.name,
                description=enc,
            )
        else:
            # If the contentview was chosen as the best matching one, fall back to raw.
            ret = ContentviewResult(
                prettified=registry["raw"].prettify(data, metadata),
                syntax_highlight=registry["raw"].syntax_highlight,
                view_name=registry["raw"].name,
                description=f"{enc}[failed to parse as {view.name}]",
            )

    ret.prettified = strutils.escape_control_characters(ret.prettified)
    return ret


def reencode_message(
    prettified: str,
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
    flow: flow.Flow,
    view_name: str,
) -> bytes:
    metadata = _make_metadata(message, flow)
    view = registry[view_name.lower()]
    if not isinstance(view, InteractiveContentview):
        raise ValueError(f"Contentview {view.name} is not interactive.")
    return view.reencode(prettified, metadata)

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


registry = ContentviewRegistry()
# Legacy contentviews need to be registered explicitly.
_legacy_views = [
    raw.ViewRaw,
    graphql.ViewGraphQL,
    json.ViewJSON,
    xml_html.ViewXmlHtml,
    wbxml.ViewWBXML,
    javascript.ViewJavaScript,
    css.ViewCSS,
    urlencoded.ViewURLEncoded,
    multipart.ViewMultipart,
    image.ViewImage,
    query.ViewQuery,
    grpc.ViewGrpcProtobuf,
    mqtt.ViewMQTT,
    http3.ViewHttp3,
    dns.ViewDns,
    socketio.ViewSocketIO
]
for View in _legacy_views:
    registry.register(LegacyContentview(View()))

for name in mitmproxy_rs.contentviews.__all__:
    cv = getattr(mitmproxy_rs.contentviews, name)
    if isinstance(cv, Contentview):
        registry.register(cv)



__all__ = [
    # Public Contentview API
    "Contentview",
    "InteractiveContentview",
    "Metadata",
    # Deprecated as of 2025-04:
    "get",
    "add",
    "remove",
    # Internal API
    "registry",
    "prettify_message",
    "ContentviewResult",
]
