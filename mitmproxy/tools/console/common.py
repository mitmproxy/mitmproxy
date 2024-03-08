import enum
import math
import platform
from collections.abc import Iterable
from functools import lru_cache

import urwid.util
from publicsuffix2 import get_sld
from publicsuffix2 import get_tld

from mitmproxy import dns
from mitmproxy import flow
from mitmproxy.dns import DNSFlow
from mitmproxy.http import HTTPFlow
from mitmproxy.tcp import TCPFlow
from mitmproxy.udp import UDPFlow
from mitmproxy.utils import emoji
from mitmproxy.utils import human

# Detect Windows Subsystem for Linux and Windows
IS_WINDOWS_OR_WSL = (
    "Microsoft" in platform.platform() or "Windows" in platform.platform()
)


def is_keypress(k):
    """
    Is this input event a keypress?
    """
    if isinstance(k, str):
        return True


def highlight_key(text, key, textattr="text", keyattr="key"):
    lst = []
    parts = text.split(key, 1)
    if parts[0]:
        lst.append((textattr, parts[0]))
    lst.append((keyattr, key))
    if parts[1]:
        lst.append((textattr, parts[1]))
    return lst


KEY_MAX = 30


def format_keyvals(
    entries: Iterable[tuple[str, None | str | urwid.Widget]],
    key_format: str = "key",
    value_format: str = "text",
    indent: int = 0,
) -> list[urwid.Columns]:
    """
    Format a list of (key, value) tuples.

    Args:
        entries: The list to format. keys must be strings, values can also be None or urwid widgets.
            The latter makes it possible to use the result of format_keyvals() as a value.
        key_format: The display attribute for the key.
        value_format: The display attribute for the value.
        indent: Additional indent to apply.
    """
    max_key_len = max((len(k) for k, v in entries if k is not None), default=0)
    max_key_len = min(max_key_len, KEY_MAX)

    if indent > 2:
        indent -= 2  # We use dividechars=2 below, which already adds two empty spaces

    ret = []
    for k, v in entries:
        if v is None:
            v = urwid.Text("")
        elif not isinstance(v, urwid.Widget):
            v = urwid.Text([(value_format, v)])
        ret.append(
            urwid.Columns(
                [
                    ("fixed", indent, urwid.Text("")),
                    ("fixed", max_key_len, urwid.Text([(key_format, k)])),
                    v,
                ],
                dividechars=2,
            )
        )
    return ret


def fcol(s: str, attr: str) -> tuple[str, int, urwid.Text]:
    s = str(s)
    return ("fixed", len(s), urwid.Text([(attr, s)]))


if urwid.util.detected_encoding:
    SYMBOL_REPLAY = "\u21ba"
    SYMBOL_RETURN = "\u2190"
    SYMBOL_MARK = "\u25cf"
    SYMBOL_UP = "\u21e7"
    SYMBOL_DOWN = "\u21e9"
    SYMBOL_ELLIPSIS = "\u2026"
    SYMBOL_FROM_CLIENT = "\u21d2"
    SYMBOL_TO_CLIENT = "\u21d0"
else:
    SYMBOL_REPLAY = "[r]"
    SYMBOL_RETURN = "<-"
    SYMBOL_MARK = "#"
    SYMBOL_UP = "^"
    SYMBOL_DOWN = " "
    SYMBOL_ELLIPSIS = "~"
    SYMBOL_FROM_CLIENT = "->"
    SYMBOL_TO_CLIENT = "<-"

SCHEME_STYLES = {
    "http": "scheme_http",
    "https": "scheme_https",
    "ws": "scheme_ws",
    "wss": "scheme_wss",
    "tcp": "scheme_tcp",
    "udp": "scheme_udp",
    "dns": "scheme_dns",
    "quic": "scheme_quic",
}
HTTP_REQUEST_METHOD_STYLES = {
    "GET": "method_get",
    "POST": "method_post",
    "DELETE": "method_delete",
    "HEAD": "method_head",
    "PUT": "method_put",
}
HTTP_RESPONSE_CODE_STYLE = {
    2: "code_200",
    3: "code_300",
    4: "code_400",
    5: "code_500",
}


class RenderMode(enum.Enum):
    TABLE = 1
    """The flow list in table format, i.e. one row per flow."""
    LIST = 2
    """The flow list in list format, i.e. potentially multiple rows per flow."""
    DETAILVIEW = 3
    """The top lines in the detail view."""


def fixlen(s: str, maxlen: int) -> str:
    if len(s) <= maxlen:
        return s.ljust(maxlen)
    else:
        return s[0 : maxlen - len(SYMBOL_ELLIPSIS)] + SYMBOL_ELLIPSIS


def fixlen_r(s: str, maxlen: int) -> str:
    if len(s) <= maxlen:
        return s.rjust(maxlen)
    else:
        return SYMBOL_ELLIPSIS + s[len(s) - maxlen + len(SYMBOL_ELLIPSIS) :]


def render_marker(marker: str) -> str:
    rendered = emoji.emoji.get(marker, SYMBOL_MARK)

    # The marker can only be one glyph. Some emoji that use zero-width joiners (ZWJ)
    # will not be rendered as a single glyph and instead will show
    # multiple glyphs. Just use the first glyph as a fallback.
    # https://emojipedia.org/emoji-zwj-sequence/
    return rendered[0]


class TruncatedText(urwid.Widget):
    def __init__(self, text, attr, align="left"):
        self.text = text
        self.attr = attr
        self.align = align
        super().__init__()

    def pack(self, size, focus=False):
        return (len(self.text), 1)

    def rows(self, size, focus=False):
        return 1

    def render(self, size, focus=False):
        text = self.text
        attr = self.attr
        if self.align == "right":
            text = text[::-1]
            attr = attr[::-1]

        text_len = urwid.util.calc_width(text, 0, len(text))
        if size is not None and len(size) > 0:
            width = size[0]
        else:
            width = text_len

        if width >= text_len:
            remaining = width - text_len
            if remaining > 0:
                c_text = text + " " * remaining
                c_attr = attr + [("text", remaining)]
            else:
                c_text = text
                c_attr = attr
        else:
            trim = urwid.util.calc_trim_text(text, 0, width - 1, 0, width - 1)
            visible_text = text[0 : trim[1]]
            if trim[3] == 1:
                visible_text += " "
            c_text = visible_text + SYMBOL_ELLIPSIS
            c_attr = urwid.util.rle_subseg(attr, 0, len(visible_text.encode())) + [
                ("focus", len(SYMBOL_ELLIPSIS.encode()))
            ]

        if self.align == "right":
            c_text = c_text[::-1]
            c_attr = c_attr[::-1]

        return urwid.TextCanvas([c_text.encode()], [c_attr], maxcol=width)


def truncated_plain(text, attr, align="left"):
    return TruncatedText(text, [(attr, len(text.encode()))], align)


# Work around https://github.com/urwid/urwid/pull/330
def rle_append_beginning_modify(rle, a_r):
    """
    Append (a, r) (unpacked from *a_r*) to BEGINNING of rle.
    Merge with first run when possible

    MODIFIES rle parameter contents. Returns None.
    """
    a, r = a_r
    if not rle:
        rle[:] = [(a, r)]
    else:
        al, run = rle[0]
        if a == al:
            rle[0] = (a, run + r)
        else:
            rle[0:0] = [(a, r)]


def colorize_host(host: str):
    tld = get_tld(host)
    sld = get_sld(host)

    attr: list = []

    tld_size = len(tld)
    sld_size = len(sld) - tld_size

    for letter in reversed(range(len(host))):
        character = host[letter]
        if tld_size > 0:
            style = "url_domain"
            tld_size -= 1
        elif tld_size == 0:
            style = "text"
            tld_size -= 1
        elif sld_size > 0:
            sld_size -= 1
            style = "url_extension"
        else:
            style = "text"
        rle_append_beginning_modify(attr, (style, len(character.encode())))
    return attr


def colorize_req(s: str):
    path = s.split("?", 2)[0]
    i_query = len(path)
    i_last_slash = path.rfind("/")
    i_ext = path[i_last_slash + 1 :].rfind(".")
    i_ext = i_last_slash + i_ext if i_ext >= 0 else len(s)
    in_val = False
    attr: list = []
    for i in range(len(s)):
        c = s[i]
        if (
            (i < i_query and c == "/")
            or (i < i_query and i > i_last_slash and c == ".")
            or (i == i_query)
        ):
            a = "url_punctuation"
        elif i > i_query:
            if in_val:
                if c == "&":
                    in_val = False
                    a = "url_punctuation"
                else:
                    a = "url_query_value"
            else:
                if c == "=":
                    in_val = True
                    a = "url_punctuation"
                else:
                    a = "url_query_key"
        elif i > i_ext:
            a = "url_extension"
        elif i > i_last_slash:
            a = "url_filename"
        else:
            a = "text"
        urwid.util.rle_append_modify(attr, (a, len(c.encode())))
    return attr


def colorize_url(url):
    parts = url.split("/", 3)
    if len(parts) < 4 or len(parts[1]) > 0 or parts[0][-1:] != ":":
        return [("error", len(url))]  # bad URL
    return (
        [
            (SCHEME_STYLES.get(parts[0], "scheme_other"), len(parts[0]) - 1),
            ("url_punctuation", 3),  # ://
        ]
        + colorize_host(parts[2])
        + colorize_req("/" + parts[3])
    )


def format_http_content_type(content_type: str) -> tuple[str, str]:
    content_type = content_type.split(";")[0]
    if content_type.endswith("/javascript"):
        style = "content_script"
    elif content_type.startswith("text/"):
        style = "content_text"
    elif (
        content_type.startswith("image/")
        or content_type.startswith("video/")
        or content_type.startswith("font/")
        or "/x-font-" in content_type
    ):
        style = "content_media"
    elif content_type.endswith("/json") or content_type.endswith("/xml"):
        style = "content_data"
    elif content_type.startswith("application/"):
        style = "content_raw"
    else:
        style = "content_other"
    return content_type, style


def format_duration(duration: float) -> tuple[str, str]:
    pretty_duration = human.pretty_duration(duration)
    style = "gradient_%02d" % int(
        99 - 100 * min(math.log2(1 + 1000 * duration) / 12, 0.99)
    )
    return pretty_duration, style


def format_size(num_bytes: int) -> tuple[str, str]:
    pretty_size = human.pretty_size(num_bytes)
    style = "gradient_%02d" % int(99 - 100 * min(math.log2(1 + num_bytes) / 20, 0.99))
    return pretty_size, style


def format_left_indicators(*, focused: bool, intercepted: bool, timestamp: float):
    indicators: list[str | tuple[str, str]] = []
    if focused:
        indicators.append(("focus", ">>"))
    else:
        indicators.append("  ")
    pretty_timestamp = human.format_timestamp(timestamp)[-8:]
    if intercepted:
        indicators.append(("intercept", pretty_timestamp))
    else:
        indicators.append(("text", pretty_timestamp))
    return "fixed", 10, urwid.Text(indicators)


def format_right_indicators(
    *,
    replay: bool,
    marked: str,
):
    indicators: list[str | tuple[str, str]] = []
    if replay:
        indicators.append(("replay", SYMBOL_REPLAY))
    else:
        indicators.append(" ")
    if bool(marked):
        indicators.append(("mark", render_marker(marked)))
    else:
        indicators.append("  ")
    return "fixed", 3, urwid.Text(indicators)


@lru_cache(maxsize=800)
def format_http_flow_list(
    *,
    render_mode: RenderMode,
    focused: bool,
    marked: str,
    is_replay: bool,
    request_method: str,
    request_scheme: str,
    request_host: str,
    request_path: str,
    request_url: str,
    request_http_version: str,
    request_timestamp: float,
    request_is_push_promise: bool,
    intercepted: bool,
    response_code: int | None,
    response_reason: str | None,
    response_content_length: int | None,
    response_content_type: str | None,
    duration: float | None,
    error_message: str | None,
) -> urwid.Widget:
    req = []

    if render_mode is RenderMode.DETAILVIEW:
        req.append(fcol(human.format_timestamp(request_timestamp), "highlight"))
    else:
        if focused:
            req.append(fcol(">>", "focus"))
        else:
            req.append(fcol("  ", "focus"))

    method_style = HTTP_REQUEST_METHOD_STYLES.get(request_method, "method_other")
    req.append(fcol(request_method, method_style))

    if request_is_push_promise:
        req.append(fcol("PUSH_PROMISE", "method_http2_push"))

    preamble_len = sum(x[1] for x in req) + len(req) - 1

    if request_http_version not in ("HTTP/1.0", "HTTP/1.1"):
        request_url += " " + request_http_version
    if intercepted and not response_code:
        url_style = "intercept"
    elif response_code or error_message:
        url_style = "text"
    else:
        url_style = "title"

    if render_mode is RenderMode.DETAILVIEW:
        req.append(urwid.Text([(url_style, request_url)]))
    else:
        req.append(truncated_plain(request_url, url_style))

    req.append(format_right_indicators(replay=is_replay, marked=marked))

    resp = [("fixed", preamble_len, urwid.Text(""))]
    if response_code:
        if intercepted:
            style = "intercept"
        else:
            style = ""

        status_style = style or HTTP_RESPONSE_CODE_STYLE.get(
            response_code // 100, "code_other"
        )
        resp.append(fcol(SYMBOL_RETURN, status_style))
        resp.append(fcol(str(response_code), status_style))
        if response_reason and render_mode is RenderMode.DETAILVIEW:
            resp.append(fcol(response_reason, status_style))

        if response_content_type:
            ct, ct_style = format_http_content_type(response_content_type)
            resp.append(fcol(ct, style or ct_style))

        if response_content_length:
            size, size_style = format_size(response_content_length)
        elif response_content_length == 0:
            size = "[no content]"
            size_style = "text"
        else:
            size = "[content missing]"
            size_style = "text"
        resp.append(fcol(size, style or size_style))

        if duration:
            dur, dur_style = format_duration(duration)
            resp.append(fcol(dur, style or dur_style))
    elif error_message:
        resp.append(fcol(SYMBOL_RETURN, "error"))
        resp.append(urwid.Text([("error", error_message)]))

    return urwid.Pile(
        [urwid.Columns(req, dividechars=1), urwid.Columns(resp, dividechars=1)]
    )


@lru_cache(maxsize=800)
def format_http_flow_table(
    *,
    render_mode: RenderMode,
    focused: bool,
    marked: str,
    is_replay: str | None,
    request_method: str,
    request_scheme: str,
    request_host: str,
    request_path: str,
    request_url: str,
    request_http_version: str,
    request_timestamp: float,
    request_is_push_promise: bool,
    intercepted: bool,
    response_code: int | None,
    response_reason: str | None,
    response_content_length: int | None,
    response_content_type: str | None,
    duration: float | None,
    error_message: str | None,
) -> urwid.Widget:
    items = [
        format_left_indicators(
            focused=focused, intercepted=intercepted, timestamp=request_timestamp
        )
    ]

    if intercepted and not response_code:
        request_style = "intercept"
    else:
        request_style = ""

    scheme_style = request_style or SCHEME_STYLES.get(request_scheme, "scheme_other")
    items.append(fcol(fixlen(request_scheme.upper(), 5), scheme_style))

    if request_is_push_promise:
        method_style = "method_http2_push"
    else:
        method_style = request_style or HTTP_REQUEST_METHOD_STYLES.get(
            request_method, "method_other"
        )
    items.append(fcol(fixlen(request_method, 4), method_style))

    items.append(
        (
            "weight",
            0.25,
            TruncatedText(request_host, colorize_host(request_host), "right"),
        )
    )
    items.append(
        ("weight", 1.0, TruncatedText(request_path, colorize_req(request_path), "left"))
    )

    if intercepted and response_code:
        response_style = "intercept"
    else:
        response_style = ""

    if response_code:
        status = str(response_code)
        status_style = response_style or HTTP_RESPONSE_CODE_STYLE.get(
            response_code // 100, "code_other"
        )

        if response_content_length and response_content_type:
            content, content_style = format_http_content_type(response_content_type)
            content_style = response_style or content_style
        elif response_content_length:
            content = ""
            content_style = "content_none"
        elif response_content_length == 0:
            content = "[no content]"
            content_style = "content_none"
        else:
            content = "[content missing]"
            content_style = "content_none"

    elif error_message:
        status = "err"
        status_style = "error"
        content = error_message
        content_style = "error"

    else:
        status = ""
        status_style = "text"
        content = ""
        content_style = ""

    items.append(fcol(fixlen(status, 3), status_style))
    items.append(("weight", 0.15, truncated_plain(content, content_style, "right")))

    if response_content_length:
        size, size_style = format_size(response_content_length)
        items.append(fcol(fixlen_r(size, 5), response_style or size_style))
    else:
        items.append(("fixed", 5, urwid.Text("")))

    if duration:
        duration_pretty, duration_style = format_duration(duration)
        items.append(
            fcol(fixlen_r(duration_pretty, 5), response_style or duration_style)
        )
    else:
        items.append(("fixed", 5, urwid.Text("")))

    items.append(
        format_right_indicators(
            replay=bool(is_replay),
            marked=marked,
        )
    )
    return urwid.Columns(items, dividechars=1, min_width=15)


@lru_cache(maxsize=800)
def format_message_flow(
    *,
    render_mode: RenderMode,
    focused: bool,
    timestamp_start: float,
    marked: str,
    protocol: str,
    client_address,
    server_address,
    total_size: int,
    duration: float | None,
    error_message: str | None,
):
    conn = f"{human.format_address(client_address)} <-> {human.format_address(server_address)}"

    items = []

    if render_mode in (RenderMode.TABLE, RenderMode.DETAILVIEW):
        items.append(
            format_left_indicators(
                focused=focused, intercepted=False, timestamp=timestamp_start
            )
        )
    else:
        if focused:
            items.append(fcol(">>", "focus"))
        else:
            items.append(fcol("  ", "focus"))

    if render_mode is RenderMode.TABLE:
        items.append(fcol(fixlen(protocol.upper(), 5), SCHEME_STYLES[protocol]))
    else:
        items.append(fcol(protocol.upper(), SCHEME_STYLES[protocol]))

    items.append(("weight", 1.0, truncated_plain(conn, "text", "left")))
    if error_message:
        items.append(("weight", 1.0, truncated_plain(error_message, "error", "left")))

    if total_size:
        size, size_style = format_size(total_size)
        items.append(fcol(fixlen_r(size, 5), size_style))
    else:
        items.append(("fixed", 5, urwid.Text("")))

    if duration:
        duration_pretty, duration_style = format_duration(duration)
        items.append(fcol(fixlen_r(duration_pretty, 5), duration_style))
    else:
        items.append(("fixed", 5, urwid.Text("")))

    items.append(format_right_indicators(replay=False, marked=marked))

    return urwid.Pile([urwid.Columns(items, dividechars=1, min_width=15)])


@lru_cache(maxsize=800)
def format_dns_flow(
    *,
    render_mode: RenderMode,
    focused: bool,
    intercepted: bool,
    marked: str,
    is_replay: str | None,
    op_code: str,
    request_timestamp: float,
    domain: str,
    type: str,
    response_code: str | None,
    response_code_http_equiv: int,
    answer: str | None,
    error_message: str,
    duration: float | None,
):
    items = []

    if render_mode in (RenderMode.TABLE, RenderMode.DETAILVIEW):
        items.append(
            format_left_indicators(
                focused=focused, intercepted=intercepted, timestamp=request_timestamp
            )
        )
    else:
        items.append(fcol(">>" if focused else "  ", "focus"))

    scheme_style = "intercepted" if intercepted else SCHEME_STYLES["dns"]
    t = f"DNS {op_code}"
    if render_mode is RenderMode.TABLE:
        t = fixlen(t, 10)
    items.append(fcol(t, scheme_style))
    items.append(("weight", 0.5, TruncatedText(domain, colorize_host(domain), "right")))
    items.append(fcol("(" + fixlen(type, 5)[: len(type)] + ") =", "text"))

    items.append(
        (
            "weight",
            1,
            (
                truncated_plain(
                    "..." if answer is None else "?" if not answer else answer, "text"
                )
                if error_message is None
                else truncated_plain(error_message, "error")
            ),
        )
    )
    status_style = (
        "intercepted"
        if intercepted
        else HTTP_RESPONSE_CODE_STYLE.get(response_code_http_equiv // 100, "code_other")
    )
    items.append(
        fcol(fixlen("" if response_code is None else response_code, 9), status_style)
    )

    if duration:
        duration_pretty, duration_style = format_duration(duration)
        items.append(fcol(fixlen_r(duration_pretty, 5), duration_style))
    else:
        items.append(("fixed", 5, urwid.Text("")))

    items.append(
        format_right_indicators(
            replay=bool(is_replay),
            marked=marked,
        )
    )
    return urwid.Pile([urwid.Columns(items, dividechars=1, min_width=15)])


def format_flow(
    f: flow.Flow,
    *,
    render_mode: RenderMode,
    hostheader: bool = False,  # pass options directly if we need more stuff from them
    focused: bool = True,
) -> urwid.Widget:
    """
    This functions calls the proper renderer depending on the flow type.
    We also want to cache the renderer output, so we extract all attributes
    relevant for display and call the render with only that. This assures that rows
    are updated if the flow is changed.
    """
    duration: float | None
    error_message: str | None
    if f.error:
        error_message = f.error.msg
    else:
        error_message = None

    if isinstance(f, (TCPFlow, UDPFlow)):
        total_size = 0
        for message in f.messages:
            total_size += len(message.content)
        if f.messages:
            duration = f.messages[-1].timestamp - f.client_conn.timestamp_start
        else:
            duration = None
        if f.client_conn.tls_version == "QUIC":
            protocol = "quic"
        else:
            protocol = f.type
        return format_message_flow(
            render_mode=render_mode,
            focused=focused,
            timestamp_start=f.client_conn.timestamp_start,
            marked=f.marked,
            protocol=protocol,
            client_address=f.client_conn.peername,
            server_address=f.server_conn.address,
            total_size=total_size,
            duration=duration,
            error_message=error_message,
        )
    elif isinstance(f, DNSFlow):
        if f.response:
            duration = f.response.timestamp - f.request.timestamp
            response_code_str: str | None = dns.response_codes.to_str(
                f.response.response_code
            )
            response_code_http_equiv = dns.response_codes.http_equiv_status_code(
                f.response.response_code
            )
            answer = ", ".join(str(x) for x in f.response.answers)
        else:
            duration = None
            response_code_str = None
            response_code_http_equiv = 0
            answer = None
        return format_dns_flow(
            render_mode=render_mode,
            focused=focused,
            intercepted=f.intercepted,
            marked=f.marked,
            is_replay=f.is_replay,
            op_code=dns.op_codes.to_str(f.request.op_code),
            request_timestamp=f.request.timestamp,
            domain=f.request.questions[0].name if f.request.questions else "",
            type=dns.types.to_str(f.request.questions[0].type)
            if f.request.questions
            else "",
            response_code=response_code_str,
            response_code_http_equiv=response_code_http_equiv,
            answer=answer,
            error_message=error_message,
            duration=duration,
        )
    elif isinstance(f, HTTPFlow):
        intercepted = f.intercepted
        response_content_length: int | None
        if f.response:
            if f.response.raw_content is not None:
                response_content_length = len(f.response.raw_content)
            else:
                response_content_length = None
            response_code: int | None = f.response.status_code
            response_reason: str | None = f.response.reason
            response_content_type = f.response.headers.get("content-type")
            if f.response.timestamp_end:
                duration = max(
                    [f.response.timestamp_end - f.request.timestamp_start, 0]
                )
            else:
                duration = None
        else:
            response_content_length = None
            response_code = None
            response_reason = None
            response_content_type = None
            duration = None

        scheme = f.request.scheme
        if f.websocket is not None:
            if scheme == "https":
                scheme = "wss"
            elif scheme == "http":
                scheme = "ws"

        if render_mode in (RenderMode.LIST, RenderMode.DETAILVIEW):
            render_func = format_http_flow_list
        else:
            render_func = format_http_flow_table
        return render_func(
            render_mode=render_mode,
            focused=focused,
            marked=f.marked,
            is_replay=f.is_replay,
            request_method=f.request.method,
            request_scheme=scheme,
            request_host=f.request.pretty_host if hostheader else f.request.host,
            request_path=f.request.path,
            request_url=f.request.pretty_url if hostheader else f.request.url,
            request_http_version=f.request.http_version,
            request_timestamp=f.request.timestamp_start,
            request_is_push_promise="h2-pushed-stream" in f.metadata,
            intercepted=intercepted,
            response_code=response_code,
            response_reason=response_reason,
            response_content_length=response_content_length,
            response_content_type=response_content_type,
            duration=duration,
            error_message=error_message,
        )

    else:
        raise NotImplementedError()
