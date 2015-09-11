from __future__ import absolute_import
import cStringIO
import json
import logging
import subprocess
import sys

import lxml.html
import lxml.etree
from PIL import Image

from PIL.ExifTags import TAGS
import html2text
import six

from netlib.odict import ODict
from netlib import encoding
import netlib.utils
from . import utils
from .exceptions import ContentViewException
from .contrib import jsbeautifier
from .contrib.wbxml.ASCommandResponse import ASCommandResponse

try:
    import pyamf
    from pyamf import remoting, flex
except ImportError:  # pragma nocover
    pyamf = None

try:
    import cssutils
except ImportError:  # pragma nocover
    cssutils = None
else:
    cssutils.log.setLevel(logging.CRITICAL)

    cssutils.ser.prefs.keepComments = True
    cssutils.ser.prefs.omitLastSemicolon = False
    cssutils.ser.prefs.indentClosingBrace = False
    cssutils.ser.prefs.validOnly = False

VIEW_CUTOFF = 1024 * 50
KEY_MAX = 30


def format_dict(d):
    """
    Transforms the given dictionary into a list of
        ("key",   key  )
        ("value", value)
    tuples, where key is padded to a uniform width.
    """
    max_key_len = max(len(k) for k in d.keys())
    max_key_len = min(max_key_len, KEY_MAX)
    for key, value in d.items():
        key += ":"
        key = key.ljust(max_key_len + 2)
        yield [
            ("header", key),
            ("text", value)
        ]


def format_text(content, limit):
    """
    Transforms the given content into
    """
    content = netlib.utils.cleanBin(content)

    for line in content[:limit].splitlines():
        yield [("text", line)]

    for msg in trailer(content, limit):
        yield msg


def trailer(content, limit):
    bytes_removed = len(content) - limit
    if bytes_removed > 0:
        yield [
            ("cutoff", "... {} of data not shown.".format(netlib.utils.pretty_size(bytes_removed)))
        ]


class View(object):
    name = None
    prompt = ()
    content_types = []

    def __call__(self, hdrs, content, limit):
        """
        Returns:
            A (description, content generator) tuple.

            The content generator yields lists of (style, text) tuples.
            Iit must not yield tuples of tuples, because urwid cannot process that.
        """
        raise NotImplementedError()


class ViewAuto(View):
    name = "Auto"
    prompt = ("auto", "a")
    content_types = []

    def __call__(self, hdrs, content, limit):
        ctype = hdrs.get("content-type")
        if ctype:
            ct = netlib.utils.parse_content_type(ctype) if ctype else None
            ct = "%s/%s" % (ct[0], ct[1])
            if ct in content_types_map:
                return content_types_map[ct][0](hdrs, content, limit)
            elif utils.isXML(content):
                return get("XML")(hdrs, content, limit)
        return get("Raw")(hdrs, content, limit)


class ViewRaw(View):
    name = "Raw"
    prompt = ("raw", "r")
    content_types = []

    def __call__(self, hdrs, content, limit):
        return "Raw", format_text(content, limit)


class ViewHex(View):
    name = "Hex"
    prompt = ("hex", "e")
    content_types = []

    @staticmethod
    def _format(content, limit):
        for offset, hexa, s in netlib.utils.hexdump(content[:limit]):
            yield [
                ("offset", offset + " "),
                ("text", hexa + "   "),
                ("text", s)
            ]
        for msg in trailer(content, limit):
            yield msg

    def __call__(self, hdrs, content, limit):
        return "Hex", self._format(content, limit)


class ViewXML(View):
    name = "XML"
    prompt = ("xml", "x")
    content_types = ["text/xml"]

    def __call__(self, hdrs, content, limit):
        parser = lxml.etree.XMLParser(
            remove_blank_text=True,
            resolve_entities=False,
            strip_cdata=False,
            recover=False
        )
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
        doctype = docinfo.doctype
        if prev:
            doctype += "\n".join(prev).strip()
        doctype = doctype.strip()

        s = lxml.etree.tostring(
            document,
            pretty_print=True,
            xml_declaration=True,
            doctype=doctype or None,
            encoding=docinfo.encoding
        )

        return "XML-like data", format_text(s, limit)


class ViewJSON(View):
    name = "JSON"
    prompt = ("json", "s")
    content_types = ["application/json"]

    def __call__(self, hdrs, content, limit):
        pretty_json = utils.pretty_json(content)
        if pretty_json:
            return "JSON", format_text(pretty_json, limit)


class ViewHTML(View):
    name = "HTML"
    prompt = ("html", "h")
    content_types = ["text/html"]

    def __call__(self, hdrs, content, limit):
        if utils.isXML(content):
            parser = lxml.etree.HTMLParser(
                strip_cdata=True,
                remove_blank_text=True
            )
            d = lxml.html.fromstring(content, parser=parser)
            docinfo = d.getroottree().docinfo
            s = lxml.etree.tostring(
                d,
                pretty_print=True,
                doctype=docinfo.doctype
            )
            return "HTML", format_text(s, limit)


class ViewHTMLOutline(View):
    name = "HTML Outline"
    prompt = ("html outline", "o")
    content_types = ["text/html"]

    def __call__(self, hdrs, content, limit):
        content = content.decode("utf-8")
        h = html2text.HTML2Text(baseurl="")
        h.ignore_images = True
        h.body_width = 0
        content = h.handle(content)
        return "HTML Outline", format_text(content, limit)


class ViewURLEncoded(View):
    name = "URL-encoded"
    prompt = ("urlencoded", "u")
    content_types = ["application/x-www-form-urlencoded"]

    def __call__(self, hdrs, content, limit):
        d = netlib.utils.urldecode(content)
        return "URLEncoded form", format_dict(ODict(d))


class ViewMultipart(View):
    name = "Multipart Form"
    prompt = ("multipart", "m")
    content_types = ["multipart/form-data"]

    @staticmethod
    def _format(v):
        yield [("highlight", "Form data:\n")]
        for message in format_dict(ODict(v)):
            yield message

    def __call__(self, hdrs, content, limit):
        v = netlib.utils.multipartdecode(hdrs, content)
        if v:
            return "Multipart form", self._format(v)


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


    class ViewAMF(View):
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

        def _format(self, envelope, limit):
            for target, message in iter(envelope):
                if isinstance(message, pyamf.remoting.Request):
                    yield [
                        ("header", "Request: "),
                        ("text", str(target)),
                    ]
                else:
                    yield [
                        ("header", "Response: "),
                        ("text", "%s, code %s" % (target, message.status)),
                    ]

                s = json.dumps(self.unpack(message), indent=4)
                for msg in format_text(s, limit):
                    yield msg

        def __call__(self, hdrs, content, limit):
            envelope = remoting.decode(content, strict=False)
            if envelope:
                return "AMF v%s" % envelope.amfVersion, self._format(envelope, limit)


class ViewJavaScript(View):
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
        cutoff = max(0, len(content) - limit)
        return "JavaScript", format_text(res, limit - cutoff)


class ViewCSS(View):
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

        return "CSS", format_text(beautified, limit)


class ViewImage(View):
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
            ("Size", "%s x %s px" % img.size),
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
            clean.append(
                [netlib.utils.cleanBin(i[0]), netlib.utils.cleanBin(i[1])]
            )
        fmt = format_dict(ODict(clean))
        return "%s image" % img.format, fmt


class ViewProtobuf(View):
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
            p = subprocess.Popen(
                ["protoc", "--version"],
                stdout=subprocess.PIPE
            )
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
        return "Protobuf", format_text(decoded, limit)


class ViewWBXML(View):
    name = "WBXML"
    prompt = ("wbxml", "w")
    content_types = [
        "application/vnd.wap.wbxml",
        "application/vnd.ms-sync.wbxml"
    ]

    def __call__(self, hdrs, content, limit):

        try:
            parser = ASCommandResponse(content)
            parsedContent = parser.xmlString
            if parsedContent:
                return "WBXML", format_text(parsedContent, limit)
        except:
            return None


views = [
    ViewAuto(),
    ViewRaw(),
    ViewHex(),
    ViewJSON(),
    ViewXML(),
    ViewWBXML(),
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


def get_content_view(viewmode, headers, content, limit, is_request):
    """
        Returns:
            A (description, content generator) tuple.

        Raises:
            ContentViewException, if the content view threw an error.
    """
    if not content:
        if is_request:
            return "No request content (press tab to view response)", []
        else:
            return "No content", []
    msg = []

    enc = headers.get("content-encoding")
    if enc and enc != "identity":
        decoded = encoding.decode(enc, content)
        if decoded:
            content = decoded
            msg.append("[decoded %s]" % enc)
    try:
        ret = viewmode(headers, content, limit)
    # Third-party viewers can fail in unexpected ways...
    except Exception as e:
        six.reraise(
            ContentViewException,
            ContentViewException(str(e)),
            sys.exc_info()[2]
        )
    if not ret:
        ret = get("Raw")(headers, content, limit)
        msg.append("Couldn't parse: falling back to Raw")
    else:
        msg.append(ret[0])
    return " ".join(msg), ret[1]
