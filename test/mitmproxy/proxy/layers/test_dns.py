import struct
import time

import pytest
from hypothesis import given
from hypothesis import HealthCheck
from hypothesis import settings
from hypothesis import strategies as st

from ..tutils import Placeholder
from ..tutils import Playbook
from ..tutils import reply
from mitmproxy.dns import DNSFlow
from mitmproxy.net.dns import response_codes
from mitmproxy.proxy.commands import CloseConnection
from mitmproxy.proxy.commands import Log
from mitmproxy.proxy.commands import OpenConnection
from mitmproxy.proxy.commands import SendData
from mitmproxy.proxy.events import ConnectionClosed
from mitmproxy.proxy.events import DataReceived
from mitmproxy.proxy.layers import dns
from mitmproxy.test.tflow import tdnsreq
from mitmproxy.test.tflow import tdnsresp
from mitmproxy.test.tflow import terr


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.binary())
def test_fuzz_unpack_tcp_message(tctx, data):
    layer = dns.DNSLayer(tctx)
    try:
        layer.unpack_message(data, True)
    except struct.error:
        pass


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(st.binary())
def test_fuzz_unpack_udp_message(tctx, data):
    tctx.client.transport_protocol = "udp"
    tctx.server.transport_protocol = "udp"

    layer = dns.DNSLayer(tctx)
    try:
        layer.unpack_message(data, True)
    except struct.error:
        pass


@pytest.mark.parametrize("transport_protocol", ["tcp", "udp"])
def test_invalid_and_dummy_end(tctx, transport_protocol):
    tctx.client.transport_protocol = transport_protocol
    tctx.server.transport_protocol = transport_protocol

    data = b"Not a DNS packet"
    if tctx.client.transport_protocol == "tcp":
        data = struct.pack("!H", len(data)) + data

    assert (
        Playbook(dns.DNSLayer(tctx))
        >> DataReceived(tctx.client, data)
        << Log(
            "Client(client:1234, state=open) sent an invalid message: question #0: unpack encountered a label of length 99"
        )
        << CloseConnection(tctx.client)
        >> ConnectionClosed(tctx.client)
    )


@pytest.mark.parametrize("transport_protocol", ["tcp", "udp"])
def test_regular(tctx, transport_protocol):
    tctx.client.transport_protocol = transport_protocol
    tctx.server.transport_protocol = transport_protocol

    f = Placeholder(DNSFlow)

    req = tdnsreq()
    resp = tdnsresp()

    def resolve(flow: DNSFlow):
        nonlocal req, resp
        assert flow.request
        req.timestamp = flow.request.timestamp
        assert flow.request == req
        resp.timestamp = time.time()
        flow.response = resp

    assert (
        Playbook(dns.DNSLayer(tctx))
        >> DataReceived(tctx.client, dns.pack_message(req, transport_protocol))
        << dns.DnsRequestHook(f)
        >> reply(side_effect=resolve)
        << dns.DnsResponseHook(f)
        >> reply()
        << SendData(tctx.client, dns.pack_message(resp, transport_protocol))
        >> ConnectionClosed(tctx.client)
        << None
    )
    assert f().request == req
    assert f().response == resp
    assert not f().live


@pytest.mark.parametrize("transport_protocol", ["tcp", "udp"])
def test_regular_mode_no_hook(tctx, transport_protocol):
    tctx.client.transport_protocol = transport_protocol
    tctx.server.transport_protocol = transport_protocol

    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx)
    layer.context.server.address = None

    req = tdnsreq()

    def no_resolve(flow: DNSFlow):
        nonlocal req
        assert flow.request
        req.timestamp = flow.request.timestamp
        assert flow.request == req

    assert (
        Playbook(layer)
        >> DataReceived(
            tctx.client, dns.pack_message(req, tctx.client.transport_protocol)
        )
        << dns.DnsRequestHook(f)
        >> reply(side_effect=no_resolve)
        << dns.DnsErrorHook(f)
        >> reply()
        << SendData(
            tctx.client,
            dns.pack_message(
                req.fail(response_codes.SERVFAIL), tctx.client.transport_protocol
            ),
        )
        >> ConnectionClosed(tctx.client)
        << None
    )
    assert f().request == req
    assert not f().response
    assert not f().live
    assert (
        f().error.msg == "No hook has set a response and there is no upstream server."
    )


@pytest.mark.parametrize("transport_protocol", ["tcp", "udp"])
def test_reverse_premature_close(tctx, transport_protocol):
    tctx.client.transport_protocol = transport_protocol
    tctx.server.transport_protocol = transport_protocol

    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)

    req = tdnsreq()

    assert (
        Playbook(layer)
        >> DataReceived(
            tctx.client, dns.pack_message(req, tctx.client.transport_protocol)
        )
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, dns.pack_message(req, tctx.server.transport_protocol))
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )
    assert f().request
    assert not f().response
    assert not f().live
    req.timestamp = f().request.timestamp
    assert f().request == req


def test_regular_hook_err(tctx):
    f = Placeholder(DNSFlow)

    req = tdnsreq()

    def err(flow: DNSFlow):
        flow.error = terr()

    assert (
        Playbook(dns.DNSLayer(tctx))
        >> DataReceived(
            tctx.client, dns.pack_message(req, tctx.client.transport_protocol)
        )
        << dns.DnsRequestHook(f)
        >> reply(side_effect=err)
        << dns.DnsErrorHook(f)
        >> reply()
        << SendData(
            tctx.client,
            dns.pack_message(
                req.fail(response_codes.SERVFAIL), tctx.client.transport_protocol
            ),
        )
        >> ConnectionClosed(tctx.client)
        << None
    )
    assert f().error
    assert not f().live


@pytest.mark.parametrize("transport_protocol", ["tcp", "udp"])
def test_reverse(tctx, transport_protocol):
    tctx.client.transport_protocol = transport_protocol
    tctx.server.transport_protocol = transport_protocol

    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)

    req = tdnsreq()
    resp = tdnsresp()

    assert (
        Playbook(layer)
        >> DataReceived(
            tctx.client, dns.pack_message(req, tctx.client.transport_protocol)
        )
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, dns.pack_message(req, tctx.server.transport_protocol))
        >> DataReceived(
            tctx.server, dns.pack_message(resp, tctx.server.transport_protocol)
        )
        << dns.DnsResponseHook(f)
        >> reply()
        << SendData(tctx.client, dns.pack_message(resp, tctx.client.transport_protocol))
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )
    assert f().request
    assert f().response
    assert not f().live
    req.timestamp = f().request.timestamp
    resp.timestamp = f().response.timestamp
    assert f().request == req and f().response == resp


@pytest.mark.parametrize("transport_protocol", ["tcp", "udp"])
def test_reverse_fail_connection(tctx, transport_protocol):
    tctx.client.transport_protocol = transport_protocol
    tctx.server.transport_protocol = transport_protocol

    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)

    req = tdnsreq()

    assert (
        Playbook(layer)
        >> DataReceived(
            tctx.client, dns.pack_message(req, tctx.client.transport_protocol)
        )
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply("UDP no likey today.")
        << dns.DnsErrorHook(f)
        >> reply()
        << SendData(
            tctx.client,
            dns.pack_message(
                req.fail(response_codes.SERVFAIL), tctx.client.transport_protocol
            ),
        )
        << None
    )
    assert f().request
    assert not f().response
    assert f().error.msg == "UDP no likey today."
    req.timestamp = f().request.timestamp
    assert f().request == req


@pytest.mark.parametrize("transport_protocol", ["tcp", "udp"])
def test_reverse_with_query_resend(tctx, transport_protocol):
    tctx.client.transport_protocol = transport_protocol
    tctx.server.transport_protocol = transport_protocol

    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)

    req = tdnsreq()
    req2 = tdnsreq()
    req2.reserved = 4
    resp = tdnsresp()

    assert (
        Playbook(layer)
        >> DataReceived(
            tctx.client, dns.pack_message(req, tctx.client.transport_protocol)
        )
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, dns.pack_message(req, tctx.server.transport_protocol))
        >> DataReceived(
            tctx.client, dns.pack_message(req2, tctx.client.transport_protocol)
        )
        << dns.DnsRequestHook(f)
        >> reply()
        << SendData(tctx.server, dns.pack_message(req2, tctx.server.transport_protocol))
        >> DataReceived(
            tctx.server, dns.pack_message(resp, tctx.server.transport_protocol)
        )
        << dns.DnsResponseHook(f)
        >> reply()
        << SendData(tctx.client, dns.pack_message(resp, tctx.client.transport_protocol))
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )
    assert f().request
    assert f().response
    assert not f().live
    req2.timestamp = f().request.timestamp
    resp.timestamp = f().response.timestamp
    assert f().request == req2
    assert f().response == resp


def test_tcp_message_over_multiple_events(tctx):
    tctx.client.transport_protocol = "tcp"
    tctx.server.transport_protocol = "tcp"

    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)
    f = Placeholder(DNSFlow)
    req = tdnsreq()
    resp = tdnsresp()
    resp_bytes = dns.pack_message(resp, tctx.client.transport_protocol)
    split = len(resp_bytes) // 2

    assert (
        Playbook(layer)
        >> DataReceived(
            tctx.client, dns.pack_message(req, tctx.client.transport_protocol)
        )
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, dns.pack_message(req, tctx.server.transport_protocol))
        >> DataReceived(tctx.server, resp_bytes[:split])
        >> DataReceived(tctx.server, resp_bytes[split:])
        << dns.DnsResponseHook(f)
        >> reply()
        << SendData(tctx.client, dns.pack_message(resp, tctx.client.transport_protocol))
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )


def test_query_pipelining_same_event(tctx):
    tctx.client.transport_protocol = "tcp"
    tctx.server.transport_protocol = "tcp"

    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)
    f1 = Placeholder(DNSFlow)
    f2 = Placeholder(DNSFlow)
    req1 = tdnsreq(id=1)
    req2 = tdnsreq(id=2)
    resp1 = tdnsresp(id=1)
    resp2 = tdnsresp(id=2)
    req_bytes = dns.pack_message(
        req1, tctx.client.transport_protocol
    ) + dns.pack_message(req2, tctx.client.transport_protocol)

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req_bytes)
        << dns.DnsRequestHook(f1)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, dns.pack_message(req1, tctx.server.transport_protocol))
        << dns.DnsRequestHook(f2)
        >> reply()
        << SendData(tctx.server, dns.pack_message(req2, tctx.server.transport_protocol))
        >> DataReceived(
            tctx.server, dns.pack_message(resp1, tctx.server.transport_protocol)
        )
        << dns.DnsResponseHook(f1)
        >> reply()
        << SendData(
            tctx.client, dns.pack_message(resp1, tctx.server.transport_protocol)
        )
        >> DataReceived(
            tctx.server, dns.pack_message(resp2, tctx.server.transport_protocol)
        )
        << dns.DnsResponseHook(f2)
        >> reply()
        << SendData(
            tctx.client, dns.pack_message(resp2, tctx.server.transport_protocol)
        )
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )


def test_query_pipelining_multiple_events(tctx):
    tctx.client.transport_protocol = "tcp"
    tctx.server.transport_protocol = "tcp"

    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)
    f1 = Placeholder(DNSFlow)
    f2 = Placeholder(DNSFlow)
    req1 = tdnsreq(id=1)
    req2 = tdnsreq(id=2)
    resp1 = tdnsresp(id=1)
    resp2 = tdnsresp(id=2)
    req_bytes = dns.pack_message(
        req1, tctx.client.transport_protocol
    ) + dns.pack_message(req2, tctx.client.transport_protocol)
    split = len(req_bytes) * 3 // 4

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req_bytes[:split])
        << dns.DnsRequestHook(f1)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, dns.pack_message(req1, tctx.server.transport_protocol))
        >> DataReceived(
            tctx.server, dns.pack_message(resp1, tctx.server.transport_protocol)
        )
        << dns.DnsResponseHook(f1)
        >> reply()
        << SendData(
            tctx.client, dns.pack_message(resp1, tctx.server.transport_protocol)
        )
        >> DataReceived(tctx.client, req_bytes[split:])
        << dns.DnsRequestHook(f2)
        >> reply()
        << SendData(tctx.server, dns.pack_message(req2, tctx.server.transport_protocol))
        >> DataReceived(
            tctx.server, dns.pack_message(resp2, tctx.server.transport_protocol)
        )
        << dns.DnsResponseHook(f2)
        >> reply()
        << SendData(
            tctx.client, dns.pack_message(resp2, tctx.server.transport_protocol)
        )
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )


def test_invalid_tcp_message_length(tctx):
    tctx.client.transport_protocol = "tcp"
    tctx.server.transport_protocol = "tcp"

    assert (
        Playbook(dns.DNSLayer(tctx))
        >> DataReceived(tctx.client, b"\x00\x00")
        << Log(
            "Client(client:1234, state=open) sent an invalid message: Message length field cannot be zero"
        )
        << CloseConnection(tctx.client)
        >> ConnectionClosed(tctx.client)
    )
