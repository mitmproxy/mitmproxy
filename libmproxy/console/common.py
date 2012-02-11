import urwid
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
                ret.append(Text(""))
            else:
                ret.append(
                    urwid.Columns(
                        [
                            ("fixed", indent, urwid.Text("")),
                            (
                                "fixed",
                                maxk,
                                urwid.Text([(key, kv[0] or "")])
                            ),
                            urwid.Text([(val, kv[1])])
                        ],
                        dividechars = 2
                    )
                )
    return ret


def shortcuts(k):
    if k == " ":
        k = "page down"
    elif k == "j":
        k = "down"
    elif k == "k":
        k = "up"
    return k


def format_flow(f, focus, extended=False, padding=2):
    txt = []
    if extended:
        txt.append(("highlight", utils.format_timestamp(f.request.timestamp)))
    txt.append(" ")
    if f.request.is_replay():
        txt.append(("method", "[replay]"))
    txt.extend([
        ("ack", "!") if f.intercepting and not f.request.acked else " ",
        ("method", f.request.method),
        " ",
        (
            "text" if (f.response or f.error) else "title",
            f.request.get_url(),
        ),
    ])
    if f.response or f.error or f.request.is_replay():
        tsr = f.response or f.error
        if extended and tsr:
            ts = ("highlight", utils.format_timestamp(tsr.timestamp) + " ")
        else:
            ts = " "

        txt.append("\n")
        txt.append(("text", ts))
        txt.append(" "*(padding+2))

    if f.response:
        txt.append(
           ("ack", "!") if f.intercepting and not f.response.acked else " "
        )
        txt.append("<- ")
        if f.response.is_replay():
            txt.append(("method", "[replay] "))
        if f.response.code in [200, 304]:
            txt.append(("goodcode", str(f.response.code)))
        else:
            txt.append(("error", str(f.response.code)))
        t = f.response.headers["content-type"]
        if t:
            t = t[0].split(";")[0]
            txt.append(("text", " %s"%t))
        if f.response.content:
            txt.append(", %s"%utils.pretty_size(len(f.response.content)))
    elif f.error:
        txt.append(
           ("error", f.error.msg)
        )

    if focus:
        txt.insert(0, ("focus", ">>" + " "*(padding-2)))
    else:
        txt.insert(0, " "*padding)
    return txt


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


