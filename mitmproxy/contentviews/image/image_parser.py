import io
import typing

from kaitaistruct import KaitaiStream

from mitmproxy.contrib.kaitaistruct import png

Metadata = typing.List[typing.Tuple[str, str]]


def parse_png(data: bytes) -> Metadata:
    img = png.Png(KaitaiStream(io.BytesIO(data)))
    parts = [
        ('Format', 'Portable network graphics')
    ]
    parts.append(('Size', "{0} x {1} px".format(img.ihdr.width, img.ihdr.height)))
    for chunk in img.chunks:
        if chunk.type == 'gAMA':
            parts.append(('gamma', str(chunk.body.gamma_int / 100000)))
        elif chunk.type == 'pHYs':
            aspectx = chunk.body.pixels_per_unit_x
            aspecty = chunk.body.pixels_per_unit_y
            parts.append(('aspect', "{0} x {1}".format(aspectx, aspecty)))
        elif chunk.type == 'tEXt':
            parts.append((chunk.body.keyword, chunk.body.text))
        elif chunk.type == 'iTXt':
            parts.append((chunk.body.keyword, chunk.body.text))
        elif chunk.type == 'zTXt':
            parts.append((chunk.body.keyword, chunk.body.text_datastream.decode('iso8859-1')))
    return parts
