"""
mitmproxy includes a set of content views which can be used to
format/decode/highlight/reencode data. While they are mostly used for HTTP message
bodies, the may be used in other contexts, e.g. to decode WebSocket messages.

See "Custom Contentviews" in the mitmproxy documentation for examples.
"""

import logging
import traceback
import warnings
from dataclasses import dataclass

from ._view_raw import raw
from ..tcp import TCPMessage
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
from .json import json_contentview
from . import mqtt
from . import msgpack
from . import multipart
from . import protobuf
from . import query
from . import socketio
from . import urlencoded
from . import wbxml
from . import xml_html
from ._api import Contentview
from ._api import InteractiveContentview
from ._api import Metadata
from ._api import SyntaxHighlight
from ._compat import add
from ._compat import get
from ._compat import LegacyContentview
from ._compat import remove
from ._registry import ContentviewRegistry
from ._utils import get_data
from ._utils import make_metadata
from .base import View
import mitmproxy_rs.contentviews
from mitmproxy import flow
from mitmproxy import http
from mitmproxy.utils import strutils

logger = logging.getLogger(__name__)


@dataclass
class ContentviewResult:
    text: str | None
    syntax_highlight: SyntaxHighlight
    view_name: str | None
    description: str


def prettify_message(
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
    flow: flow.Flow,
    view_name: str | None,
) -> ContentviewResult:
    if view_name == "auto":  # pragma: no cover
        warnings.warn(
            "The 'auto' view is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )
        view_name = None

    data, enc = get_data(message)
    if data is None:
        return ContentviewResult(
            text="Content is missing.",
            syntax_highlight="error",
            description="",
            view_name=None,
        )

    # Determine the correct view
    metadata = make_metadata(message, flow)
    view = registry.get_view(data, metadata, view_name)

    # Finally, we can pretty-print!
    try:
        ret = ContentviewResult(
            text=view.prettify(data, metadata),
            syntax_highlight=view.syntax_highlight,
            view_name=view.name,
            description=enc,
        )
    except Exception as e:
        logger.debug(f"Contentview failed: {e}", exc_info=True)
        if view_name:
            # If the contentview has been set explicitly, we display a hard error.
            ret = ContentviewResult(
                text=f"Couldn't parse as {view.name}:\n{traceback.format_exc()}",
                syntax_highlight="error",
                view_name=view.name,
                description=enc,
            )
        else:
            # If the contentview was chosen as the best matching one, fall back to raw.
            ret = ContentviewResult(
                text=registry["raw"].prettify(data, metadata),
                syntax_highlight=registry["raw"].syntax_highlight,
                view_name=registry["raw"].name,
                description=f"{enc}[failed to parse as {view.name}]",
            )

    ret.text = strutils.escape_control_characters(ret.text)
    return ret


def reencode_message(
    prettified: str,
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
    flow: flow.Flow,
    view_name: str,
) -> bytes:
    metadata = make_metadata(message, flow)
    view = registry[view_name.lower()]
    if not isinstance(view, InteractiveContentview):
        raise ValueError(f"Contentview {view.name} is not interactive.")
    return view.reencode(prettified, metadata)


registry = ContentviewRegistry()
# Legacy contentviews need to be registered explicitly.
_legacy_views = [
    graphql.ViewGraphQL,
    xml_html.ViewXmlHtml,
    wbxml.ViewWBXML,
    javascript.ViewJavaScript,
    css.ViewCSS,
    urlencoded.ViewURLEncoded,
    multipart.ViewMultipart,
    image.ViewImage,
    query.ViewQuery,
    mqtt.ViewMQTT,
    http3.ViewHttp3,
    dns.ViewDns,
    socketio.ViewSocketIO,
]
for ViewCls in _legacy_views:
    registry.register(LegacyContentview(ViewCls()))

_views: list[Contentview] = [
    json_contentview,
    raw,
]
for view in _views:
    registry.register(view)
for name in mitmproxy_rs.contentviews.__all__:
    cv = getattr(mitmproxy_rs.contentviews, name)
    if isinstance(cv, Contentview) and not isinstance(cv, type):
        registry.register(cv)


def add(contentview: Contentview | type[Contentview]) -> None:
    """
    Register a contentview for use in mitmproxy.

    You may pass a `Contentview` instance or the class itself.
    When passing the class, its constructor will be invoked with no arguments.
    """
    if isinstance(contentview, View):
        warnings.warn(
            f"`mitmproxy.contentviews.View` is deprecated since mitmproxy 12, "
            f"migrate {contentview.__class__.__name__} to `mitmproxy.contentviews.Contentview` instead.",
            stacklevel=2
        )
        contentview = LegacyContentview(contentview)
    registry.register(contentview)


__all__ = [
    # Public Contentview API
    "Contentview",
    "InteractiveContentview",
    "Metadata",
    "SyntaxHighlight",
    "add",
]
