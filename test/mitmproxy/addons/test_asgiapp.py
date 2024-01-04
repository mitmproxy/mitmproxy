import asyncio
import json

import flask
from flask import request

from mitmproxy.addons import asgiapp
from mitmproxy.addons import next_layer
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.test import taddons

tapp = flask.Flask(__name__)


@tapp.route("/")
def hello():
    return "testapp"


@tapp.route("/parameters")
def request_check():
    args = {}
    for k in request.args.keys():
        args[k] = request.args[k]
    return json.dumps(args)


@tapp.route("/requestbody", methods=["POST"])
def request_body():
    return json.dumps({"body": request.data.decode()})


@tapp.route("/error")
def error():
    raise ValueError("An exception...")


async def errapp(scope, receive, send):
    raise ValueError("errapp")


async def noresponseapp(scope, receive, send):
    return


async def test_asgi_full(caplog):
    ps = Proxyserver()
    addons = [
        asgiapp.WSGIApp(tapp, "testapp", 80),
        asgiapp.ASGIApp(errapp, "errapp", 80),
        asgiapp.ASGIApp(noresponseapp, "noresponseapp", 80),
    ]
    with taddons.context(ps, *addons) as tctx:
        tctx.master.addons.add(next_layer.NextLayer())
        tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
        assert await ps.setup_servers()
        proxy_addr = ("127.0.0.1", ps.listen_addrs()[0][1])

        # We parallelize connection establishment/closure because those operations tend to be slow.
        [
            (r1, w1),
            (r2, w2),
            (r3, w3),
            (r4, w4),
            (r5, w5),
        ] = await asyncio.gather(
            asyncio.open_connection(*proxy_addr),
            asyncio.open_connection(*proxy_addr),
            asyncio.open_connection(*proxy_addr),
            asyncio.open_connection(*proxy_addr),
            asyncio.open_connection(*proxy_addr),
        )

        req = f"GET http://testapp:80/ HTTP/1.1\r\n\r\n"
        w1.write(req.encode())
        header = await r1.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 200 OK")
        body = await r1.readuntil(b"testapp")
        assert body == b"testapp"

        req = f"GET http://testapp:80/parameters?param1=1&param2=2 HTTP/1.1\r\n\r\n"
        w2.write(req.encode())
        header = await r2.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 200 OK")
        body = await r2.readuntil(b"}")
        assert body == b'{"param1": "1", "param2": "2"}'

        req = f"POST http://testapp:80/requestbody HTTP/1.1\r\nContent-Length: 6\r\n\r\nHello!"
        w3.write(req.encode())
        header = await r3.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 200 OK")
        body = await r3.readuntil(b"}")
        assert body == b'{"body": "Hello!"}'

        req = f"GET http://errapp:80/?foo=bar HTTP/1.1\r\n\r\n"
        w4.write(req.encode())
        header = await r4.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 500")
        body = await r4.readuntil(b"ASGI Error")
        assert body == b"ASGI Error"
        assert "ValueError" in caplog.text

        req = f"GET http://noresponseapp:80/ HTTP/1.1\r\n\r\n"
        w5.write(req.encode())
        header = await r5.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 500")
        body = await r5.readuntil(b"ASGI Error")
        assert body == b"ASGI Error"
        assert "no response sent" in caplog.text

        w1.close()
        w2.close()
        w3.close()
        w4.close()
        w5.close()
        await asyncio.gather(
            w1.wait_closed(),
            w2.wait_closed(),
            w3.wait_closed(),
            w4.wait_closed(),
            w5.wait_closed(),
        )

        tctx.configure(ps, server=False)
        assert await ps.setup_servers()
