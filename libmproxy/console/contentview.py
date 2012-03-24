import urwid
import common
from .. import utils, encoding, flow

VIEW_CUTOFF = 1024*100

VIEW_CONTENT_RAW = 0
VIEW_CONTENT_HEX = 1
VIEW_CONTENT_PRETTY = 2

CONTENT_VIEWS = {
    VIEW_CONTENT_RAW: "raw",
    VIEW_CONTENT_HEX: "hex",
    VIEW_CONTENT_PRETTY: "pretty"
}

VIEW_CONTENT_PRETTY_TYPE_AUTO = 0
VIEW_CONTENT_PRETTY_TYPE_JSON = 1
VIEW_CONTENT_PRETTY_TYPE_XML = 2
VIEW_CONTENT_PRETTY_TYPE_URLENCODED = 3

CONTENT_PRETTY_NAMES = {
    VIEW_CONTENT_PRETTY_TYPE_JSON: "JSON",
    VIEW_CONTENT_PRETTY_TYPE_XML: "XML",
    VIEW_CONTENT_PRETTY_TYPE_URLENCODED: "URL-encoded"
}

CONTENT_TYPES_MAP = {
    "text/html": VIEW_CONTENT_PRETTY_TYPE_XML,
    "application/json": VIEW_CONTENT_PRETTY_TYPE_JSON,
    "text/xml": VIEW_CONTENT_PRETTY_TYPE_XML,
    "multipart/form-data": VIEW_CONTENT_PRETTY_TYPE_URLENCODED
}

def trailer(clen, txt):
    rem = clen - VIEW_CUTOFF
    if rem > 0:
        txt.append(urwid.Text(""))
        txt.append(
            urwid.Text(
                [
                    ("highlight", "... %s of data not shown"%utils.pretty_size(rem))
                ]
            )
        )


def view_raw(hdrs, content):
    txt = []
    for i in utils.cleanBin(content[:VIEW_CUTOFF]).splitlines():
        txt.append(
            urwid.Text(("text", i))
        )
    trailer(len(content), txt)
    return "Raw", txt


def view_hex(hdrs, content):
    txt = []
    for offset, hexa, s in utils.hexdump(content[:VIEW_CUTOFF]):
        txt.append(urwid.Text([
            ("offset", offset),
            " ",
            ("text", hexa),
            "   ",
            ("text", s),
        ]))
    trailer(len(content), txt)
    return "HEX", txt


def view_xmlish(hdrs, content):
    txt = []
    for i in utils.pretty_xmlish(content[:VIEW_CUTOFF]):
        txt.append(
            urwid.Text(("text", i)),
        )
    trailer(len(content), txt)
    return "XML-like data", txt


def view_json(hdrs, content):
    lines = utils.pretty_json(content)
    if lines:
        txt = []
        sofar = 0
        for i in lines:
            sofar += len(i)
            txt.append(
                urwid.Text(("text", i)),
            )
            if sofar > VIEW_CUTOFF:
                break
        trailer(sum(len(i) for i in lines), txt)
        return "JSON", txt


# FIXME
def view_formdata(content, boundary):
    rx = re.compile(r'\bname="([^"]+)"')
    keys = []
    vals = []

    for i in content.split("--" + boundary):
        parts = i.splitlines()
        if len(parts) > 1 and parts[0][0:2] != "--":
            match = rx.search(parts[1])
            if match:
                keys.append(match.group(1) + ":")
                vals.append(utils.cleanBin(
                    "\n".join(parts[3+parts[2:].index(""):])
                ))
    r = [
        urwid.Text(("highlight", "Form data:\n")),
    ]
    r.extend(common.format_keyvals(
        zip(keys, vals),
        key = "header",
        val = "text"
    ))
    return r


def view_urlencoded(hdrs, content):
    lines = utils.urldecode(content)
    if lines:
        body = common.format_keyvals(
                    [(k+":", v) for (k, v) in lines],
                    key = "header",
                    val = "text"
               )
        return "URLEncoded form", body


PRETTY_FUNCTION_MAP = {
    VIEW_CONTENT_PRETTY_TYPE_XML: view_xmlish,
    VIEW_CONTENT_PRETTY_TYPE_JSON: view_json,
    VIEW_CONTENT_PRETTY_TYPE_URLENCODED: view_urlencoded
}

def get_view_func(viewmode, pretty_type, hdrs, content):
    """
        Returns a function object.
    """
    if viewmode == VIEW_CONTENT_HEX:
        return view_hex
    elif viewmode == VIEW_CONTENT_RAW:
        return view_raw
    else:
        if pretty_type == VIEW_CONTENT_PRETTY_TYPE_AUTO:
            ctype = hdrs.get("content-type")
            if ctype:
                ctype = ctype[0]
            ct = utils.parse_content_type(ctype) if ctype else None
            if ct:
                pretty_type = CONTENT_TYPES_MAP.get("%s/%s"%(ct[0], ct[1]))
            if not pretty_type and utils.isXML(content):
                pretty_type = VIEW_CONTENT_PRETTY_TYPE_XML
        return PRETTY_FUNCTION_MAP.get(pretty_type, view_raw)


def get_content_view(viewmode, pretty_type, hdrItems, content):
    """
        Returns a (msg, body) tuple.
    """
    msg = []

    hdrs = flow.ODictCaseless([list(i) for i in hdrItems])

    enc = hdrs.get("content-encoding")
    if enc and enc[0] != "identity":
        decoded = encoding.decode(enc[0], content)
        if decoded:
            content = decoded
            msg.append("[decoded %s]"%enc[0])

    if viewmode == VIEW_CONTENT_PRETTY and pretty_type != VIEW_CONTENT_PRETTY_TYPE_AUTO:
        msg.append("[forced to %s]"%(CONTENT_PRETTY_NAMES[pretty_type]))
    func = get_view_func(viewmode, pretty_type, hdrs, content)

    ret = func(hdrs, content)
    if not ret:
        ret = view_raw(hdrs, content)
    msg.append(ret[0])
    return " ".join(msg), ret[1]
