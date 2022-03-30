import time

from mitmproxy.proxy.commands import CloseConnection, Log, OpenConnection, SendData
from mitmproxy.proxy.events import ConnectionClosed, DataReceived
from mitmproxy.proxy.layers import dns
from mitmproxy.dns import DNSFlow
from mitmproxy.test.tutils import tdnsreq, tdnsresp
from ..tutils import Placeholder, Playbook, reply


def test_invalid_and_dummy_end(tctx):
    layer = dns.DNSLayer(tctx, dns.DnsMode.Simple)
    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, b'Not a DNS packet')
        << Log('Client(client:1234, state=open) sent an invalid message: 14 is not a valid OpCode')
        >> ConnectionClosed(tctx.client)
        >> DataReceived(tctx.client, b'You still there?')
        >> DataReceived(tctx.client, tdnsreq().packed)
        >> DataReceived(tctx.client, b'Hello?')
        << None
    )
    assert not layer.flows


def test_simple(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx, dns.DnsMode.Simple)

    req = tdnsreq()
    resp = tdnsresp()

    def resolve(flow: DNSFlow):
        nonlocal layer, req, resp
        assert flow.request
        assert layer.flows[flow.request.id] is flow
        req.timestamp = flow.request.timestamp
        assert flow.request == req
        resp.timestamp = time.time()
        flow.response = resp

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req.packed)
        << dns.DnsRequestHook(f)
        >> reply(side_effect=resolve)
        << dns.DnsResponseHook(f)
        >> reply()
        << SendData(tctx.client, resp.packed)
        >> ConnectionClosed(tctx.client)
        << None
    )
    assert not layer.flows and f().request == req and f().response == resp and not f().live


def test_simple_no_hook(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx, dns.DnsMode.Simple)

    req = tdnsreq()

    def no_resolve(flow: DNSFlow):
        nonlocal layer, req
        assert flow.request
        assert layer.flows[flow.request.id] is flow
        req.timestamp = flow.request.timestamp
        assert flow.request == req

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req.packed)
        << dns.DnsRequestHook(f)
        >> reply(side_effect=no_resolve)
        << dns.DnsErrorHook(f)
        >> reply()
        >> ConnectionClosed(tctx.client)
        << None
    )
    assert not layer.flows and f().request == req and not f().response and not f().live


def test_forward(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx, dns.DnsMode.Forward)

    req = tdnsreq()
    resp = tdnsresp()

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req.packed)
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, req.packed)
        >> DataReceived(tctx.server, resp.packed)
        << dns.DnsResponseHook(f)
        >> reply()
        << SendData(tctx.client, resp.packed)
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )
    assert not layer.flows and f().request and f().response and not f().live
    req.timestamp = f().request.timestamp
    resp.timestamp = f().response.timestamp
    assert f().request == req and f().response == resp


def test_forward_fail_connection(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx, dns.DnsMode.Forward)

    req = tdnsreq()

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req.packed)
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply("UDP no likey today.")
        << dns.DnsErrorHook(f)
        >> reply()
        << None
    )
    assert not layer.flows and f().request and not f().response and f().error.msg == "UDP no likey today." and not f().live
    req.timestamp = f().request.timestamp
    assert f().request == req


def test_forward_with_id_change(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx, dns.DnsMode.Forward)

    req = tdnsreq()
    req2 = tdnsreq()
    req2.id = req.id + 1
    resp = tdnsresp()
    resp.id = req2.id

    def check_in_flows(flow: DNSFlow):
        nonlocal layer
        assert flow.request
        assert layer.flows[flow.request.id] is flow

    def change_id(flow: DNSFlow):
        nonlocal req, resp
        check_in_flows(flow)
        req.timestamp = flow.request.timestamp
        assert flow.request == req
        flow.request = req2

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req.packed)
        << dns.DnsRequestHook(f)
        >> reply(side_effect=change_id)
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, req2.packed)
        >> DataReceived(tctx.server, resp.packed)
        << dns.DnsResponseHook(f)
        >> reply(side_effect=check_in_flows)
        << SendData(tctx.client, resp.packed)
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )
    assert not layer.flows and f().request and f().response and not f().live
    req2.timestamp = f().request.timestamp
    resp.timestamp = f().response.timestamp
    assert f().request == req2 and f().response == resp


def test_forward_with_query_resend(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx, dns.DnsMode.Forward)

    req = tdnsreq()
    req2 = tdnsreq()
    req2.reserved = 4
    resp = tdnsresp()

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req.packed)
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, req.packed)
        >> DataReceived(tctx.client, req2.packed)
        << dns.DnsRequestHook(f)
        >> reply()
        << SendData(tctx.server, req2.packed)
        >> DataReceived(tctx.server, resp.packed)
        << dns.DnsResponseHook(f)
        >> reply()
        << SendData(tctx.client, resp.packed)
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )
    assert not layer.flows and f().request and f().response and not f().live
    req2.timestamp = f().request.timestamp
    resp.timestamp = f().response.timestamp
    assert f().request == req2 and f().response == resp


def test_forward_with_invalid_response(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx, dns.DnsMode.Forward)

    req = tdnsreq()
    resp = tdnsresp()
    resp.id = resp.id + 1

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req.packed)
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, req.packed)
        >> DataReceived(tctx.server, resp.packed)
        << Log(f'Server(<no address>, state=open) responded to unknown message #{resp.id}')
    )
    assert layer.flows and f().request and not f().response and f().live
    req.timestamp = f().request.timestamp
    assert f().request == req
