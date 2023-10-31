import time

from ..tutils import Placeholder
from ..tutils import Playbook
from ..tutils import reply
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


def test_invalid_and_dummy_end(tctx):
    assert (
        Playbook(dns.DNSLayer(tctx))
        >> DataReceived(tctx.client, b"Not a DNS packet")
        << Log(
            "Client(client:1234, state=open) sent an invalid message: question #0: unpack encountered a label of length 99"
        )
        << CloseConnection(tctx.client)
        >> ConnectionClosed(tctx.client)
    )


def test_regular(tctx):
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
        >> DataReceived(tctx.client, req.packed)
        << dns.DnsRequestHook(f)
        >> reply(side_effect=resolve)
        << dns.DnsResponseHook(f)
        >> reply()
        << SendData(tctx.client, resp.packed)
        >> ConnectionClosed(tctx.client)
        << None
    )
    assert f().request == req
    assert f().response == resp
    assert not f().live


def test_regular_mode_no_hook(tctx):
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
        >> DataReceived(tctx.client, req.packed)
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


def test_reverse_premature_close(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)

    req = tdnsreq()

    assert (
        Playbook(layer)
        >> DataReceived(tctx.client, req.packed)
        << dns.DnsRequestHook(f)
        >> reply()
        << OpenConnection(tctx.server)
        >> reply(None)
        << SendData(tctx.server, req.packed)
        >> ConnectionClosed(tctx.client)
        << CloseConnection(tctx.server)
        << None
    )
    assert f().request
    assert not f().response
    assert not f().live
    req.timestamp = f().request.timestamp
    assert f().request == req


def test_reverse(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)

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
    assert f().request
    assert f().response
    assert not f().live
    req.timestamp = f().request.timestamp
    resp.timestamp = f().response.timestamp
    assert f().request == req and f().response == resp


def test_reverse_fail_connection(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)

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
    assert f().request
    assert not f().response
    assert f().error.msg == "UDP no likey today."
    req.timestamp = f().request.timestamp
    assert f().request == req


def test_reverse_with_query_resend(tctx):
    f = Placeholder(DNSFlow)
    layer = dns.DNSLayer(tctx)
    layer.context.server.address = ("8.8.8.8", 53)

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
    assert f().request
    assert f().response
    assert not f().live
    req2.timestamp = f().request.timestamp
    resp.timestamp = f().response.timestamp
    assert f().request == req2
    assert f().response == resp
