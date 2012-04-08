import re, cStringIO
import urwid
from PIL import Image
from PIL.ExifTags import TAGS
import lxml.html, lxml.etree
import common
from .. import utils, encoding, flow
from ..contrib import jsbeautifier

VIEW_CUTOFF = 1024*50

VIEW_AUTO = 0
VIEW_JSON = 1
VIEW_XML = 2
VIEW_URLENCODED = 3
VIEW_MULTIPART = 4
VIEW_JAVASCRIPT = 5
VIEW_IMAGE = 6
VIEW_RAW = 7
VIEW_HEX = 8
VIEW_HTML = 9

VIEW_NAMES = {
    VIEW_AUTO: "Auto",
    VIEW_JSON: "JSON",
    VIEW_XML: "XML",
    VIEW_URLENCODED: "URL-encoded",
    VIEW_MULTIPART: "Multipart Form",
    VIEW_JAVASCRIPT: "JavaScript",
    VIEW_IMAGE: "Image",
    VIEW_RAW: "Raw",
    VIEW_HEX: "Hex",
    VIEW_HTML: "HTML",
}


VIEW_PROMPT = (
    ("auto detect", "a"),
    ("hex", "e"),
    ("html", "h"),
    ("image", "i"),
    ("javascript", "j"),
    ("json", "s"),
    ("raw", "r"),
    ("multipart", "m"),
    ("urlencoded", "u"),
    ("xml", "x"),
)

VIEW_SHORTCUTS = {
    "a": VIEW_AUTO,
    "x": VIEW_XML,
    "h": VIEW_HTML,
    "i": VIEW_IMAGE,
    "j": VIEW_JAVASCRIPT,
    "s": VIEW_JSON,
    "u": VIEW_URLENCODED,
    "m": VIEW_MULTIPART,
    "r": VIEW_RAW,
    "e": VIEW_HEX,
}

CONTENT_TYPES_MAP = {
    "text/html": VIEW_HTML,
    "application/json": VIEW_JSON,
    "text/xml": VIEW_XML,
    "multipart/form-data": VIEW_MULTIPART,
    "application/x-www-form-urlencoded": VIEW_URLENCODED,
    "application/x-javascript": VIEW_JAVASCRIPT,
    "application/javascript": VIEW_JAVASCRIPT,
    "text/javascript": VIEW_JAVASCRIPT,
    "image/png": VIEW_IMAGE,
    "image/jpeg": VIEW_IMAGE,
    "image/gif": VIEW_IMAGE,
    "image/vnd.microsoft.icon": VIEW_IMAGE,
    "image/x-icon": VIEW_IMAGE,
}

def trailer(clen, txt, limit):
    rem = clen - limit
    if rem > 0:
        txt.append(urwid.Text(""))
        txt.append(
            urwid.Text(
                [
                    ("highlight", "... %s of data not shown. Press "%utils.pretty_size(rem)),
                    ("key", "f"),
                    ("highlight", " to load all data.")
                ]
            )
        )


def _view_text(content, total, limit):
    """
        Generates a body for a chunk of text.
    """
    txt = []
    for i in utils.cleanBin(content).splitlines():
        txt.append(
            urwid.Text(("text", i), wrap="any")
        )
    trailer(total, txt, limit)
    return txt


def view_raw(hdrs, content, limit):
    txt = _view_text(content[:limit], len(content), limit)
    return "Raw", txt


def view_hex(hdrs, content, limit):
    txt = []
    for offset, hexa, s in utils.hexdump(content[:limit]):
        txt.append(urwid.Text([
            ("offset", offset),
            " ",
            ("text", hexa),
            "   ",
            ("text", s),
        ]))
    trailer(len(content), txt, limit)
    return "Hex", txt


def view_xml(hdrs, content, limit):
    parser = lxml.etree.XMLParser(remove_blank_text=True, resolve_entities=False, strip_cdata=False, recover=False)
    try:
        document = lxml.etree.fromstring(content, parser)
    except lxml.etree.XMLSyntaxError:
        return None
    docinfo = document.getroottree().docinfo

    prev = []
    p = document.getroottree().getroot().getprevious()
    while p is not None:
        prev.insert(
            0,
            lxml.etree.tostring(p)
        )
        p = p.getprevious()
    doctype=docinfo.doctype
    if prev:
        doctype += "\n".join(prev).strip()
    doctype = doctype.strip()

    s = lxml.etree.tostring(
            document,
            pretty_print=True,
            xml_declaration=True,
            doctype=doctype or None,
            encoding = docinfo.encoding
        )

    txt = []
    for i in s[:limit].strip().split("\n"):
        txt.append(
            urwid.Text(("text", i)),
        )
    trailer(len(content), txt, limit)
    return "XML-like data", txt


def view_html(hdrs, content, limit):
    if utils.isXML(content):
        parser = lxml.etree.HTMLParser(strip_cdata=True, remove_blank_text=True)
        d = lxml.html.fromstring(content, parser=parser)
        docinfo = d.getroottree().docinfo
        s = lxml.etree.tostring(d, pretty_print=True, doctype=docinfo.doctype)
        return "HTML", _view_text(s[:limit], len(s), limit)


def view_json(hdrs, content, limit):
    lines = utils.pretty_json(content)
    if lines:
        txt = []
        sofar = 0
        for i in lines:
            sofar += len(i)
            txt.append(
                urwid.Text(("text", i)),
            )
            if sofar > limit:
                break
        trailer(sum(len(i) for i in lines), txt, limit)
        return "JSON", txt


def view_multipart(hdrs, content, limit):
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


def view_urlencoded(hdrs, content, limit):
    lines = utils.urldecode(content)
    if lines:
        body = common.format_keyvals(
                    [(k+":", v) for (k, v) in lines],
                    key = "header",
                    val = "text"
               )
        return "URLEncoded form", body


def view_javascript(hdrs, content, limit):
    opts = jsbeautifier.default_options()
    opts.indent_size = 2
    try:
        res = jsbeautifier.beautify(content[:limit], opts)
    # begin nocover
    except:
        # Bugs in jsbeautifier mean that it can trhow arbitrary errors.
        return None
    # end nocover
    return "JavaScript", _view_text(res, len(content), limit)


def view_image(hdrs, content, limit):
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
    VIEW_XML: view_xml,
    VIEW_HTML: view_html,
    VIEW_JSON: view_json,
    VIEW_URLENCODED: view_urlencoded,
    VIEW_MULTIPART: view_multipart,
    VIEW_JAVASCRIPT: view_javascript,
    VIEW_IMAGE: view_image,
    VIEW_HEX: view_hex,
    VIEW_RAW: view_raw,
}

def get_view_func(viewmode, hdrs, content):
    """
        Returns a function object.
    """
    if viewmode == VIEW_AUTO:
        ctype = hdrs.get("content-type")
        if ctype:
            ctype = ctype[0]
        ct = utils.parse_content_type(ctype) if ctype else None
        if ct:
            viewmode = CONTENT_TYPES_MAP.get("%s/%s"%(ct[0], ct[1]))
        if not viewmode and utils.isXML(content):
            viewmode = VIEW_XML
    return PRETTY_FUNCTION_MAP.get(viewmode, view_raw)


def get_content_view(viewmode, hdrItems, content, limit):
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
    func = get_view_func(viewmode, hdrs, content)
    ret = func(hdrs, content, limit)
    if not ret:
        viewmode = VIEW_RAW
        ret = view_raw(hdrs, content, limit)
        msg.append("Couldn't parse: falling back to Raw")
    else:
        msg.append(ret[0])
    return " ".join(msg), ret[1]
