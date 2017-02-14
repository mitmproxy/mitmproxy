import imghdr

from mitmproxy.contentviews import base
from mitmproxy.types import multidict
from . import image_parser


class ViewImage(base.View):
    name = "Image"
    prompt = ("image", "i")
    content_types = [
        "image/png",
        "image/jpeg",
        "image/gif",
    ]

    def __call__(self, data, **metadata):
        image_type = imghdr.what('', h=data)
        if image_type == 'png':
            f = "PNG"
            parts = image_parser.parse_png(data)
            fmt = base.format_dict(multidict.MultiDict(parts))
            return "%s image" % f, fmt
        elif image_type == 'gif':
            f = "GIF"
            parts = image_parser.parse_gif(data)
            fmt = base.format_dict(multidict.MultiDict(parts))
            return "%s image" % f, fmt
        elif image_type == 'jpeg':
            f = "JPEG"
            parts = image_parser.parse_jpeg(data)
            fmt = base.format_dict(multidict.MultiDict(parts))
            return "%s image" % f, fmt
