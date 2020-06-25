import os
from typing import Iterable

import pytest
from hypothesis import example, given, seed, settings
from hypothesis.strategies import binary, composite, integers, lists, sampled_from

from mitmproxy import options
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import context, events
from mitmproxy.proxy2.commands import OpenConnection, SendData
from mitmproxy.proxy2.events import DataReceived, Start
from mitmproxy.proxy2.layers import http
from test.mitmproxy.proxy2.tutils import Placeholder, Playbook, reply

settings.register_profile("full", max_examples=100_000, deadline=None)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


@pytest.fixture(scope="module")
def opts():
    opts = options.Options()
    Proxyserver().load(opts)
    return opts


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
def fuzz_request(draw):
    request = draw(request_lines) + b"\r\n"
    request += b"\r\n".join(draw(headers))
    request += b"\r\n\r\n" + draw(bodies)
    request = mutate(draw, request)
    request = list(split(draw, request))
    return request


@composite
def fuzz_response(draw):
    response = draw(response_lines) + b"\r\n"
    response += b"\r\n".join(draw(headers))
    response += b"\r\n\r\n" + draw(bodies)
    response = mutate(draw, response)
    response = list(split(draw, response))
    return response


@given(fuzz_request())
def test_fuzz_request(opts, data):
    tctx = context.Context(context.Client(("client", 1234), ("127.0.0.1", 8080)), opts)

    layer = http.HttpLayer(tctx, HTTPMode.regular)
    for _ in layer.handle_event(Start()):
        pass
    for chunk in data:
        for _ in layer.handle_event(DataReceived(tctx.client, chunk)):
            pass


@given(fuzz_response())
@example([b'0 OK\r\n\r\n', b'\r\n', b'5\r\n12345\r\n0\r\n\r\n'])
def test_fuzz_response(opts, data):
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
