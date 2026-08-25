import io

from kaitaistruct import KaitaiStream

from mitmproxy.contrib.kaitaistruct import gif
from mitmproxy.contrib.kaitaistruct import ico
from mitmproxy.contrib.kaitaistruct import jpeg
from mitmproxy.contrib.kaitaistruct import png

type ImageMetadata = list[tuple[str, str]]


def parse_png(data: bytes) -> ImageMetadata:
    img = png.Png(KaitaiStream(io.BytesIO(data)))
    parts = [
        ("Format", "Portable network graphics"),
        ("Size", f"{img.ihdr.width} x {img.ihdr.height} px"),
    ]
    for chunk in img.chunks:
        if chunk.type == "gAMA":
            parts.append(("gamma", str(chunk.body.gamma_int / 100000)))
        elif chunk.type == "pHYs":
            aspectx = chunk.body.pixels_per_unit_x
            aspecty = chunk.body.pixels_per_unit_y
            parts.append(("aspect", f"{aspectx} x {aspecty}"))
        elif chunk.type == "tEXt":
            parts.append((chunk.body.keyword, chunk.body.text))
        elif chunk.type == "iTXt":
            parts.append((chunk.body.keyword, chunk.body.text))
        elif chunk.type == "zTXt":
            parts.append(
                (chunk.body.keyword, chunk.body.text_datastream.decode("iso8859-1"))
            )
    return parts


def parse_gif(data: bytes) -> ImageMetadata:
    img = gif.Gif(KaitaiStream(io.BytesIO(data)))
    descriptor = img.logical_screen_descriptor
    parts = [
        ("Format", "Compuserve GIF"),
        ("Version", f"GIF{img.hdr.version}"),
        ("Size", f"{descriptor.screen_width} x {descriptor.screen_height} px"),
        ("background", str(descriptor.bg_color_index)),
    ]
    ext_blocks = []
    for block in img.blocks:
        if block.block_type.name == "extension":
            ext_blocks.append(block)
    comment_blocks = []
    for block in ext_blocks:
        if block.body.label._name_ == "comment":
            comment_blocks.append(block)
    for block in comment_blocks:
        entries = block.body.body.entries
        for entry in entries:
            comment = entry.bytes
            if comment != b"":
                parts.append(("comment", str(comment)))
    return parts


def parse_jpeg(data: bytes) -> ImageMetadata:
    img = jpeg.Jpeg(KaitaiStream(io.BytesIO(data)))
    parts = [("Format", "JPEG (ISO 10918)")]
    for segment in img.segments:
        if segment.marker._name_ == "sof0":
            parts.append(
                ("Size", f"{segment.data.image_width} x {segment.data.image_height} px")
            )
        if segment.marker._name_ == "app0":
            parts.append(
                (
                    "jfif_version",
                    f"({segment.data.version_major}, {segment.data.version_minor})",
                )
            )
            parts.append(
                (
                    "jfif_density",
                    f"({segment.data.density_x}, {segment.data.density_y})",
                )
            )
            parts.append(("jfif_unit", str(segment.data.density_units._value_)))
        if segment.marker._name_ == "com":
            parts.append(("comment", segment.data.decode("utf8", "backslashreplace")))
        if segment.marker._name_ == "app1":
            if hasattr(segment.data, "body"):
                for field in segment.data.body.data.body.ifd0.fields:
                    if field.data is not None:
                        parts.append(
                            (field.tag._name_, field.data.decode("UTF-8").strip("\x00"))
                        )
    return parts


def parse_ico(data: bytes) -> ImageMetadata:
    img = ico.Ico(KaitaiStream(io.BytesIO(data)))
    parts = [
        ("Format", "ICO"),
        ("Number of images", str(img.num_images)),
    ]

    for i, image in enumerate(img.images):
        parts.append(
            (
                f"Image {i + 1}",
                "Size: {} x {}\n{: >18}Bits per pixel: {}\n{: >18}PNG: {}".format(
                    256 if not image.width else image.width,
                    256 if not image.height else image.height,
                    "",
                    image.bpp,
                    "",
                    image.is_png,
                ),
            )
        )

    return parts
