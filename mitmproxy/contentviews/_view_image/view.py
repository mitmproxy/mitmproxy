from .._utils import merge_repeated_keys
from .._utils import yaml_dumps
from . import image_parser
from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.contrib import imghdr


def test_ico(h, f):
    if h.startswith(b"\x00\x00\x01\x00"):
        return "ico"
    return None


imghdr.tests.append(test_ico)


class ImageContentview(Contentview):
    syntax_highlight = "yaml"

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
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
            image_metadata = []
        if image_type:
            view_name = f"{image_type.upper()} Image"
        else:
            view_name = "Unknown Image"
        return f"# {view_name}\n" + yaml_dumps(merge_repeated_keys(image_metadata))

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return float(
            bool(
                metadata.content_type
                and metadata.content_type.startswith("image/")
                and not metadata.content_type.endswith("+xml")
            )
        )


image = ImageContentview()
