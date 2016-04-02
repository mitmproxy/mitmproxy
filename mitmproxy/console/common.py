from __future__ import absolute_import

import urwid
import urwid.util
import os

import netlib.utils

from .. import utils
from .. import flow_export
from ..models import decoded
from . import signals


try:
    import pyperclip
except:
    pyperclip = False


VIEW_FLOW_REQUEST = 0
VIEW_FLOW_RESPONSE = 1

METHOD_OPTIONS = [
    ("get", "g"),
    ("post", "p"),
    ("put", "u"),
    ("head", "h"),
    ("trace", "t"),
    ("delete", "d"),
    ("options", "o"),
    ("edit raw", "e"),
]


def is_keypress(k):
    """
        Is this input event a keypress?
    """
    if isinstance(k, basestring):
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
                if isinstance(kv[1], urwid.Widget):
                    v = kv[1]
                elif kv[1] is None:
                    v = urwid.Text("")
                else:
                    v = urwid.Text([(val, kv[1])])
                ret.append(
                    urwid.Columns(
                        [
                            ("fixed", indent, urwid.Text("")),
                            (
                                "fixed",
                                maxk,
                                urwid.Text([(key, kv[0] or "")])
                            ),
                            v
                        ],
                        dividechars = 2
                    )
                )
    return ret


def shortcuts(k):
    if k == " ":
        k = "page down"
    elif k == "ctrl f":
        k = "page down"
    elif k == "ctrl b":
        k = "page up"
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
    SYMBOL_MARK = u"\u25cf"
else:
    SYMBOL_REPLAY = u"[r]"
    SYMBOL_RETURN = u"<-"
    SYMBOL_MARK = "[m]"


def raw_format_flow(f, focus, extended):
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

    if f["marked"]:
        req.append(fcol(SYMBOL_MARK, "mark"))

    if f["req_is_replay"]:
        req.append(fcol(SYMBOL_REPLAY, "replay"))
    req.append(fcol(f["req_method"], "method"))

    preamble = sum(i[1] for i in req) + len(req) - 1

    if f["intercepted"] and not f["acked"]:
        uc = "intercept"
    elif f["resp_code"] or f["err_msg"]:
        uc = "text"
    else:
        uc = "title"

    url = f["req_url"]
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

    if f["resp_code"]:
        codes = {
            2: "code_200",
            3: "code_300",
            4: "code_400",
            5: "code_500",
        }
        ccol = codes.get(f["resp_code"] / 100, "code_other")
        resp.append(fcol(SYMBOL_RETURN, ccol))
        if f["resp_is_replay"]:
            resp.append(fcol(SYMBOL_REPLAY, "replay"))
        resp.append(fcol(f["resp_code"], ccol))
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


# Save file to disk
def save_data(path, data):
    if not path:
        return
    try:
        with file(path, "wb") as f:
            f.write(data)
    except IOError as v:
        signals.status_message.send(message=v.strerror)


def ask_save_overwrite(path, data):
    if not path:
        return
    path = os.path.expanduser(path)
    if os.path.exists(path):
        def save_overwrite(k):
            if k == "y":
                save_data(path, data)

        signals.status_prompt_onekey.send(
            prompt = "'" + path + "' already exists. Overwrite?",
            keys = (
                ("yes", "y"),
                ("no", "n"),
            ),
            callback = save_overwrite
        )
    else:
        save_data(path, data)


def ask_save_path(prompt, data):
    signals.status_prompt_path.send(
        prompt = prompt,
        callback = ask_save_overwrite,
        args = (data, )
    )


def copy_flow_format_data(part, scope, flow):
    if part == "u":
        data = flow.request.url
    else:
        data = ""
        if scope in ("q", "a"):
            if flow.request.content is None:
                return None, "Request content is missing"
            with decoded(flow.request):
                if part == "h":
                    data += netlib.http.http1.assemble_request(flow.request)
                elif part == "c":
                    data += flow.request.content
                else:
                    raise ValueError("Unknown part: {}".format(part))
        if scope == "a" and flow.request.content and flow.response:
            # Add padding between request and response
            data += "\r\n" * 2
        if scope in ("s", "a") and flow.response:
            if flow.response.content is None:
                return None, "Response content is missing"
            with decoded(flow.response):
                if part == "h":
                    data += netlib.http.http1.assemble_response(flow.response)
                elif part == "c":
                    data += flow.response.content
                else:
                    raise ValueError("Unknown part: {}".format(part))
    return data, False


def export_prompt(k, flow):
    exporters = {
        "c": flow_export.curl_command,
        "p": flow_export.python_code,
        "r": flow_export.raw_request,
        "l": flow_export.locust_code,
        "t": flow_export.locust_task,
    }
    if k in exporters:
        copy_to_clipboard_or_prompt(exporters[k](flow))


def copy_to_clipboard_or_prompt(data):
    # pyperclip calls encode('utf-8') on data to be copied without checking.
    # if data are already encoded that way UnicodeDecodeError is thrown.
    toclip = ""
    try:
        toclip = data.decode('utf-8')
    except (UnicodeDecodeError):
        toclip = data

    try:
        pyperclip.copy(toclip)
    except (RuntimeError, UnicodeDecodeError, AttributeError, TypeError):
        def save(k):
            if k == "y":
                ask_save_path("Save data", data)
        signals.status_prompt_onekey.send(
            prompt = "Cannot copy data to clipboard. Save as file?",
            keys = (
                ("yes", "y"),
                ("no", "n"),
            ),
            callback = save
        )


def copy_flow(part, scope, flow, master, state):
    """
    part: _c_ontent, _h_eaders+content, _u_rl
    scope: _a_ll, re_q_uest, re_s_ponse
    """
    data, err = copy_flow_format_data(part, scope, flow)

    if err:
        signals.status_message.send(message=err)
        return

    if not data:
        if scope == "q":
            signals.status_message.send(message="No request content to copy.")
        elif scope == "s":
            signals.status_message.send(message="No response content to copy.")
        else:
            signals.status_message.send(message="No contents to copy.")
        return

    copy_to_clipboard_or_prompt(data)


def ask_copy_part(scope, flow, master, state):
    choices = [
        ("content", "c"),
        ("headers+content", "h")
    ]
    if scope != "s":
        choices.append(("url", "u"))

    signals.status_prompt_onekey.send(
        prompt = "Copy",
        keys = choices,
        callback = copy_flow,
        args = (scope, flow, master, state)
    )


def ask_save_body(part, master, state, flow):
    """
    Save either the request or the response body to disk. part can either be
    "q" (request), "s" (response) or None (ask user if necessary).
    """

    request_has_content = flow.request and flow.request.content
    response_has_content = flow.response and flow.response.content

    if part is None:
        # We first need to determine whether we want to save the request or the
        # response content.
        if request_has_content and response_has_content:
            signals.status_prompt_onekey.send(
                prompt = "Save",
                keys = (
                    ("request", "q"),
                    ("response", "s"),
                ),
                callback = ask_save_body,
                args = (master, state, flow)
            )
        elif response_has_content:
            ask_save_body("s", master, state, flow)
        else:
            ask_save_body("q", master, state, flow)

    elif part == "q" and request_has_content:
        ask_save_path(
            "Save request content",
            flow.request.get_decoded_content()
        )
    elif part == "s" and response_has_content:
        ask_save_path(
            "Save response content",
            flow.response.get_decoded_content()
        )
    else:
        signals.status_message.send(message="No content to save.")


flowcache = utils.LRUCache(800)


def format_flow(f, focus, extended=False, hostheader=False, marked=False):
    d = dict(
        intercepted = f.intercepted,
        acked = f.reply.acked,

        req_timestamp = f.request.timestamp_start,
        req_is_replay = f.request.is_replay,
        req_method = f.request.method,
        req_url = f.request.pretty_url if hostheader else f.request.url,
        req_http_version = f.request.http_version,

        err_msg = f.error.msg if f.error else None,
        resp_code = f.response.status_code if f.response else None,

        marked = marked,
    )
    if f.response:
        if f.response.content:
            contentdesc = netlib.utils.pretty_size(len(f.response.content))
        elif f.response.content is None:
            contentdesc = "[content missing]"
        else:
            contentdesc = "[no content]"
        duration = 0
        if f.response.timestamp_end and f.request.timestamp_start:
            duration = f.response.timestamp_end - f.request.timestamp_start
        roundtrip = utils.pretty_duration(duration)

        d.update(dict(
            resp_code = f.response.status_code,
            resp_is_replay = f.response.is_replay,
            resp_clen = contentdesc,
            roundtrip = roundtrip,
        ))
        t = f.response.headers.get("content-type")
        if t:
            d["resp_ctype"] = t.split(";")[0]
        else:
            d["resp_ctype"] = ""
    return flowcache.get(
        raw_format_flow,
        tuple(sorted(d.items())), focus, extended
    )
