import pytest
import struct
import time

from ..tutils import Placeholder
from ..tutils import Playbook
from ..tutils import reply
from hypothesis import given
from hypothesis import strategies as st
from mitmproxy.dns import DNSFlow
from mitmproxy.proxy.commands import CloseConnection
from mitmproxy.proxy.commands import Log
from mitmproxy.proxy.commands import OpenConnection
from mitmproxy.proxy.commands import SendData
from mitmproxy.proxy.events import ConnectionClosed
from mitmproxy.proxy.events import DataReceived
from mitmproxy.proxy.layers import dns
from mitmproxy.test.tutils import tdnsreq
from mitmproxy.test.tutils import tdnsresp

# add @examples for this
@given(st.binary())
def test_fuzz_unpack_tcp_message(data):
    try:
        dns.unpack_message(data, "tcp", bytearray())
    except struct.error:
        pass

@given(st.binary())
def test_fuzz_unpack_udp_message(data):
    try:
        dns.unpack_message(data, "udp", bytearray())
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
        >> DataReceived(tctx.client, dns.pack_message(req, tctx.client.transport_protocol))
        << dns.DnsRequestHook(f)
        >> reply(side_effect=no_resolve)
        << dns.DnsErrorHook(f)
        >> reply()
        >> ConnectionClosed(tctx.client)
        << None
    )
    assert f().request == req
    assert not f().response
    assert not f().live


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
        >> DataReceived(tctx.client, dns.pack_message(req, tctx.client.transport_protocol))
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
        >> DataReceived(tctx.client, dns.pack_message(req, tctx.client.transport_protocol))
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, dns.pack_message(req, tctx.server.transport_protocol))
        >> DataReceived(tctx.server, dns.pack_message(resp, tctx.server.transport_protocol))
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
        >> DataReceived(tctx.client, dns.pack_message(req, tctx.client.transport_protocol))
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply("UDP no likey today.")
        << dns.DnsErrorHook(f)
        >> reply()
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
        >> DataReceived(tctx.client, dns.pack_message(req, tctx.client.transport_protocol))
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, dns.pack_message(req, tctx.server.transport_protocol))
        >> DataReceived(tctx.client, dns.pack_message(req2, tctx.client.transport_protocol))
        << dns.DnsRequestHook(f)
        >> reply()
        << SendData(tctx.server, dns.pack_message(req2, tctx.server.transport_protocol))
        >> DataReceived(tctx.server, dns.pack_message(resp,tctx.server.transport_protocol))
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
