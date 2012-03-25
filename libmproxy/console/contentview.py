import re, cStringIO
import urwid
from PIL import Image
from PIL.ExifTags import TAGS
import common
from .. import utils, encoding, flow
from ..contrib import jsbeautifier

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
VIEW_CONTENT_PRETTY_TYPE_MULTIPART = 4
VIEW_CONTENT_PRETTY_TYPE_JAVASCRIPT = 5
VIEW_CONTENT_PRETTY_TYPE_IMAGE = 6

CONTENT_PRETTY_NAMES = {
    VIEW_CONTENT_PRETTY_TYPE_JSON: "JSON",
    VIEW_CONTENT_PRETTY_TYPE_XML: "XML",
    VIEW_CONTENT_PRETTY_TYPE_URLENCODED: "URL-encoded",
    VIEW_CONTENT_PRETTY_TYPE_MULTIPART: "Multipart Form",
    VIEW_CONTENT_PRETTY_TYPE_JAVASCRIPT: "JavaScript",
    VIEW_CONTENT_PRETTY_TYPE_IMAGE: "Image",
}

CONTENT_TYPES_MAP = {
    "text/html": VIEW_CONTENT_PRETTY_TYPE_XML,
    "application/json": VIEW_CONTENT_PRETTY_TYPE_JSON,
    "text/xml": VIEW_CONTENT_PRETTY_TYPE_XML,
    "multipart/form-data": VIEW_CONTENT_PRETTY_TYPE_MULTIPART,
    "application/x-www-form-urlencoded": VIEW_CONTENT_PRETTY_TYPE_URLENCODED,
    "application/x-javascript": VIEW_CONTENT_PRETTY_TYPE_JAVASCRIPT,
    "application/javascript": VIEW_CONTENT_PRETTY_TYPE_JAVASCRIPT,
    "text/javascript": VIEW_CONTENT_PRETTY_TYPE_JAVASCRIPT,
    "image/png": VIEW_CONTENT_PRETTY_TYPE_IMAGE,
    "image/jpeg": VIEW_CONTENT_PRETTY_TYPE_IMAGE,
    "image/gif": VIEW_CONTENT_PRETTY_TYPE_IMAGE,
    "image/x-icon": VIEW_CONTENT_PRETTY_TYPE_IMAGE,
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


def _view_text(content):
    """
        Generates a body for a chunk of text.
    """
    txt = []
    for i in utils.cleanBin(content[:VIEW_CUTOFF]).splitlines():
        txt.append(
            urwid.Text(("text", i))
        )
    trailer(len(content), txt)
    return txt


def view_raw(hdrs, content):
    txt = _view_text(content)
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


def view_multipart(hdrs, content):
    v = hdrs.get("content-type")
    if v:
        v = utils.parse_content_type(v[0])
        if not v:
            return
        boundary = v[2].get("boundary")
        if not boundary:
            return

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
        return "Multipart form", r


def view_urlencoded(hdrs, content):
    lines = utils.urldecode(content)
    if lines:
        body = common.format_keyvals(
                    [(k+":", v) for (k, v) in lines],
                    key = "header",
                    val = "text"
               )
        return "URLEncoded form", body


def view_javascript(hdrs, content):
    opts = jsbeautifier.default_options()
    opts.indent_size = 2
    res = jsbeautifier.beautify(content, opts)
    return "JavaScript", _view_text(res)


def view_image(hdrs, content):
    try:
        img = Image.open(cStringIO.StringIO(content))
    except IOError:
        return None
    parts = [
        ("Format", str(img.format_description)),
        ("Size", "%s x %s px"%img.size),
        ("Mode", str(img.mode)),
    ]
    for i in sorted(img.info.keys()):
        if i != "exif":
            parts.append(
                (str(i), str(img.info[i]))
            )
    if hasattr(img, "_getexif"):
        ex = img._getexif()
        if ex:
            for i in sorted(ex.keys()):
                tag = TAGS.get(i, i)
                parts.append(
                    (str(tag), str(ex[i]))
                )
    clean = []
    for i in parts:
        clean.append([utils.cleanBin(i[0]), utils.cleanBin(i[1])])
    fmt = common.format_keyvals(
            clean,
            key = "header",
            val = "text"
        )
    return "%s image"%img.format, fmt


PRETTY_FUNCTION_MAP = {
    VIEW_CONTENT_PRETTY_TYPE_XML: view_xmlish,
    VIEW_CONTENT_PRETTY_TYPE_JSON: view_json,
    VIEW_CONTENT_PRETTY_TYPE_URLENCODED: view_urlencoded,
    VIEW_CONTENT_PRETTY_TYPE_MULTIPART: view_multipart,
    VIEW_CONTENT_PRETTY_TYPE_JAVASCRIPT: view_javascript,
    VIEW_CONTENT_PRETTY_TYPE_IMAGE: view_image,
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
