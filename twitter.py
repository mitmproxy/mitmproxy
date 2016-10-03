import certifi
import h2.connection
import h2.events

import errno
import socket
import ssl
import time

SERVER_NAME = 'twitter.com'

socket.setdefaulttimeout(2)

c = h2.connection.H2Connection()
c.initiate_connection()

ctx = ssl.create_default_context(cafile=certifi.where())
ctx.set_alpn_protocols(['h2', 'http/1.1'])
ctx.set_npn_protocols(['h2', 'http/1.1'])

s = socket.create_connection((SERVER_NAME, 443))
s = ctx.wrap_socket(s, server_hostname=SERVER_NAME)

s.sendall(c.data_to_send())

c.prioritize(1, weight=201, depends_on=0, exclusive=False)

headers = [
    (':method', 'GET'),
    (':path', '/'),
    (':authority', SERVER_NAME),
    (':scheme', 'https'),
    ('user-agent', 'custom-python-script'),
]
c.send_headers(1, headers, end_stream=True)

s.sendall(c.data_to_send())


while True:
    data = s.recv(65536 * 256)
    if not data:
        break

    try:
        events = c.receive_data(data)
        s.sendall(c.data_to_send())
    except:
        break

    for event in events:
        print(event)
