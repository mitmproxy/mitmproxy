import platform
import typing
from functools import lru_cache

import urwid
import urwid.util

from mitmproxy.utils import human

# Detect Windows Subsystem for Linux
IS_WSL = "Microsoft" in platform.platform()


def is_keypress(k):
    """
        Is this input event a keypress?
    """
    if isinstance(k, str):
        return True


def highlight_key(str, key, textattr="text", keyattr="key"):
    l = []
    parts = str.split(key, 1)
    if parts[0]:
        l.append((textattr, parts[0]))
    l.append((keyattr, key))
    if parts[1]:
        l.append((textattr, parts[1]))
    return l


KEY_MAX = 30


def format_keyvals(
        entries: typing.List[typing.Tuple[str, typing.Union[None, str, urwid.Widget]]],
        key_format: str = "key",
        value_format: str = "text",
        indent: int = 0
) -> typing.List[urwid.Columns]:
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
                    (
                        "fixed",
                        max_key_len,
                        urwid.Text([(key_format, k)])
                    ),
                    v
                ],
                dividechars=2
            )
        )
    return ret


def fcol(s, attr):
    s = str(s)
    return (
        "fixed",
        len(s),
        urwid.Text(
            [
                (attr, s)
            ]
        )
    )


if urwid.util.detected_encoding and not IS_WSL:
    SYMBOL_REPLAY = u"\u21ba"
    SYMBOL_RETURN = u"\u2190"
    SYMBOL_MARK = u"\u25cf"
    SYMBOL_UP = u"\u21E7"
    SYMBOL_DOWN = u"\u21E9"
else:
    SYMBOL_REPLAY = u"[r]"
    SYMBOL_RETURN = u"<-"
    SYMBOL_MARK = "[m]"
    SYMBOL_UP = "^"
    SYMBOL_DOWN = " "


@lru_cache(maxsize=800)
def raw_format_flow(f, flow):
    f = dict(f)
    pile = []
    req = []
    if f["extended"]:
        req.append(
            fcol(
                human.format_timestamp(f["req_timestamp"]),
                "highlight"
            )
        )
    else:
        req.append(fcol(">>" if f["focus"] else "  ", "focus"))

    if f["marked"]:
        req.append(fcol(SYMBOL_MARK, "mark"))

    if f["req_is_replay"]:
        req.append(fcol(SYMBOL_REPLAY, "replay"))

    pushed = ' PUSH_PROMISE' if 'h2-pushed-stream' in flow.metadata else ''
    req.append(fcol(f["req_method"] + pushed, "method"))

    preamble = sum(i[1] for i in req) + len(req) - 1

    if f["intercepted"] and not f["acked"]:
        uc = "intercept"
    elif "resp_code" in f or "err_msg" in f:
        uc = "text"
    else:
        uc = "title"

    url = f["req_url"]

    if f["max_url_len"] and len(url) > f["max_url_len"]:
        url = url[:f["max_url_len"]] + "…"

    if f["req_http_version"] not in ("HTTP/1.0", "HTTP/1.1"):
        url += " " + f["req_http_version"]
    req.append(
        urwid.Text([(uc, url)])
    )

    pile.append(urwid.Columns(req, dividechars=1))

    resp = []
    resp.append(
        ("fixed", preamble, urwid.Text(""))
    )

    if "resp_code" in f:
        codes = {
            2: "code_200",
            3: "code_300",
            4: "code_400",
            5: "code_500",
        }
        ccol = codes.get(f["resp_code"] // 100, "code_other")
        resp.append(fcol(SYMBOL_RETURN, ccol))
        if f["resp_is_replay"]:
            resp.append(fcol(SYMBOL_REPLAY, "replay"))
        resp.append(fcol(f["resp_code"], ccol))
        if f["extended"]:
            resp.append(fcol(f["resp_reason"], ccol))
        if f["intercepted"] and f["resp_code"] and not f["acked"]:
            rc = "intercept"
        else:
            rc = "text"

        if f["resp_ctype"]:
            resp.append(fcol(f["resp_ctype"], rc))
        resp.append(fcol(f["resp_clen"], rc))
        resp.append(fcol(f["roundtrip"], rc))

    elif f["err_msg"]:
        resp.append(fcol(SYMBOL_RETURN, "error"))
        resp.append(
            urwid.Text([
                (
                    "error",
                    f["err_msg"]
                )
            ])
        )
    pile.append(urwid.Columns(resp, dividechars=1))
    return urwid.Pile(pile)


def format_flow(f, focus, extended=False, hostheader=False, max_url_len=False):
    acked = False
    if f.reply and f.reply.state == "committed":
        acked = True
    d = dict(
        focus=focus,
        extended=extended,
        max_url_len=max_url_len,
        intercepted=f.intercepted,
        acked=acked,
        req_timestamp=f.request.timestamp_start,
        req_is_replay=f.request.is_replay,
        req_method=f.request.method,
        req_url=f.request.pretty_url if hostheader else f.request.url,
        req_http_version=f.request.http_version,
        err_msg=f.error.msg if f.error else None,
        marked=f.marked,
    )
    if f.response:
        if f.response.raw_content:
            contentdesc = human.pretty_size(len(f.response.raw_content))
        elif f.response.raw_content is None:
            contentdesc = "[content missing]"
        else:
            contentdesc = "[no content]"
        duration = 0
        if f.response.timestamp_end and f.request.timestamp_start:
            duration = f.response.timestamp_end - f.request.timestamp_start
        roundtrip = human.pretty_duration(duration)

        d.update(dict(
            resp_code=f.response.status_code,
            resp_reason=f.response.reason,
            resp_is_replay=f.response.is_replay,
            resp_clen=contentdesc,
            roundtrip=roundtrip,
        ))

        t = f.response.headers.get("content-type")
        if t:
            d["resp_ctype"] = t.split(";")[0]
        else:
            d["resp_ctype"] = ""

    return raw_format_flow(tuple(sorted(d.items())), f)
