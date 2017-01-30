from kaitaistruct import KaitaiStream

from . import png

def get_png(data):
    img = png.Png(KaitaiStream(data))
    parts = {'format': 'Portable network graphics'}
    f = 'PNG'
    width = img.ihdr.width
    height = img.ihdr.height
    parts["width"] = width
    parts["height"] = height
    for i in range(0, len(img.chunks)):
        chunk = img.chunks[i]
        if chunk.type == 'gAMA':
            gamma = chunk.gamma_int / 100000
            parts['gamma'] = gamma
        elif chunk.type == 'pHYs':
            aspectx = chunk.pixels_per_unit_x
            aspecty = chunk.pixels_per_unit_y
            parts["aspectx"] = aspectx
            parts["aspecty"] = aspecty
    return f, parts

def format_contentviews(parts):
    ret = []
    ret.append(tuple(['Format', parts["format"]]))
    if "width" in parts:
        ret.append(tuple(['Size', str(parts["width"]) + " x " + str(parts["height"]) + " px"]))
    if "aspectx" in parts:
        ret.append(tuple(['aspect', '(' + str(parts["aspectx"]) + ', ' + str(parts["aspecty"]) + ')']))
    if "gamma" in parts:
        ret.append(tuple(['gamma', str(parts["gamma"])]))
    return ret
