import codecs

import hyperframe.frame
from mitmproxy import exceptions


def read_raw_frame(rfile):
    header = rfile.safe_read(9)
    length = int(codecs.encode(header[:3], 'hex_codec'), 16)

    if length == 4740180:
        raise exceptions.HttpException("Length field looks more like HTTP/1.1:\n{}".format(rfile.read(-1)))

    body = rfile.safe_read(length)
    return [header, body]


def parse_frame(header, body=None):
    if body is None:
        body = header[9:]
        header = header[:9]

    frame, _ = hyperframe.frame.Frame.parse_frame_header(header)
    frame.parse_body(memoryview(body))
    return frame
