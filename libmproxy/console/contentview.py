import logging
import re, cStringIO, traceback, json
import urwid

from PIL import Image
from PIL.ExifTags import TAGS

import lxml.html, lxml.etree
import netlib.utils
import common
from .. import utils, encoding, flow
from ..contrib import jsbeautifier, html2text
import subprocess
try:
    import pyamf
    from pyamf import remoting, flex
except ImportError: # pragma nocover
    pyamf = None

try:
    import cssutils
except ImportError: # pragma nocover
    cssutils = None
else:
    cssutils.log.setLevel(logging.CRITICAL)

    cssutils.ser.prefs.keepComments = True
    cssutils.ser.prefs.omitLastSemicolon = False
    cssutils.ser.prefs.indentClosingBrace = False
    cssutils.ser.prefs.validOnly = False

VIEW_CUTOFF = 1024*50


def _view_text(content, total, limit):
    """
        Generates a body for a chunk of text.
    """
    txt = []
    for i in netlib.utils.cleanBin(content).splitlines():
        txt.append(
            urwid.Text(("text", i), wrap="any")
        )
    trailer(total, txt, limit)
    return txt


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


class ViewAuto:
    name = "Auto"
    prompt = ("auto", "a")
    content_types = []
    def __call__(self, hdrs, content, limit):
        ctype = hdrs.get_first("content-type")
        if ctype:
            ct = utils.parse_content_type(ctype) if ctype else None
            ct = "%s/%s"%(ct[0], ct[1])
            if ct in content_types_map:
                return content_types_map[ct][0](hdrs, content, limit)
            elif utils.isXML(content):
                return get("XML")(hdrs, content, limit)
        return get("Raw")(hdrs, content, limit)


class ViewRaw:
    name = "Raw"
    prompt = ("raw", "r")
    content_types = []
    def __call__(self, hdrs, content, limit):
        txt = _view_text(content[:limit], len(content), limit)
        return "Raw", txt


class ViewHex:
    name = "Hex"
    prompt = ("hex", "e")
    content_types = []
    def __call__(self, hdrs, content, limit):
        txt = []
        for offset, hexa, s in netlib.utils.hexdump(content[:limit]):
            txt.append(urwid.Text([
                ("offset", offset),
                " ",
                ("text", hexa),
                "   ",
                ("text", s),
            ]))
        trailer(len(content), txt, limit)
        return "Hex", txt


class ViewXML:
    name = "XML"
    prompt = ("xml", "x")
    content_types = ["text/xml"]
    def __call__(self, hdrs, content, limit):
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


class ViewJSON:
    name = "JSON"
    prompt = ("json", "s")
    content_types = ["application/json"]
    def __call__(self, hdrs, content, limit):
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


class ViewHTML:
    name = "HTML"
    prompt = ("html", "h")
    content_types = ["text/html"]
    def __call__(self, hdrs, content, limit):
        if utils.isXML(content):
            parser = lxml.etree.HTMLParser(strip_cdata=True, remove_blank_text=True)
            d = lxml.html.fromstring(content, parser=parser)
            docinfo = d.getroottree().docinfo
            s = lxml.etree.tostring(d, pretty_print=True, doctype=docinfo.doctype)
            return "HTML", _view_text(s[:limit], len(s), limit)


class ViewHTMLOutline:
    name = "HTML Outline"
    prompt = ("html outline", "o")
    content_types = ["text/html"]
    def __call__(self, hdrs, content, limit):
        content = content.decode("utf-8")
        h = html2text.HTML2Text(baseurl="")
        h.ignore_images = True
        h.body_width = 0
        content = h.handle(content)
        txt = _view_text(content[:limit], len(content), limit)
        return "HTML Outline", txt


class ViewURLEncoded:
    name = "URL-encoded"
    prompt = ("urlencoded", "u")
    content_types = ["application/x-www-form-urlencoded"]
    def __call__(self, hdrs, content, limit):
        lines = utils.urldecode(content)
        if lines:
            body = common.format_keyvals(
                        [(k+":", v) for (k, v) in lines],
                        key = "header",
                        val = "text"
                   )
            return "URLEncoded form", body


class ViewMultipart:
    name = "Multipart Form"
    prompt = ("multipart", "m")
    content_types = ["multipart/form-data"]
    def __call__(self, hdrs, content, limit):
        v = hdrs.get_first("content-type")
        if v:
            v = utils.parse_content_type(v)
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
                        vals.append(netlib.utils.cleanBin(
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


if pyamf:
    class DummyObject(dict):
        def __init__(self, alias):
            dict.__init__(self)

        def __readamf__(self, input):
            data = input.readObject()
            self["data"] = data

    def pyamf_class_loader(s):
        for i in pyamf.CLASS_LOADERS:
            if i != pyamf_class_loader:
                v = i(s)
                if v:
                    return v
        return DummyObject

    pyamf.register_class_loader(pyamf_class_loader)

    class ViewAMF:
        name = "AMF"
        prompt = ("amf", "f")
        content_types = ["application/x-amf"]

        def unpack(self, b, seen=set([])):
            if hasattr(b, "body"):
                return self.unpack(b.body, seen)
            if isinstance(b, DummyObject):
                if id(b) in seen:
                    return "<recursion>"
                else:
                    seen.add(id(b))
                    for k, v in b.items():
                        b[k] = self.unpack(v, seen)
                    return b
            elif isinstance(b, dict):
                for k, v in b.items():
                    b[k] = self.unpack(v, seen)
                return b
            elif isinstance(b, list):
                return [self.unpack(i) for i in b]
            elif isinstance(b, flex.ArrayCollection):
                return [self.unpack(i, seen) for i in b]
            else:
                return b

        def __call__(self, hdrs, content, limit):
            envelope = remoting.decode(content, strict=False)
            if not envelope:
                return None


            txt = []
            for target, message in iter(envelope):
                if isinstance(message, pyamf.remoting.Request):
                    txt.append(urwid.Text([
                        ("header", "Request: "),
                        ("text", str(target)),
                    ]))
                else:
                    txt.append(urwid.Text([
                        ("header", "Response: "),
                        ("text", "%s, code %s"%(target, message.status)),
                    ]))

                s = json.dumps(self.unpack(message), indent=4)
                txt.extend(_view_text(s[:limit], len(s), limit))

            return "AMF v%s"%envelope.amfVersion, txt


class ViewJavaScript:
    name = "JavaScript"
    prompt = ("javascript", "j")
    content_types = [
        "application/x-javascript",
        "application/javascript",
        "text/javascript"
    ]
    def __call__(self, hdrs, content, limit):
        opts = jsbeautifier.default_options()
        opts.indent_size = 2
        res = jsbeautifier.beautify(content[:limit], opts)
        return "JavaScript", _view_text(res, len(res), limit)

class ViewCSS:
    name = "CSS"
    prompt = ("css", "c")
    content_types = [
        "text/css"
    ]

    def __call__(self, hdrs, content, limit):
        if cssutils:
            sheet = cssutils.parseString(content)
            beautified = sheet.cssText
        else:
            beautified = content

        return "CSS", _view_text(beautified, len(beautified), limit)


class ViewImage:
    name = "Image"
    prompt = ("image", "i")
    content_types = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/vnd.microsoft.icon",
        "image/x-icon",
    ]
    def __call__(self, hdrs, content, limit):
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
            clean.append([netlib.utils.cleanBin(i[0]), netlib.utils.cleanBin(i[1])])
        fmt = common.format_keyvals(
                clean,
                key = "header",
                val = "text"
            )
        return "%s image"%img.format, fmt

class ViewProtobuf:
    """Human friendly view of protocol buffers
    The view uses the protoc compiler to decode the binary
    """

    name = "Protocol Buffer"
    prompt = ("protobuf", "p")
    content_types = [
        "application/x-protobuf",
        "application/x-protobuffer",
    ]

    @staticmethod
    def is_available():
        try:
            p = subprocess.Popen(["protoc", "--version"], stdout=subprocess.PIPE)
            out, _ = p.communicate()
            return out.startswith("libprotoc")
        except:
            return False

    def decode_protobuf(self, content):
        # if Popen raises OSError, it will be caught in
        # get_content_view and fall back to Raw
        p = subprocess.Popen(['protoc', '--decode_raw'],
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        out, err = p.communicate(input=content)
        if out:
            return out
        else:
            return err

    def __call__(self, hdrs, content, limit):
        decoded = self.decode_protobuf(content)
        txt = _view_text(decoded[:limit], len(decoded), limit)
        return "Protobuf", txt

views = [
    ViewAuto(),
    ViewRaw(),
    ViewHex(),
    ViewJSON(),
    ViewXML(),
    ViewHTML(),
    ViewHTMLOutline(),
    ViewJavaScript(),
    ViewCSS(),
    ViewURLEncoded(),
    ViewMultipart(),
    ViewImage(),
]
if pyamf:
    views.append(ViewAMF())

if ViewProtobuf.is_available():
    views.append(ViewProtobuf())

content_types_map = {}
for i in views:
    for ct in i.content_types:
        l = content_types_map.setdefault(ct, [])
        l.append(i)


view_prompts = [i.prompt for i in views]


def get_by_shortcut(c):
    for i in views:
        if i.prompt[1] == c:
            return i


def get(name):
    for i in views:
        if i.name == name:
            return i


def get_content_view(viewmode, hdrItems, content, limit, logfunc):
    """
        Returns a (msg, body) tuple.
    """
    if not content:
        return ("No content", "")
    msg = []

    hdrs = flow.ODictCaseless([list(i) for i in hdrItems])

    enc = hdrs.get_first("content-encoding")
    if enc and enc != "identity":
        decoded = encoding.decode(enc, content)
        if decoded:
            content = decoded
            msg.append("[decoded %s]"%enc)
    try:
        ret = viewmode(hdrs, content, limit)
    # Third-party viewers can fail in unexpected ways...
    except Exception:
        s = traceback.format_exc()
        s = "Content viewer failed: \n"  + s
        logfunc(s)
        ret = None
    if not ret:
        ret = get("Raw")(hdrs, content, limit)
        msg.append("Couldn't parse: falling back to Raw")
    else:
        msg.append(ret[0])
    return " ".join(msg), ret[1]
