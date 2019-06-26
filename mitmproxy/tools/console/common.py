import platform
import typing
from functools import lru_cache
from datetime import datetime

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
        index_format: str = "highlight",
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
    max_key_len = max((len(e[0]) for e in entries if e[0] is not None), default=0)
    max_key_len = min(max_key_len, KEY_MAX)

    if len(entries) > 0 and len(entries[0]) == 3:
        max_index_len = max_key_len
        max_key_len = max((len(e[1]) for e in entries if e[1] is not None), default=0)
        max_key_len = min(max_key_len, KEY_MAX)

    if indent > 2:
        indent -= 2  # We use dividechars=2 below, which already adds two empty spaces

    ret = []
    for e in entries:
        if len(e) == 3:
            i, k, v = e
        else:
            k, v = e
        if v is None:
            v = urwid.Text("")
        elif not isinstance(v, urwid.Widget):
            v = urwid.Text([(value_format, v)])
        line = [("fixed", indent, urwid.Text("")),
                (
                    "fixed",
                    max_key_len,
                    urwid.Text([(key_format, k)])
        ),
            v
        ]
        if len(e) == 3:
            line[0:0] = [((
                "fixed",
                max_index_len,
                urwid.Text([(index_format, i)])
            ))]
        ret.append(
            urwid.Columns(
                line,
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
    SYMBOL_DIRECTION = u"\u2192"
    SYMBOL_MARK = u"\u25cf"
    SYMBOL_UP = u"\u21E7"
    SYMBOL_DOWN = u"\u21E9"
else:
    SYMBOL_REPLAY = u"[r]"
    SYMBOL_RETURN = u"<-"
    SYMBOL_DIRECTION = u"->"
    SYMBOL_MARK = "[m]"
    SYMBOL_UP = "^"
    SYMBOL_DOWN = " "


@lru_cache(maxsize=800)
def raw_format_item(i):
    i = dict(i)
    pile = []
    req = []
    if i["extended"]:
        req.append(
            fcol(
                human.format_timestamp(i["req_timestamp"]),
                "highlight"
            )
        )
    else:
        req.append(fcol(">>" if i["focus"] else "  ", "focus"))

    if i["marked"]:
        req.append(fcol(SYMBOL_MARK, "mark"))

    if i["req_is_replay"]:
        req.append(fcol(SYMBOL_REPLAY, "replay"))

    req.append(fcol(i["req_method"], "method"))

    preamble = sum(i[1] for i in req) + len(req) - 1

    if i["intercepted"] and not i["acked"]:
        uc = "intercept"
    elif "resp_code" in i or "err_msg" in i:
        uc = "text"
    else:
        uc = "title"

    url = i["req_url"]

    if i["max_url_len"] and len(url) > i["max_url_len"]:
        url = url[:i["max_url_len"]] + "…"

    if i["req_http_version"] not in ("HTTP/1.0", "HTTP/1.1"):
        url += " " + i["req_http_version"]
    req.append(
        urwid.Text([(uc, url)])
    )

    pile.append(urwid.Columns(req, dividechars=1))

    resp = []
    resp.append(
        ("fixed", preamble, urwid.Text(""))
    )

    if "resp_code" in i:
        codes = {
            2: "code_200",
            3: "code_300",
            4: "code_400",
            5: "code_500",
        }
        ccol = codes.get(i["resp_code"] // 100, "code_other")
        resp.append(fcol(SYMBOL_RETURN, ccol))
        if i["resp_is_replay"]:
            resp.append(fcol(SYMBOL_REPLAY, "replay"))
        resp.append(fcol(i["resp_code"], ccol))
        if i["extended"]:
            resp.append(fcol(i["resp_reason"], ccol))
        if i["intercepted"] and i["resp_code"] and not i["acked"]:
            rc = "intercept"
        else:
            rc = "text"

        if i["resp_ctype"]:
            resp.append(fcol(i["resp_ctype"], rc))
        resp.append(fcol(i["resp_clen"], rc))
        resp.append(fcol(i["roundtrip"], rc))

    elif i["err_msg"]:
        resp.append(fcol(SYMBOL_RETURN, "error"))
        resp.append(
            urwid.Text([
                (
                    "error",
                    i["err_msg"]
                )
            ])
        )
    pile.append(urwid.Columns(resp, dividechars=1))
    return urwid.Pile(pile)


def format_item(i, focus, extended=False, hostheader=False, max_url_len=False):
    acked = False
    if i.reply and i.reply.state == "committed":
        acked = True
    pushed = ' PUSH_PROMISE' if 'h2-pushed-stream' in i.metadata else ''
    d = dict(
        focus=focus,
        extended=extended,
        max_url_len=max_url_len,
        intercepted=i.intercepted,
        acked=acked,
        req_timestamp=i.request.timestamp_start,
        req_is_replay=i.request.is_replay,
        req_method=i.request.method + pushed,
        req_url=i.request.pretty_url if hostheader else i.request.url,
        req_http_version=i.request.http_version,
        err_msg=i.error.msg if i.error else None,
        marked=i.marked,
    )
    if i.response:
        if i.response.raw_content:
            contentdesc = human.pretty_size(len(i.response.raw_content))
        elif i.response.raw_content is None:
            contentdesc = "[content missing]"
        else:
            contentdesc = "[no content]"
        duration = 0
        if i.response.timestamp_end and i.request.timestamp_start:
            duration = i.response.timestamp_end - i.request.timestamp_start
        roundtrip = human.pretty_duration(duration)

        d.update(dict(
            resp_code=i.response.status_code,
            resp_reason=i.response.reason,
            resp_is_replay=i.response.is_replay,
            resp_clen=contentdesc,
            roundtrip=roundtrip,
        ))

        t = i.response.headers.get("content-type")
        if t:
            d["resp_ctype"] = t.split(";")[0]
        else:
            d["resp_ctype"] = ""

    return raw_format_item(tuple(d.items()))


@lru_cache(maxsize=800)
def raw_format_http2_item(i):
    i = dict(i)
    pile = []
    l1 = []
    l2 = []

    l1.append(fcol(">>" if i["focus"] else "  ", "focus"))

    if i["marked"]:
        l1.append(fcol(SYMBOL_MARK, "mark"))

    space_l2 = sum(i[1] for i in l1) + len(l1) + 13

    l1.append(fcol(i['frame_type'], "frame_type"))

    space_l1 = space_l2 - sum(i[1] for i in l1) + len(l1) - 1

    l1.append(("fixed", space_l1, urwid.Text("")))

    space_l2 = sum(i[1] for i in l1) + len(l1) - 1

    l1.append(fcol(i['source_addr'], "text"))
    l1.append(fcol(SYMBOL_DIRECTION, "text"))
    l1.append(fcol(i['dest_addr'], "text"))

    l2.append(("fixed", space_l2, urwid.Text("")))
    l2.append(fcol("Stream ID: %s" % i['stream_id'], "stream_id"))
    l2.append(fcol("Timestamp: %s" % i['timestamp'], "text"))

    pile.append(urwid.Columns(l1, dividechars=1))
    pile.append(urwid.Columns(l2, dividechars=1))
    return urwid.Pile(pile)


def format_http2_item(i, focus):
    d = dict(
        focus=focus,
        marked=i.marked,
        timestamp=datetime.fromtimestamp(i.timestamp).isoformat(),
        frame_type=i.frame_type,
        stream_id=i.stream_id,
    )
    if i.from_client:
        d.update(source_addr=i.flow.client_conn.address[0],
                 dest_addr=i.flow.server_conn.address[0])
    else:
        d.update(source_addr=i.flow.server_conn.address[0],
                 dest_addr=i.flow.client_conn.address[0])

    return raw_format_http2_item(tuple(sorted(d.items())))
