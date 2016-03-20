"""
Mitmproxy Content Views
=======================

mitmproxy includes a set of content views which can be used to format/decode/highlight data.
While they are currently used for HTTP message bodies only, the may be used in other contexts
in the future, e.g. to decode protobuf messages sent as WebSocket frames.

Thus, the View API is very minimalistic. The only arguments are `data` and `**metadata`,
where `data` is the actual content (as bytes). The contents on metadata depend on the protocol in
use. For HTTP, the message headers are passed as the ``headers`` keyword argument. For HTTP
requests, the query parameters are passed as the ``query`` keyword argument.

"""
from __future__ import (absolute_import, print_function, division)
from six.moves import cStringIO as StringIO
import json
import logging
import subprocess
import sys
import lxml.html
import lxml.etree
import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import html2text
import six
from netlib.odict import ODict
from netlib import encoding
from netlib.utils import clean_bin, hexdump, urldecode, multipartdecode, parse_content_type
from . import utils
from .exceptions import ContentViewException
from .contrib import jsbeautifier
from .contrib.wbxml.ASCommandResponse import ASCommandResponse

try:
    import pyamf
    from pyamf import remoting, flex
except ImportError:  # pragma no cover
    pyamf = None

try:
    import cssutils
except ImportError:  # pragma no cover
    cssutils = None
else:
    cssutils.log.setLevel(logging.CRITICAL)

    cssutils.ser.prefs.keepComments = True
    cssutils.ser.prefs.omitLastSemicolon = False
    cssutils.ser.prefs.indentClosingBrace = False
    cssutils.ser.prefs.validOnly = False

# Default view cutoff *in lines*
VIEW_CUTOFF = 512

KEY_MAX = 30


def format_dict(d):
    """
    Helper function that transforms the given dictionary into a list of
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


def format_text(text):
    """
    Helper function that transforms bytes into the view output format.
    """
    for line in text.splitlines():
        yield [("text", line)]


class View(object):
    name = None
    prompt = ()
    content_types = []

    def __call__(self, data, **metadata):
        """
        Transform raw data into human-readable output.

        Args:
            data: the data to decode/format as bytes.
            metadata: optional keyword-only arguments for metadata. Implementations must not
                rely on a given argument being present.

        Returns:
            A (description, content generator) tuple.

            The content generator yields lists of (style, text) tuples, where each list represents
            a single line. ``text`` is a unfiltered byte string which may need to be escaped,
            depending on the used output.

        Caveats:
            The content generator must not yield tuples of tuples,
            because urwid cannot process that. You have to yield a *list* of tuples per line.
        """
        raise NotImplementedError()


class ViewAuto(View):
    name = "Auto"
    prompt = ("auto", "a")
    content_types = []

    def __call__(self, data, **metadata):
        headers = metadata.get("headers", {})
        ctype = headers.get("content-type")
        if data and ctype:
            ct = parse_content_type(ctype) if ctype else None
            ct = "%s/%s" % (ct[0], ct[1])
            if ct in content_types_map:
                return content_types_map[ct][0](data, **metadata)
            elif utils.isXML(data):
                return get("XML")(data, **metadata)
        if metadata.get("query"):
            return get("Query")(data, **metadata)
        if data and utils.isMostlyBin(data):
            return get("Hex")(data)
        if not data:
            return "No content", []
        return get("Raw")(data)


class ViewRaw(View):
    name = "Raw"
    prompt = ("raw", "r")
    content_types = []

    def __call__(self, data, **metadata):
        return "Raw", format_text(data)


class ViewHex(View):
    name = "Hex"
    prompt = ("hex", "e")
    content_types = []

    @staticmethod
    def _format(data):
        for offset, hexa, s in hexdump(data):
            yield [
                ("offset", offset + " "),
                ("text", hexa + "   "),
                ("text", s)
            ]

    def __call__(self, data, **metadata):
        return "Hex", self._format(data)


class ViewXML(View):
    name = "XML"
    prompt = ("xml", "x")
    content_types = ["text/xml"]

    def __call__(self, data, **metadata):
        parser = lxml.etree.XMLParser(
            remove_blank_text=True,
            resolve_entities=False,
            strip_cdata=False,
            recover=False
        )
        try:
            document = lxml.etree.fromstring(data, parser)
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

        return "XML-like data", format_text(s)


class ViewJSON(View):
    name = "JSON"
    prompt = ("json", "s")
    content_types = ["application/json"]

    def __call__(self, data, **metadata):
        pretty_json = utils.pretty_json(data)
        if pretty_json:
            return "JSON", format_text(pretty_json)


class ViewHTML(View):
    name = "HTML"
    prompt = ("html", "h")
    content_types = ["text/html"]

    def __call__(self, data, **metadata):
        if utils.isXML(data):
            parser = lxml.etree.HTMLParser(
                strip_cdata=True,
                remove_blank_text=True
            )
            d = lxml.html.fromstring(data, parser=parser)
            docinfo = d.getroottree().docinfo
            s = lxml.etree.tostring(
                d,
                pretty_print=True,
                doctype=docinfo.doctype,
                encoding='utf8'
            )
            return "HTML", format_text(s)


class ViewHTMLOutline(View):
    name = "HTML Outline"
    prompt = ("html outline", "o")
    content_types = ["text/html"]

    def __call__(self, data, **metadata):
        data = data.decode("utf-8")
        h = html2text.HTML2Text(baseurl="")
        h.ignore_images = True
        h.body_width = 0
        outline = h.handle(data)
        return "HTML Outline", format_text(outline)


class ViewURLEncoded(View):
    name = "URL-encoded"
    prompt = ("urlencoded", "u")
    content_types = ["application/x-www-form-urlencoded"]

    def __call__(self, data, **metadata):
        d = urldecode(data)
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

    def __call__(self, data, **metadata):
        headers = metadata.get("headers", {})
        v = multipartdecode(headers, data)
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
            elif isinstance(b, datetime.datetime):
                return str(b)
            elif isinstance(b, flex.ArrayCollection):
                return [self.unpack(i, seen) for i in b]
            else:
                return b

        def _format(self, envelope):
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
                for msg in format_text(s):
                    yield msg

        def __call__(self, data, **metadata):
            envelope = remoting.decode(data, strict=False)
            if envelope:
                return "AMF v%s" % envelope.amfVersion, self._format(envelope)


class ViewJavaScript(View):
    name = "JavaScript"
    prompt = ("javascript", "j")
    content_types = [
        "application/x-javascript",
        "application/javascript",
        "text/javascript"
    ]

    def __call__(self, data, **metadata):
        opts = jsbeautifier.default_options()
        opts.indent_size = 2
        res = jsbeautifier.beautify(data, opts)
        return "JavaScript", format_text(res)


class ViewCSS(View):
    name = "CSS"
    prompt = ("css", "c")
    content_types = [
        "text/css"
    ]

    def __call__(self, data, **metadata):
        if cssutils:
            sheet = cssutils.parseString(data)
            beautified = sheet.cssText
        else:
            beautified = data

        return "CSS", format_text(beautified)


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

    def __call__(self, data, **metadata):
        try:
            img = Image.open(StringIO(data))
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
        fmt = format_dict(ODict(parts))
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

    def __call__(self, data, **metadata):
        decoded = self.decode_protobuf(data)
        return "Protobuf", format_text(decoded)


class ViewQuery(View):
    name = "Query"
    prompt = ("query", "q")
    content_types = []

    def __call__(self, data, **metadata):
        query = metadata.get("query")
        if query:
            return "Query", format_dict(query)
        else:
            return "Query", format_text("")


class ViewWBXML(View):
    name = "WBXML"
    prompt = ("wbxml", "w")
    content_types = [
        "application/vnd.wap.wbxml",
        "application/vnd.ms-sync.wbxml"
    ]

    def __call__(self, data, **metadata):

        try:
            parser = ASCommandResponse(data)
            parsedContent = parser.xmlString
            if parsedContent:
                return "WBXML", format_text(parsedContent)
        except:
            return None


views = []
content_types_map = {}
view_prompts = []


def get(name):
    for i in views:
        if i.name == name:
            return i


def get_by_shortcut(c):
    for i in views:
        if i.prompt[1] == c:
            return i


def add(view):
    # TODO: auto-select a different name (append an integer?)
    for i in views:
        if i.name == view.name:
            raise ContentViewException("Duplicate view: " + view.name)

    # TODO: the UI should auto-prompt for a replacement shortcut
    for prompt in view_prompts:
        if prompt[1] == view.prompt[1]:
            raise ContentViewException("Duplicate view shortcut: " + view.prompt[1])

    views.append(view)

    for ct in view.content_types:
        l = content_types_map.setdefault(ct, [])
        l.append(view)

    view_prompts.append(view.prompt)


def remove(view):
    for ct in view.content_types:
        l = content_types_map.setdefault(ct, [])
        l.remove(view)

        if not len(l):
            del content_types_map[ct]

    view_prompts.remove(view.prompt)
    views.remove(view)


add(ViewAuto())
add(ViewRaw())
add(ViewHex())
add(ViewJSON())
add(ViewXML())
add(ViewWBXML())
add(ViewHTML())
add(ViewHTMLOutline())
add(ViewJavaScript())
add(ViewCSS())
add(ViewURLEncoded())
add(ViewMultipart())
add(ViewImage())
add(ViewQuery())

if pyamf:
    add(ViewAMF())

if ViewProtobuf.is_available():
    add(ViewProtobuf())


def safe_to_print(lines, encoding="utf8"):
    """
    Wraps a content generator so that each text portion is a *safe to print* unicode string.
    """
    for line in lines:
        clean_line = []
        for (style, text) in line:
            try:
                text = clean_bin(text.decode(encoding, "strict"))
            except UnicodeDecodeError:
                text = clean_bin(text).decode(encoding, "strict")
            clean_line.append((style, text))
        yield clean_line


def get_content_view(viewmode, data, **metadata):
    """
        Args:
            viewmode: the view to use.
            data, **metadata: arguments passed to View instance.

        Returns:
            A (description, content generator) tuple.
            In contrast to calling the views directly, text is always safe-to-print unicode.

        Raises:
            ContentViewException, if the content view threw an error.
    """
    msg = []

    headers = metadata.get("headers", {})
    enc = headers.get("content-encoding")
    if enc and enc != "identity":
        decoded = encoding.decode(enc, data)
        if decoded:
            data = decoded
            msg.append("[decoded %s]" % enc)
    try:
        ret = viewmode(data, **metadata)
    # Third-party viewers can fail in unexpected ways...
    except Exception as e:
        six.reraise(
            ContentViewException,
            ContentViewException(str(e)),
            sys.exc_info()[2]
        )
    if not ret:
        ret = get("Raw")(data, **metadata)
        msg.append("Couldn't parse: falling back to Raw")
    else:
        msg.append(ret[0])
    return " ".join(msg), safe_to_print(ret[1])
