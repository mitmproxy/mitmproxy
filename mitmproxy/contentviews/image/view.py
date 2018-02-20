import imghdr

from mitmproxy.contentviews import base
from mitmproxy.coretypes import multidict
from . import image_parser


def test_ico(h, f):
    if h.startswith(b"\x00\x00\x01\x00"):
        return "ico"


imghdr.tests.append(test_ico)


class ViewImage(base.View):
    name = "Image"

    # there is also a fallback in the auto view for image/*.
    content_types = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/vnd.microsoft.icon",
        "image/x-icon",
        "image/webp",
    ]

    def __call__(self, data, **metadata):
        image_type = imghdr.what('', h=data)
        if image_type == 'png':
            image_metadata = image_parser.parse_png(data)
        elif image_type == 'gif':
            image_metadata = image_parser.parse_gif(data)
        elif image_type == 'jpeg':
            image_metadata = image_parser.parse_jpeg(data)
        elif image_type == 'ico':
            image_metadata = image_parser.parse_ico(data)
        else:
            image_metadata = [
                ("Image Format", image_type or "unknown")
            ]
        if image_type:
            view_name = "{} Image".format(image_type.upper())
        else:
            view_name = "Unknown Image"
        return view_name, base.format_dict(multidict.MultiDict(image_metadata))
