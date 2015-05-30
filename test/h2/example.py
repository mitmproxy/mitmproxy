from netlib.h2.frame import *
from netlib.h2.h2 import *

c = H2Client(("127.0.0.1", 443))
c.connect()

c.send_frame(HeadersFrame(
    flags=(Frame.FLAG_END_HEADERS | Frame.FLAG_END_STREAM),
    stream_id=0x1,
    headers=[
        (b':method', 'GET'),
        (b':path', b'/index.html'),
        (b':scheme', b'https'),
        (b':authority', b'localhost'),
    ]))

while True:
    print c.read_frame().human_readable()
