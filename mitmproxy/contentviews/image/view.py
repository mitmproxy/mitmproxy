from . import image_parser
from mitmproxy.contentviews import base
from mitmproxy.contrib import imghdr
from mitmproxy.coretypes import multidict


def test_ico(h, f):
    if h.startswith(b"\x00\x00\x01\x00"):
        return "ico"


imghdr.tests.append(test_ico)


class ViewImage(base.View):
    name = "Image"

    def __call__(self, data, **metadata):
        image_type = imghdr.what("", h=data)
        if image_type == "png":
            image_metadata = image_parser.parse_png(data)
        elif image_type == "gif":
            image_metadata = image_parser.parse_gif(data)
        elif image_type == "jpeg":
            image_metadata = image_parser.parse_jpeg(data)
        elif image_type == "ico":
            image_metadata = image_parser.parse_ico(data)
        else:
            image_metadata = [("Image Format", image_type or "unknown")]
        if image_type:
            view_name = f"{image_type.upper()} Image"
        else:
            view_name = "Unknown Image"
        return view_name, base.format_dict(multidict.MultiDict(image_metadata))

    def render_priority(
        self, data: bytes, *, content_type: str | None = None, **metadata
    ) -> float:
        return float(
            bool(
                content_type
                and content_type.startswith("image/")
                and content_type != "image/svg+xml"
            )
        )
