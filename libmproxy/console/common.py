import urwid
import urwid.util
from .. import utils


VIEW_BODY_RAW = 0
VIEW_BODY_HEX = 1
VIEW_BODY_PRETTY = 2

BODY_VIEWS = {
    VIEW_BODY_RAW: "raw",
    VIEW_BODY_HEX: "hex",
    VIEW_BODY_PRETTY: "pretty"
}

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
                    urwid.Text([(val, kv[1])])
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


def format_flow(f, focus, extended=False, padding=2):
    pile = []

    req = []
    if extended:
        req.append(
            fcol(
                utils.format_timestamp(f.request.timestamp),
                "highlight"
            )
        )
    else:
        req.append(fcol(">>" if focus else "  ", "focus"))
    if f.request.is_replay():
        req.append(fcol(SYMBOL_REPLAY, "replay"))
    req.append(fcol(f.request.method, "method"))

    preamble = sum(i[1] for i in req) + len(req) -1

    if f.intercepting and not f.request.acked:
        uc = "intercept"
    elif f.response or f.error:
        uc = "text"
    else:
        uc = "title"

    req.append(
        urwid.Text([(uc, f.request.get_url())])
    )

    pile.append(urwid.Columns(req, dividechars=1))

    resp = []
    resp.append(
        ("fixed", preamble, urwid.Text(""))
    )

    if f.response or f.error:
        resp.append(fcol(SYMBOL_RETURN, "method"))

    if f.response:
        if f.response.is_replay():
            resp.append(fcol(SYMBOL_REPLAY, "replay"))
        if f.response.code in [200, 304]:
            resp.append(fcol(f.response.code, "goodcode"))
        else:
            resp.append(fcol(f.response.code, "error"))

        if f.intercepting and f.response and not f.response.acked:
            rc = "intercept"
        else:
            rc = "text"

        t = f.response.headers["content-type"]
        if t:
            t = t[0].split(";")[0]
            resp.append(fcol(t, rc))
        if f.response.content:
            resp.append(fcol(utils.pretty_size(len(f.response.content)), rc))
        else:
            resp.append(fcol("[empty content]", rc))
    elif f.error:
        resp.append(
            urwid.Text([
                (
                    "error",
                    f.error.msg
                )
            ])
        )
    pile.append(urwid.Columns(resp, dividechars=1))
    return urwid.Pile(pile)


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


