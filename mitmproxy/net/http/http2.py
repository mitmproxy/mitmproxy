import codecs

from hyperframe.frame import Frame

from mitmproxy import exceptions


def read_frame(rfile, parse=True):
    """
    Reads a full HTTP/2 frame from a file-like object.

    Returns a parsed frame and the consumed bytes.
    """
    header = rfile.safe_read(9)
    length = int(codecs.encode(header[:3], 'hex_codec'), 16)

    if length == 4740180:
        raise exceptions.HttpException("Length field looks more like HTTP/1.1:\n{}".format(rfile.read(-1)))

    body = rfile.safe_read(length)

    if parse:
        frame, _ = Frame.parse_frame_header(header)
        frame.parse_body(memoryview(body))
    else:
        frame = None

    return frame, b''.join([header, body])
