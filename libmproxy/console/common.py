from __future__ import absolute_import
import urwid
import urwid.util
from .. import utils
from ..protocol.http import CONTENT_MISSING


VIEW_LIST = 0
VIEW_FLOW = 1


VIEW_FLOW_REQUEST = 0
VIEW_FLOW_RESPONSE = 1


def highlight_key(s, k):
    l = []
    parts = s.split(k, 1)
    if parts[0]:
        l.append(("text", parts[0]))
    l.append(("key", k))
    if parts[1]:
        l.append(("text", parts[1]))
    return l


KEY_MAX = 30
def format_keyvals(lst, key="key", val="text", indent=0):
    """
        Format a list of (key, value) tuples.

        If key is None, it's treated specially:
            - We assume a sub-value, and add an extra indent.
            - The value is treated as a pre-formatted list of directives.
    """
    ret = []
    if lst:
        maxk = min(max(len(i[0]) for i in lst if i and i[0]), KEY_MAX)
        for i, kv in enumerate(lst):
            if kv is None:
                ret.append(urwid.Text(""))
            else:
                cols = []
                # This cumbersome construction process is here for a reason:
                # Urwid < 1.0 barfs if given a fixed size column of size zero.
                if indent:
                    cols.append(("fixed", indent, urwid.Text("")))
                cols.extend([
                    (
                        "fixed",
                        maxk,
                        urwid.Text([(key, kv[0] or "")])
                    ),
                    kv[1] if isinstance(kv[1], urwid.Widget) else urwid.Text([(val, kv[1])])
               ])
                ret.append(urwid.Columns(cols, dividechars = 2))
    return ret


def shortcuts(k):
    if k == " ":
        k = "page down"
    elif k == "j":
        k = "down"
    elif k == "k":
        k = "up"
    return k


def fcol(s, attr):
    s = unicode(s)
    return (
        "fixed",
        len(s),
        urwid.Text(
            [
                (attr, s)
            ]
        )
    )

if urwid.util.detected_encoding:
    SYMBOL_REPLAY = u"\u21ba"
    SYMBOL_RETURN = u"\u2190"
else:
    SYMBOL_REPLAY = u"[r]"
    SYMBOL_RETURN = u"<-"



def raw_format_flow(f, focus, extended, padding):
    f = dict(f)

    pile = []
    req = []
    if extended:
        req.append(
            fcol(
                utils.format_timestamp(f["req_timestamp"]),
                "highlight"
            )
        )
    else:
        req.append(fcol(">>" if focus else "  ", "focus"))
    if f["req_is_replay"]:
        req.append(fcol(SYMBOL_REPLAY, "replay"))
    req.append(fcol(f["req_method"], "method"))

    preamble = sum(i[1] for i in req) + len(req) -1

    if f["intercepting"] and not f["acked"]:
        uc = "intercept"
    elif f["resp_code"] or f["err_msg"]:
        uc = "text"
    else:
        uc = "title"

    req.append(
        urwid.Text([(uc, f["req_url"])])
    )

    pile.append(urwid.Columns(req, dividechars=1))

    resp = []
    resp.append(
        ("fixed", preamble, urwid.Text(""))
    )

    if f["resp_code"]:
        codes = {
            2: "code_200",
            3: "code_300",
            4: "code_400",
            5: "code_500",
        }
        ccol = codes.get(f["resp_code"]/100, "code_other")
        resp.append(fcol(SYMBOL_RETURN, ccol))
        if f["resp_is_replay"]:
            resp.append(fcol(SYMBOL_REPLAY, "replay"))
        resp.append(fcol(f["resp_code"], ccol))
        if f["intercepting"] and f["resp_code"] and not f["acked"]:
            rc = "intercept"
        else:
            rc = "text"

        if f["resp_ctype"]:
            resp.append(fcol(f["resp_ctype"], rc))
        resp.append(fcol(f["resp_clen"], rc))
        resp.append(fcol(f["resp_rate"], rc))

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


class FlowCache:
    @utils.LRUCache(200)
    def format_flow(self, *args):
        return raw_format_flow(*args)
flowcache = FlowCache()


def format_flow(f, focus, extended=False, hostheader=False, padding=2):
    d = dict(
        intercepting = f.intercepting,
        acked = f.reply.acked,

        req_timestamp = f.request.timestamp_start,
        req_is_replay = f.request.is_replay,
        req_method = f.request.method,
        req_url = f.request.pretty_url(hostheader=hostheader),

        err_msg = f.error.msg if f.error else None,
        resp_code = f.response.code if f.response else None,
    )
    if f.response:
        if f.response.content:
            contentdesc = utils.pretty_size(len(f.response.content))
        elif f.response.content == CONTENT_MISSING:
            contentdesc = "[content missing]"
        else:
            contentdesc = "[no content]"

        if f.response.timestamp_end:
            delta = f.response.timestamp_end - f.response.timestamp_start
        else:
            delta = 0
        size = f.response.size()
        rate = utils.pretty_size(size / ( delta if delta > 0 else 1 ) )

        d.update(dict(
            resp_code = f.response.code,
            resp_is_replay = f.response.is_replay,
            resp_clen = contentdesc,
            resp_rate = "{0}/s".format(rate),
        ))
        t = f.response.headers["content-type"]
        if t:
            d["resp_ctype"] = t[0].split(";")[0]
        else:
            d["resp_ctype"] = ""
    return flowcache.format_flow(tuple(sorted(d.items())), focus, extended, padding)



def int_version(v):
    SIG = 3
    v = urwid.__version__.split("-")[0].split(".")
    x = 0
    for i in range(min(SIG, len(v))):
        x += int(v[i]) * 10**(SIG-i)
    return x


# We have to do this to be portable over 0.9.8 and 0.9.9 If compatibility
# becomes a pain to maintain, we'll just mandate 0.9.9 or newer.
class WWrap(urwid.WidgetWrap):
    if int_version(urwid.__version__) >= 990:
        def set_w(self, x):
            self._w = x
        def get_w(self):
            return self._w
        w = property(get_w, set_w)


