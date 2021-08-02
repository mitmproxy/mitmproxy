import asyncio
import json

import flask
import pytest
from flask import request

from mitmproxy.addons import asgiapp
from mitmproxy.addons import next_layer
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.test import taddons

tapp = flask.Flask(__name__)


@tapp.route("/")
def hello():
    print("CALLED")
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


@pytest.mark.asyncio
async def test_asgi_full():
    ps = Proxyserver()
    addons = [
        asgiapp.WSGIApp(tapp, "testapp", 80),
        asgiapp.ASGIApp(errapp, "errapp", 80),
        asgiapp.ASGIApp(noresponseapp, "noresponseapp", 80),
    ]
    with taddons.context(ps, *addons) as tctx:
        tctx.master.addons.add(next_layer.NextLayer())
        tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
        ps.running()
        await tctx.master.await_log("Proxy server listening", level="info")
        proxy_addr = ps.server.sockets[0].getsockname()[:2]

        reader, writer = await asyncio.open_connection(*proxy_addr)
        req = f"GET http://testapp:80/ HTTP/1.1\r\n\r\n"
        writer.write(req.encode())
        header = await reader.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 200 OK")
        body = await reader.readuntil(b"testapp")
        assert body == b"testapp"

        reader, writer = await asyncio.open_connection(*proxy_addr)
        req = f"GET http://testapp:80/parameters?param1=1&param2=2 HTTP/1.1\r\n\r\n"
        writer.write(req.encode())
        header = await reader.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 200 OK")
        body = await reader.readuntil(b"}")
        assert body == b'{"param1": "1", "param2": "2"}'

        reader, writer = await asyncio.open_connection(*proxy_addr)
        req = f"POST http://testapp:80/requestbody HTTP/1.1\r\nContent-Length: 6\r\n\r\nHello!"
        writer.write(req.encode())
        header = await reader.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 200 OK")
        body = await reader.readuntil(b"}")
        assert body == b'{"body": "Hello!"}'

        reader, writer = await asyncio.open_connection(*proxy_addr)
        req = f"GET http://errapp:80/?foo=bar HTTP/1.1\r\n\r\n"
        writer.write(req.encode())
        header = await reader.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 500")
        body = await reader.readuntil(b"ASGI Error")
        assert body == b"ASGI Error"

        reader, writer = await asyncio.open_connection(*proxy_addr)
        req = f"GET http://noresponseapp:80/ HTTP/1.1\r\n\r\n"
        writer.write(req.encode())
        header = await reader.readuntil(b"\r\n\r\n")
        assert header.startswith(b"HTTP/1.1 500")
        body = await reader.readuntil(b"ASGI Error")
        assert body == b"ASGI Error"
