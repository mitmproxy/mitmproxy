import io, imghdr

from PIL import ExifTags
from PIL import Image

from mitmproxy.types import multidict
from . import image_parser

from mitmproxy.contentviews import base
from kaitaistruct import KaitaiStream


class ViewImage(base.View):
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
        if imghdr.what('', h=data) == 'png':
            f = "PNG"
            parts = image_parser.parse_png(io.BytesIO(data))
            fmt = base.format_dict(multidict.MultiDict(parts))
            return "%s image" % f, fmt
        try:
            img = Image.open(io.BytesIO(data))
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
                    tag = ExifTags.TAGS.get(i, i)
                    parts.append(
                        (str(tag), str(ex[i]))
                    )
        fmt = base.format_dict(multidict.MultiDict(parts))
        return "%s image" % img.format, fmt
