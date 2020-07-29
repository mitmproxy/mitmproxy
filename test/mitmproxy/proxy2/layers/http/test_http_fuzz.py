import os
from typing import Iterable

from hypothesis import example, given, settings
from hypothesis.strategies import binary, booleans, composite, dictionaries, integers, lists, permutations, \
    sampled_from, sets, text

from h2.settings import SettingCodes
from mitmproxy import options
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import context, events
from mitmproxy.proxy2.commands import OpenConnection, SendData
from mitmproxy.proxy2.events import DataReceived, Start
from mitmproxy.proxy2.layers import http
from test.mitmproxy.proxy2.layers.http.hyper_h2_test_helpers import FrameFactory
from test.mitmproxy.proxy2.tutils import Placeholder, Playbook, reply

settings.register_profile("fast", max_examples=10)
settings.register_profile("deep", max_examples=100_000, deadline=None)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "fast"))

opts = options.Options()
Proxyserver().load(opts)

request_lines = sampled_from([
    b"GET / HTTP/1.1",
    b"GET http://example.com/ HTTP/1.1",
    b"CONNECT example.com:443 HTTP/1.1",
    b"HEAD /foo HTTP/0.9",
])
response_lines = sampled_from([
    b"HTTP/1.1 200 OK",
    b"HTTP/1.1 100 Continue",
    b"HTTP/0.9 204 No Content",
    b"HEAD /foo HTTP/0.9",
])
headers = lists(sampled_from([
    b"Host: example.com",
    b"Content-Length: 5",
    b"Expect: 100-continue",
    b"Transfer-Encoding: chunked",
    b"Connection: close",
    b"",
]))
bodies = sampled_from([
    b"",
    b"12345",
    b"5\r\n12345\r\n0\r\n\r\n"
])


def mutate(draw, data: bytes) -> bytes:
    cut_start = draw(integers(0, len(data)))
    cut_end = draw(integers(cut_start, len(data)))
    data = data[:cut_start] + data[cut_end:]

    replace_start = draw(integers(0, len(data)))
    replace_end = draw(integers(replace_start, len(data)))
    return data[:replace_start] + draw(binary()) + data[replace_end:]


def split(draw, data: bytes) -> Iterable[bytes]:
    a, b = sorted([
        draw(integers(0, len(data))),
        draw(integers(0, len(data)))
    ])
    if a > 0:
        yield data[:a]
    if a != b:
        yield data[a:b]
    if b < len(data):
        yield data[b:]


@composite
def fuzz_h1_request(draw):
    request = draw(request_lines) + b"\r\n"
    request += b"\r\n".join(draw(headers))
    request += b"\r\n\r\n" + draw(bodies)
    request = mutate(draw, request)
    request = list(split(draw, request))
    return request


@composite
def fuzz_h1_response(draw):
    response = draw(response_lines) + b"\r\n"
    response += b"\r\n".join(draw(headers))
    response += b"\r\n\r\n" + draw(bodies)
    response = mutate(draw, response)
    response = list(split(draw, response))
    return response


@given(fuzz_h1_request())
def test_fuzz_h1_request(data):
    tctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080)), opts)

    layer = http.HttpLayer(tctx, HTTPMode.regular)
    for _ in layer.handle_event(Start()):
        pass
    for chunk in data:
        for _ in layer.handle_event(DataReceived(tctx.client, chunk)):
            pass


@given(fuzz_h1_response())
@example([b'0 OK\r\n\r\n', b'\r\n', b'5\r\n12345\r\n0\r\n\r\n'])
def test_fuzz_h1_response(data):
    tctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080)), opts)
    server = Placeholder(context.Server)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
    assert (
            playbook
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << OpenConnection(server)
            >> reply(None)
            << SendData(server, b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
    )
    for chunk in data:
        for _ in playbook.layer.handle_event(events.DataReceived(server(), chunk)):
            pass


h2_flags = sets(sampled_from([
    "END_STREAM",
    "END_HEADERS",
]))


def _h2_request_parts(draw):
    ff = FrameFactory()
    settings = ff.build_settings_frame(
        settings=draw(dictionaries(
            keys=sampled_from(SettingCodes),
            values=integers(0, 2 ** 32 - 1),
            max_size=5,
        )), ack=draw(booleans())
    )
    headers = ff.build_headers_frame(
        headers=draw(permutations([
            (':authority', draw(sampled_from(['example.com', 'example.com:443', draw(text())]))),
            (':path', draw(sampled_from(['/', draw(text())]))),
            (':scheme', draw(sampled_from(['http', 'https', draw(text())]))),
            (':method', draw(sampled_from(['GET', 'POST', 'CONNECT', draw(text())]))),
            ('cookie', draw(text())),
            ('host', draw(text())),
            ('content-length', draw(text()))
        ]))
    )
    headers.flags.clear()
    headers.flags |= draw(h2_flags)
    data = ff.build_data_frame(
        draw(binary()), draw(h2_flags)
    )
    window_update = ff.build_window_update_frame(draw(sampled_from([1, 0, 2])), draw(integers(0, 2 ** 32 - 1)))

    return draw(lists(sampled_from([headers, settings, data, window_update]), min_size=1, max_size=4))


@composite
def h2_request_parts(draw):
    return _h2_request_parts(draw)


@composite
def h2_request_chunks(draw):
    parts = _h2_request_parts(draw)
    request = b"".join(x.serialize() for x in parts)
    request = mutate(draw, request)
    request = list(split(draw, request))
    return request


def h2_layer(opts):
    tctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080)), opts)
    tctx.client.alpn = b"h2"

    layer = http.HttpLayer(tctx, HTTPMode.regular)
    for _ in layer.handle_event(Start()):
        pass
    for _ in layer.handle_event(DataReceived(tctx.client, b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n')):
        pass
    return tctx, layer


@given(h2_request_parts())
def test_fuzz_h2_request(parts):
    tctx, layer = h2_layer(opts)
    for part in parts:
        for _ in layer.handle_event(DataReceived(tctx.client, part.serialize())):
            pass


@given(h2_request_chunks())
@example([b'\x00\x00\x00\x01\x07\x00\x00\x00\x01A\x88/\x91\xd3]\x05\\\x87\xa7\x84\x86\x82`\x80f\x80\\\x80'])
@example([b'\x00\x00\x05\x02\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00'])
@example([b'\x00\x00\x13\x01\x04\x00\x00\x00\x01A\x88/\x91\xd3]\x05\\\x87\xa7\x84\x86\x82`\x80f\x80\\\x80'])
@example([b'\x00\x00\x12\x01\x04\x00\x00\x00\x01\x84\x86\x82`\x80A\x88/\x91\xd3]\x05\\\x87\xa7\\\x81\x07'])
@example([b'\x00\x00\x12\x01\x04\x00\x00\x00\x01\x84\x86\x82`\x80A\x88/\x91\xd3]\x05\\\x87\xa7\\\x81\x07'])
@example([b'\x00\x00\x14\x01\x04\x00\x00\x00\x01A\x88/\x91\xd3]\x05\\\x87\xa7\x84\x86`\x80\x82f\x80\\\x81\x07'])
def test_fuzz_h2_request2(chunks):
    tctx, layer = h2_layer(opts)
    for chunk in chunks:
        for _ in layer.handle_event(DataReceived(tctx.client, chunk)):
            pass
