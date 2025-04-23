"""
mitmproxy includes a set of content views which can be used to
format/decode/highlight/reencode data. While they are mostly used for HTTP message
bodies, the may be used in other contexts, e.g. to decode WebSocket messages.

See "Custom Contentviews" in the mitmproxy documentation for examples.
"""

import logging
import sys
import traceback
import warnings
from dataclasses import dataclass

from ..addonmanager import cut_traceback
from ..tcp import TCPMessage
from ..udp import UDPMessage
from ..websocket import WebSocketMessage
from . import dns
from . import graphql
from . import image
from . import javascript
from . import mqtt
from . import multipart
from . import query
from . import socketio
from . import urlencoded
from . import wbxml
from . import xml_html
from ._api import Contentview
from ._api import InteractiveContentview
from ._api import Metadata
from ._api import SyntaxHighlight
from ._compat import get  # noqa: F401
from ._compat import LegacyContentview
from ._compat import remove  # noqa: F401
from ._registry import ContentviewRegistry
from ._utils import get_data
from ._utils import make_metadata
from ._view_css import css
from ._view_http3 import http3
from ._view_json import json_view
from ._view_raw import raw
from .base import View
import mitmproxy_rs.contentviews
from mitmproxy import flow
from mitmproxy import http
from mitmproxy.utils import strutils

logger = logging.getLogger(__name__)


@dataclass
class ContentviewResult:
    text: str
    syntax_highlight: SyntaxHighlight
    view_name: str | None
    description: str


registry = ContentviewRegistry()


def prettify_message(
    message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
    flow: flow.Flow,
    view_name: str = "auto",
    registry: ContentviewRegistry = registry,
) -> ContentviewResult:
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
        logger.debug(f"Contentview {view.name!r} failed: {e}", exc_info=True)
        if view_name == "auto":
            # If the contentview was chosen as the best matching one, fall back to raw.
            ret = ContentviewResult(
                text=raw.prettify(data, metadata),
                syntax_highlight=raw.syntax_highlight,
                view_name=raw.name,
                description=f"{enc}[failed to parse as {view.name}]",
            )
        else:
            # Cut the exception traceback for display.
            exc, value, tb = sys.exc_info()
            tb_cut = cut_traceback(tb, "prettify_message")
            if (
                tb_cut == tb
            ):  # If there are no extra frames, just skip displaying the traceback.
                tb_cut = None
            # If the contentview has been set explicitly, we display a hard error.
            err = "".join(traceback.format_exception(exc, value=value, tb=tb_cut))
            ret = ContentviewResult(
                text=f"Couldn't parse as {view.name}:\n{err}",
                syntax_highlight="error",
                view_name=view.name,
                description=enc,
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


# Legacy contentviews need to be registered explicitly.
_legacy_views = [
    graphql.ViewGraphQL,
    xml_html.ViewXmlHtml,
    wbxml.ViewWBXML,
    javascript.ViewJavaScript,
    urlencoded.ViewURLEncoded,
    multipart.ViewMultipart,
    image.ViewImage,
    query.ViewQuery,
    mqtt.ViewMQTT,
    dns.ViewDns,
    socketio.ViewSocketIO,
]
for ViewCls in _legacy_views:
    registry.register(LegacyContentview(ViewCls()))  # type: ignore[abstract]

_views: list[Contentview] = [
    json_view,
    raw,
    css,
    http3,
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
            stacklevel=2,
        )
        contentview = LegacyContentview(contentview)
    registry.register(contentview)


__all__ = [
    # Public Contentview API
    "Contentview",
    "InteractiveContentview",
    "SyntaxHighlight",
    "add",
    "Metadata",
]
