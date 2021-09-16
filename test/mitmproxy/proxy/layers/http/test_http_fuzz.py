from typing import Tuple, Dict, Any

import pytest
from h2.settings import SettingCodes
from hypothesis import example, given
from hypothesis.strategies import binary, booleans, composite, dictionaries, integers, lists, sampled_from, sets, text, \
    data

from mitmproxy import options, connection
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.connection import Server
from mitmproxy.http import HTTPFlow
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy import context, events
from mitmproxy.proxy.commands import OpenConnection, SendData
from mitmproxy.proxy.events import DataReceived, Start, ConnectionClosed
from mitmproxy.proxy.layers import http
from test.mitmproxy.proxy.layers.http.hyper_h2_test_helpers import FrameFactory
from test.mitmproxy.proxy.layers.http.test_http2 import make_h2, example_response_headers, example_request_headers, \
    start_h2_client
from test.mitmproxy.proxy.tutils import Placeholder, Playbook, reply, _TracebackInPlaybook, _eq

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


@composite
def mutations(draw, elements):
    data = draw(elements)

    cut_start = draw(integers(0, len(data)))
    cut_end = draw(integers(cut_start, len(data)))
    data = data[:cut_start] + data[cut_end:]

    replace_start = draw(integers(0, len(data)))
    replace_end = draw(integers(replace_start, len(data)))
    return data[:replace_start] + draw(binary()) + data[replace_end:]


@composite
def chunks(draw, elements):
    data = draw(elements)

    chunks = []
    a, b = sorted([
        draw(integers(0, len(data))),
        draw(integers(0, len(data)))
    ])
    if a > 0:
        chunks.append(data[:a])
    if a != b:
        chunks.append(data[a:b])
    if b < len(data):
        chunks.append(data[b:])

    return chunks


@composite
def h1_requests(draw):
    request = draw(request_lines) + b"\r\n"
    request += b"\r\n".join(draw(headers))
    request += b"\r\n\r\n" + draw(bodies)
    return request


@composite
def h2_responses(draw):
    response = draw(response_lines) + b"\r\n"
    response += b"\r\n".join(draw(headers))
    response += b"\r\n\r\n" + draw(bodies)
    return response


@given(chunks(mutations(h1_requests())))
def test_fuzz_h1_request(data):
    tctx = context.Context(connection.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), opts)

    layer = http.HttpLayer(tctx, HTTPMode.regular)
    for _ in layer.handle_event(Start()):
        pass
    for chunk in data:
        for _ in layer.handle_event(DataReceived(tctx.client, chunk)):
            pass


@given(chunks(mutations(h2_responses())))
@example([b'0 OK\r\n\r\n', b'\r\n', b'5\r\n12345\r\n0\r\n\r\n'])
def test_fuzz_h1_response(data):
    tctx = context.Context(connection.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), opts)
    server = Placeholder(connection.Server)
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
h2_stream_ids = integers(0, 3)
h2_stream_ids_nonzero = integers(1, 3)


@composite
def h2_headers(draw):
    required_headers = [
        [":path", '/'],
        [":scheme", draw(sampled_from(['http', 'https']))],
        [":method", draw(sampled_from(['GET', 'POST', 'CONNECT']))],
    ]
    optional_headers = [
        [":authority", draw(sampled_from(['example.com:443', 'example.com']))],
        ["cookie", "foobaz"],
        ["host", "example.com"],
        ["content-length", "42"],
    ]
    headers = required_headers + draw(lists(sampled_from(optional_headers), max_size=3))

    i = draw(integers(0, len(headers)))
    p = int(draw(booleans()))
    r = draw(text())
    if i > 0:
        headers[i - 1][p - 1] = r
    return headers


@composite
def h2_frames(draw):
    ff = FrameFactory()
    headers1 = ff.build_headers_frame(headers=draw(h2_headers()))
    headers1.flags.clear()
    headers1.flags |= draw(h2_flags)
    headers2 = ff.build_headers_frame(headers=draw(h2_headers()),
                                      depends_on=draw(h2_stream_ids),
                                      stream_weight=draw(integers(0, 255)),
                                      exclusive=draw(booleans()))
    headers2.flags.clear()
    headers2.flags |= draw(h2_flags)
    settings = ff.build_settings_frame(
        settings=draw(dictionaries(
            keys=sampled_from(SettingCodes),
            values=integers(0, 2 ** 32 - 1),
            max_size=5,
        )), ack=draw(booleans())
    )
    continuation = ff.build_continuation_frame(header_block=ff.encoder.encode(draw(h2_headers())), flags=draw(h2_flags))
    goaway = ff.build_goaway_frame(draw(h2_stream_ids))
    push_promise = ff.build_push_promise_frame(
        stream_id=draw(h2_stream_ids_nonzero),
        promised_stream_id=draw(h2_stream_ids),
        headers=draw(h2_headers())
    )
    rst = ff.build_rst_stream_frame(draw(h2_stream_ids_nonzero))
    prio = ff.build_priority_frame(
        stream_id=draw(h2_stream_ids_nonzero),
        weight=draw(integers(0, 255)),
        depends_on=draw(h2_stream_ids),
        exclusive=draw(booleans()),
    )
    data1 = ff.build_data_frame(
        draw(binary()), draw(h2_flags)
    )
    data2 = ff.build_data_frame(
        draw(binary()), draw(h2_flags), stream_id=draw(h2_stream_ids_nonzero)
    )
    window_update = ff.build_window_update_frame(draw(h2_stream_ids), draw(integers(0, 2 ** 32 - 1)))

    frames = draw(lists(sampled_from([
        headers1, headers2, settings, continuation, goaway, push_promise, rst, prio, data1, data2, window_update
    ]), min_size=1, max_size=11))
    return b"".join(x.serialize() for x in frames)


def h2_layer(opts):
    tctx = context.Context(connection.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), opts)
    tctx.client.alpn = b"h2"

    layer = http.HttpLayer(tctx, HTTPMode.regular)
    for _ in layer.handle_event(Start()):
        pass
    for _ in layer.handle_event(DataReceived(tctx.client, b'PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n')):
        pass
    return tctx, layer


def _h2_request(chunks):
    tctx, layer = h2_layer(opts)
    for chunk in chunks:
        for _ in layer.handle_event(DataReceived(tctx.client, chunk)):
            pass


@given(chunks(h2_frames()))
@example([b'\x00\x00\x00\x01\x05\x00\x00\x00\x01\x00\x00\x00\x01\x05\x00\x00\x00\x01'])
@example([b'\x00\x00\x00\x01\x07\x00\x00\x00\x01A\x88/\x91\xd3]\x05\\\x87\xa7\x84\x86\x82`\x80f\x80\\\x80'])
@example([b'\x00\x00\x05\x02\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00'])
@example([b'\x00\x00\x13\x01\x04\x00\x00\x00\x01A\x88/\x91\xd3]\x05\\\x87\xa7\x84\x86\x82`\x80f\x80\\\x80'])
@example([b'\x00\x00\x12\x01\x04\x00\x00\x00\x01\x84\x86\x82`\x80A\x88/\x91\xd3]\x05\\\x87\xa7\\\x81\x07'])
@example([b'\x00\x00\x12\x01\x04\x00\x00\x00\x01\x84\x86\x82`\x80A\x88/\x91\xd3]\x05\\\x87\xa7\\\x81\x07'])
@example([b'\x00\x00\x14\x01\x04\x00\x00\x00\x01A\x88/\x91\xd3]\x05\\\x87\xa7\x84\x86`\x80\x82f\x80'])
@example([
    b'\x00\x00%\x01\x04\x00\x00\x00\x01A\x8b/\x91\xd3]\x05\\\x87\xa6\xe3M3\x84\x86\x82`\x85\x94\xe7\x8c~\xfff\x88/\x91'
    b'\xd3]\x05\\\x87\xa7\\\x82h_\x00\x00\x07\x01\x05\x00\x00\x00\x01\xc1\x84\x86\x82\xc0\xbf\xbe'])
@example([b'\x00\x00\x03\x01\x04\x00\x00\x00\x01\x84\x86\x82\x00\x00\x08\x07\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'])
def test_fuzz_h2_request_chunks(chunks):
    _h2_request(chunks)


@given(chunks(mutations(h2_frames())))
def test_fuzz_h2_request_mutations(chunks):
    _h2_request(chunks)


def _h2_response(chunks):
    tctx = context.Context(connection.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), opts)
    playbook = Playbook(http.HttpLayer(tctx, HTTPMode.regular), hooks=False)
    server = Placeholder(connection.Server)
    assert (
            playbook
            >> DataReceived(tctx.client, b"GET http://example.com/ HTTP/1.1\r\nHost: example.com\r\n\r\n")
            << OpenConnection(server)
            >> reply(None, side_effect=make_h2)
            << SendData(server, Placeholder())
    )
    for chunk in chunks:
        for _ in playbook.layer.handle_event(events.DataReceived(server(), chunk)):
            pass


@pytest.mark.skip
@given(chunks(h2_frames()))
@example([b'\x00\x00\x03\x01\x04\x00\x00\x00\x01\x84\x86\x82',
          b'\x00\x00\x07\x05\x04\x00\x00\x00\x01\x00\x00\x00\x00\x84\x86\x82'])
@example([b'\x00\x00\x00\x00\x00\x00\x00\x00\x01'])
@example([b'\x00\x00\x00\x01\x04\x00\x00\x00\x01'])
@example([b'\x00\x00\x07\x05\x04\x00\x00\x00\x01\x00\x00\x00\x02\x84\x86\x82'])
@example([b'\x00\x00\x06\x014\x00\x01\x00\x00\x00\x00\x01@\x80\x81c\x86\x82'])
def test_fuzz_h2_response_chunks(chunks):
    _h2_response(chunks)


@given(chunks(mutations(h2_frames())))
def test_fuzz_h2_response_mutations(chunks):
    _h2_response(chunks)


@pytest.mark.parametrize("example", [(
        True, False,
        ["data_req", "reply_hook_req_headers", "reply_openconn", "data_resp", "data_reqbody",
         "data_respbody", "err_server_rst", "reply_hook_resp_headers"]),
    (True, False, ["data_req", "reply_hook_req_headers", "reply_openconn", "err_server_rst",
                   "data_reqbody", "reply_hook_error"]),
])
def test_cancel_examples(example):
    """
    We can't specify examples in test_fuzz_cancel (because we use data, see
    https://hypothesis.readthedocs.io/en/latest/data.html#interactive-draw),
    so we have this here for explicit examples.
    """
    stream_req, stream_resp, draws = example

    def draw(lst):
        if draws:
            this_draw = draws.pop(0)
            for name, evt in lst:
                if name == this_draw:
                    return name, evt
            raise AssertionError(f"{this_draw} not in list: {[name for name, _ in lst]}")
        else:
            return lst[0]

    _test_cancel(stream_req, stream_resp, draw)


@given(stream_request=booleans(), stream_response=booleans(), data=data())
def test_fuzz_cancel(stream_request, stream_response, data):
    _test_cancel(stream_request, stream_response, lambda lst: data.draw(sampled_from(lst)))


def _test_cancel(stream_req, stream_resp, draw):
    """
    Test that we don't raise an exception if someone disconnects.
    """
    tctx = context.Context(connection.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), opts)
    playbook, cff = start_h2_client(tctx)
    flow = Placeholder(HTTPFlow)
    server = Placeholder(Server)

    def maybe_stream(flow: HTTPFlow):
        if stream_req:
            flow.request.stream = True
        if stream_resp and flow.response:
            flow.response.stream = True

    hook_req_headers = http.HttpRequestHeadersHook(flow)
    hook_req = http.HttpRequestHook(flow)
    hook_resp_headers = http.HttpResponseHeadersHook(flow)
    hook_resp = http.HttpResponseHook(flow)
    hook_error = http.HttpErrorHook(flow)
    openconn = OpenConnection(server)
    send_upstream = SendData(server, Placeholder(bytes))

    data_req = DataReceived(tctx.client, cff.build_headers_frame(example_request_headers).serialize())
    data_reqbody = DataReceived(tctx.client, cff.build_data_frame(b"foo", flags=["END_STREAM"]).serialize())
    data_resp = DataReceived(server, cff.build_headers_frame(example_response_headers).serialize())
    data_respbody = DataReceived(server, cff.build_data_frame(b"bar", flags=["END_STREAM"]).serialize())

    client_disc = ConnectionClosed(tctx.client)
    client_rst = DataReceived(tctx.client, cff.build_rst_stream_frame(1).serialize())
    server_disc = ConnectionClosed(server)
    server_rst = DataReceived(server, cff.build_rst_stream_frame(1).serialize())

    evts: Dict[str, Tuple[Any, Any, Any]] = {}
    # precondition, but-not-after-this
    evts["data_req"] = data_req, None, client_disc
    evts["data_reqbody"] = data_reqbody, data_req, client_disc
    evts["reply_hook_req_headers"] = reply(to=hook_req_headers, side_effect=maybe_stream), hook_req_headers, None
    evts["reply_hook_req"] = reply(to=hook_req), hook_req, None
    evts["reply_openconn"] = reply(None, to=openconn, side_effect=make_h2), openconn, None
    evts["data_resp"] = data_resp, send_upstream, server_disc
    evts["data_respbody"] = data_respbody, data_resp, server_disc
    evts["reply_hook_resp_headers"] = reply(to=hook_resp_headers, side_effect=maybe_stream), hook_resp_headers, None
    evts["reply_hook_resp"] = reply(to=hook_resp), hook_resp, None
    evts["reply_hook_error"] = reply(to=hook_error), hook_error, None

    evts["err_client_disc"] = client_disc, None, None
    evts["err_client_rst"] = client_rst, None, client_disc
    evts["err_server_disc"] = server_disc, send_upstream, None
    evts["err_server_rst"] = server_rst, send_upstream, server_disc

    def eq_maybe(a, b):
        # _eq helpfully raises a TypeError when placeholder types don't match
        # that is useful in (test) development, but may happen legitimately when fuzzing here.
        try:
            return _eq(a, b)
        except TypeError:
            return False

    while evts:
        candidates = []
        for name, (evt, precon, negprecon) in evts.items():
            precondition_ok = (
                    precon is None or any(eq_maybe(x, precon) for x in playbook.actual)
            )
            neg_precondition_ok = (
                    negprecon is None or not any(eq_maybe(x, negprecon) for x in playbook.actual)
            )
            if precondition_ok and neg_precondition_ok:
                # crude hack to increase fuzzing efficiency: make it more likely that we progress.
                for i in range(1 if name.startswith("err_") else 3):
                    candidates.append((name, evt))
        if not candidates:
            break

        name, evt = draw(candidates)
        del evts[name]
        try:
            assert playbook >> evt
        except AssertionError:
            if any(
                    isinstance(x, _TracebackInPlaybook)
                    for x in playbook.actual
            ):
                raise
            else:
                # add commands that the server issued.
                playbook.expected.extend(playbook.actual[len(playbook.expected):])
