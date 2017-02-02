import typing

from kaitaistruct import KaitaiStream

from . import png

Metadata = typing.List[typing.Tuple[str, str]]

def parse_png(data: bytes) -> Metadata:
    img = png.Png(KaitaiStream(data))
    parts = [tuple(['Format', 'Portable network graphics'])]
    parts.append(tuple(['Size', str(img.ihdr.width) + " x " + str(img.ihdr.height) + " px"]))
    for chunk in img.chunks:
        if chunk.type == 'gAMA':
            parts.append(tuple(['gamma', str(chunk.body.gamma_int / 100000)]))
        elif chunk.type == 'pHYs':
            aspectx = chunk.body.pixels_per_unit_x
            aspecty = chunk.body.pixels_per_unit_y
            parts.append(tuple(['aspect', str(aspectx) + " x " + str(aspecty)]))
        elif chunk.type == 'tEXt':
            parts.append(tuple([chunk.body.keyword, chunk.body.text]))
        elif chunk.type == 'iTXt':
            parts.append(tuple([chunk.body.keyword, chunk.body.text]))
        elif chunk.type == 'zTXt':
            parts.append(tuple([chunk.body.keyword, chunk.body.text_datastream.decode('iso8859-1')]))
    return parts
