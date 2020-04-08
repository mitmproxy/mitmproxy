import platform
import typing
import datetime
import time
import math
from functools import lru_cache
from publicsuffix2 import get_sld, get_tld

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
        entries: typing.Iterable[typing.Tuple[str, typing.Union[None, str, urwid.Widget]]],
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


if urwid.util.detected_encoding:
    SYMBOL_REPLAY = u"\u21ba"
    SYMBOL_RETURN = u"\u2190"
    SYMBOL_MARK = u"\u25cf"
    SYMBOL_UP = u"\u21E7"
    SYMBOL_DOWN = u"\u21E9"
    SYMBOL_ELLIPSIS = u"\u2026"
else:
    SYMBOL_REPLAY = u"[r]"
    SYMBOL_RETURN = u"<-"
    SYMBOL_MARK = "[m]"
    SYMBOL_UP = "^"
    SYMBOL_DOWN = " "
    SYMBOL_ELLIPSIS = "~"


def fixlen(s, maxlen):
    if len(s) <= maxlen:
        return s.ljust(maxlen)
    else:
        return s[0:maxlen - len(SYMBOL_ELLIPSIS)] + SYMBOL_ELLIPSIS


def fixlen_r(s, maxlen):
    if len(s) <= maxlen:
        return s.rjust(maxlen)
    else:
        return SYMBOL_ELLIPSIS + s[len(s) - maxlen + len(SYMBOL_ELLIPSIS):]


class TruncatedText(urwid.Widget):
    def __init__(self, text, attr, align='left'):
        self.text = text
        self.attr = attr
        self.align = align
        super(TruncatedText, self).__init__()

    def pack(self, size, focus=False):
        return (len(self.text), 1)

    def rows(self, size, focus=False):
        return 1

    def render(self, size, focus=False):
        text = self.text
        attr = self.attr
        if self.align == 'right':
            text = text[::-1]
            attr = attr[::-1]

        text_len = len(text)  # TODO: unicode?
        if size is not None and len(size) > 0:
            width = size[0]
        else:
            width = text_len

        if width >= text_len:
            remaining = width - text_len
            if remaining > 0:
                c_text = text + ' ' * remaining
                c_attr = attr + [('text', remaining)]
            else:
                c_text = text
                c_attr = attr
        else:
            visible_len = width - len(SYMBOL_ELLIPSIS)
            visible_text = text[0:visible_len]
            c_text = visible_text + SYMBOL_ELLIPSIS
            c_attr = (urwid.util.rle_subseg(attr, 0, len(visible_text.encode())) +
                      [('focus', len(SYMBOL_ELLIPSIS.encode()))])

        if self.align == 'right':
            c_text = c_text[::-1]
            c_attr = c_attr[::-1]

        return urwid.TextCanvas([c_text.encode()], [c_attr], maxcol=width)


def truncated_plain(text, attr, align='left'):
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


def colorize_host(host):
    tld = get_tld(host)
    sld = get_sld(host)

    attr = []

    tld_size = len(tld)
    sld_size = len(sld) - tld_size

    for letter in reversed(range(len(host))):
        character = host[letter]
        if tld_size > 0:
            style = 'url_domain'
            tld_size -= 1
        elif tld_size == 0:
            style = 'text'
            tld_size -= 1
        elif sld_size > 0:
            sld_size -= 1
            style = 'url_extension'
        else:
            style = 'text'
        rle_append_beginning_modify(attr, (style, len(character.encode())))
    return attr


def colorize_req(s):
    path = s.split('?', 2)[0]
    i_query = len(path)
    i_last_slash = path.rfind('/')
    i_ext = path[i_last_slash + 1:].rfind('.')
    i_ext = i_last_slash + i_ext if i_ext >= 0 else len(s)
    in_val = False
    attr = []
    for i in range(len(s)):
        c = s[i]
        if ((i < i_query and c == '/') or
            (i < i_query and i > i_last_slash and c == '.') or
           (i == i_query)):
            a = 'url_punctuation'
        elif i > i_query:
            if in_val:
                if c == '&':
                    in_val = False
                    a = 'url_punctuation'
                else:
                    a = 'url_query_value'
            else:
                if c == '=':
                    in_val = True
                    a = 'url_punctuation'
                else:
                    a = 'url_query_key'
        elif i > i_ext:
            a = 'url_extension'
        elif i > i_last_slash:
            a = 'url_filename'
        else:
            a = 'text'
        urwid.util.rle_append_modify(attr, (a, len(c.encode())))
    return attr


def colorize_url(url):
    parts = url.split('/', 3)
    if len(parts) < 4 or len(parts[1]) > 0 or parts[0][-1:] != ':':
        return [('error', len(url))]  # bad URL
    schemes = {
        'http:': 'scheme_http',
        'https:': 'scheme_https',
    }
    return [
        (schemes.get(parts[0], "scheme_other"), len(parts[0]) - 1),
        ('url_punctuation', 3),  # ://
    ] + colorize_host(parts[2]) + colorize_req('/' + parts[3])


@lru_cache(maxsize=800)
def raw_format_list(f):
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

    req.append(fcol(f["req_method"], "method"))

    preamble = sum(i[1] for i in req) + len(req) - 1

    if f["intercepted"] and not f["acked"]:
        uc = "intercept"
    elif "resp_code" in f or "err_msg" in f:
        uc = "text"
    else:
        uc = "title"

    url = f["req_url"]

    if f["cols"] and len(url) > f["cols"]:
        url = url[:f["cols"]] + "…"

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
        pretty_duration = human.pretty_duration(f["duration"])
        resp.append(fcol(pretty_duration, rc))

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


@lru_cache(maxsize=800)
def raw_format_table(f):
    f = dict(f)
    pile = []
    req = []

    cursor = [' ', 'focus']
    if f['focus']:
        cursor[0] = '>'
    req.append(fcol(*cursor))

    if f.get('resp_is_replay', False) or f.get('req_is_replay', False):
        req.append(fcol(SYMBOL_REPLAY, 'replay'))
    if f['marked']:
        req.append(fcol(SYMBOL_MARK, 'mark'))

    if f["two_line"]:
        req.append(TruncatedText(f["req_url"], colorize_url(f["req_url"]), 'left'))
        pile.append(urwid.Columns(req, dividechars=1))

        req = []
        req.append(fcol('  ', 'text'))

    if f["intercepted"] and not f["acked"]:
        uc = "intercept"
    elif "resp_code" in f or f["err_msg"] is not None:
        uc = "highlight"
    else:
        uc = "title"

    if f["extended"]:
        s = human.format_timestamp(f["req_timestamp"])
    else:
        s = datetime.datetime.fromtimestamp(time.mktime(time.localtime(f["req_timestamp"]))).strftime("%H:%M:%S")
    req.append(fcol(s, uc))

    methods = {
        'GET': 'method_get',
        'POST': 'method_post',
        'DELETE': 'method_delete',
        'HEAD': 'method_head',
        'PUT': 'method_put'
    }
    uc = methods.get(f["req_method"], "method_other")
    if f['extended']:
        req.append(fcol(f["req_method"], uc))
        if f["req_promise"]:
            req.append(fcol('PUSH_PROMISE', 'method_http2_push'))
    else:
        if f["req_promise"]:
            uc = 'method_http2_push'
        req.append(("fixed", 4, truncated_plain(f["req_method"], uc)))

    if f["two_line"]:
        req.append(fcol(f["req_http_version"], 'text'))
    else:
        schemes = {
            'http': 'scheme_http',
            'https': 'scheme_https',
        }
        req.append(fcol(fixlen(f["req_scheme"].upper(), 5), schemes.get(f["req_scheme"], "scheme_other")))

        req.append(('weight', 0.25, TruncatedText(f["req_host"], colorize_host(f["req_host"]), 'right')))
        req.append(('weight', 1.0, TruncatedText(f["req_path"], colorize_req(f["req_path"]), 'left')))

    ret = (' ' * len(SYMBOL_RETURN), 'text')
    status = ('', 'text')
    content = ('', 'text')
    size = ('', 'text')
    duration = ('', 'text')

    if "resp_code" in f:
        codes = {
            2: "code_200",
            3: "code_300",
            4: "code_400",
            5: "code_500",
        }
        ccol = codes.get(f["resp_code"] // 100, "code_other")
        ret = (SYMBOL_RETURN, ccol)
        status = (str(f["resp_code"]), ccol)

        if f["resp_len"] < 0:
            if f["intercepted"] and f["resp_code"] and not f["acked"]:
                rc = "intercept"
            else:
                rc = "content_none"

            if f["resp_len"] == -1:
                contentdesc = "[content missing]"
            else:
                contentdesc = "[no content]"
            content = (contentdesc, rc)
        else:
            if f["resp_ctype"]:
                ctype = f["resp_ctype"].split(";")[0]
                if ctype.endswith('/javascript'):
                    rc = 'content_script'
                elif ctype.startswith('text/'):
                    rc = 'content_text'
                elif (ctype.startswith('image/') or
                      ctype.startswith('video/') or
                      ctype.startswith('font/') or
                      "/x-font-" in ctype):
                    rc = 'content_media'
                elif ctype.endswith('/json') or ctype.endswith('/xml'):
                    rc = 'content_data'
                elif ctype.startswith('application/'):
                    rc = 'content_raw'
                else:
                    rc = 'content_other'
                content = (ctype, rc)

            rc = 'gradient_%02d' % int(99 - 100 * min(math.log2(1 + f["resp_len"]) / 20, 0.99))

            size_str = human.pretty_size(f["resp_len"])
            if not f['extended']:
                # shorten to 5 chars max
                if len(size_str) > 5:
                    size_str = size_str[0:4].rstrip('.') + size_str[-1:]
            size = (size_str, rc)

        if f['duration'] is not None:
            rc = 'gradient_%02d' % int(99 - 100 * min(math.log2(1 + 1000 * f['duration']) / 12, 0.99))
            duration = (human.pretty_duration(f['duration']), rc)

    elif f["err_msg"]:
        status = ('Err', 'error')
        content = f["err_msg"], 'error'

    if f["two_line"]:
        req.append(fcol(*ret))
    req.append(fcol(fixlen(status[0], 3), status[1]))
    req.append(('weight', 0.15, truncated_plain(content[0], content[1], 'right')))
    if f['extended']:
        req.append(fcol(*size))
    else:
        req.append(fcol(fixlen_r(size[0], 5), size[1]))
    req.append(fcol(fixlen_r(duration[0], 5), duration[1]))

    pile.append(urwid.Columns(req, dividechars=1, min_width=15))

    return urwid.Pile(pile)


def format_flow(f, focus, extended=False, hostheader=False, cols=False, layout='default'):
    acked = False
    if f.reply and f.reply.state == "committed":
        acked = True
    d = dict(
        focus=focus,
        extended=extended,
        two_line=extended or cols < 100,
        cols=cols,
        intercepted=f.intercepted,
        acked=acked,
        req_timestamp=f.request.timestamp_start,
        req_is_replay=f.request.is_replay,
        req_method=f.request.method,
        req_promise='h2-pushed-stream' in f.metadata,
        req_url=f.request.pretty_url if hostheader else f.request.url,
        req_scheme=f.request.scheme,
        req_host=f.request.pretty_host if hostheader else f.request.host,
        req_path=f.request.path,
        req_http_version=f.request.http_version,
        err_msg=f.error.msg if f.error else None,
        marked=f.marked,
    )
    if f.response:
        if f.response.raw_content:
            content_len = len(f.response.raw_content)
            contentdesc = human.pretty_size(len(f.response.raw_content))
        elif f.response.raw_content is None:
            content_len = -1
            contentdesc = "[content missing]"
        else:
            content_len = -2
            contentdesc = "[no content]"

        duration = None
        if f.response.timestamp_end and f.request.timestamp_start:
            duration = max([f.response.timestamp_end - f.request.timestamp_start, 0])

        d.update(dict(
            resp_code=f.response.status_code,
            resp_reason=f.response.reason,
            resp_is_replay=f.response.is_replay,
            resp_len=content_len,
            resp_ctype=f.response.headers.get("content-type"),
            resp_clen=contentdesc,
            duration=duration,
        ))

    if ((layout == 'default' and cols < 100) or layout == "list"):
        return raw_format_list(tuple(sorted(d.items())))
    else:
        return raw_format_table(tuple(sorted(d.items())))
