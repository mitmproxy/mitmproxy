from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import logging
import os.path
import re
import secrets
import sys
from collections.abc import Callable
from collections.abc import Sequence
from io import BytesIO
from typing import Any
from typing import ClassVar
from typing import Concatenate
from typing import Literal

import tornado.escape
import tornado.web
import tornado.websocket

import mitmproxy.flow
import mitmproxy.tools.web.master
import mitmproxy_rs
from mitmproxy import certs
from mitmproxy import command
from mitmproxy import contentviews
from mitmproxy import flowfilter
from mitmproxy import http
from mitmproxy import io
from mitmproxy import log
from mitmproxy import optmanager
from mitmproxy import version
from mitmproxy.dns import DNSFlow
from mitmproxy.http import HTTPFlow
from mitmproxy.net.http import status_codes
from mitmproxy.tcp import TCPFlow
from mitmproxy.tcp import TCPMessage
from mitmproxy.tools.web.webaddons import WebAuth
from mitmproxy.udp import UDPFlow
from mitmproxy.udp import UDPMessage
from mitmproxy.utils import asyncio_utils
from mitmproxy.utils.emoji import emoji
from mitmproxy.utils.strutils import always_str
from mitmproxy.utils.strutils import cut_after_n_lines
from mitmproxy.websocket import WebSocketMessage

TRANSPARENT_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08"
    b"\x04\x00\x00\x00\xb5\x1c\x0c\x02\x00\x00\x00\x0bIDATx\xdac\xfc\xff\x07"
    b"\x00\x02\x00\x01\xfc\xa8Q\rh\x00\x00\x00\x00IEND\xaeB`\x82"
)

logger = logging.getLogger(__name__)


def cert_to_json(certs: Sequence[certs.Cert]) -> dict | None:
    if not certs:
        return None
    cert = certs[0]
    return {
        "keyinfo": cert.keyinfo,
        "sha256": cert.fingerprint().hex(),
        "notbefore": int(cert.notbefore.timestamp()),
        "notafter": int(cert.notafter.timestamp()),
        "serial": str(cert.serial),
        "subject": cert.subject,
        "issuer": cert.issuer,
        "altnames": [str(x.value) for x in cert.altnames],
    }


def flow_to_json(flow: mitmproxy.flow.Flow) -> dict:
    """
    Remove flow message content and cert to save transmission space.
    Args:
        flow: The original flow.
    Sync with web/src/flow.ts.
    """
    f = {
        "id": flow.id,
        "intercepted": flow.intercepted,
        "is_replay": flow.is_replay,
        "type": flow.type,
        "modified": flow.modified(),
        "marked": emoji.get(flow.marked, "🔴") if flow.marked else "",
        "comment": flow.comment,
        "timestamp_created": flow.timestamp_created,
    }

    if flow.client_conn:
        f["client_conn"] = {
            "id": flow.client_conn.id,
            "peername": flow.client_conn.peername,
            "sockname": flow.client_conn.sockname,
            "tls_established": flow.client_conn.tls_established,
            "cert": cert_to_json(flow.client_conn.certificate_list),
            "sni": flow.client_conn.sni,
            "cipher": flow.client_conn.cipher,
            "alpn": always_str(flow.client_conn.alpn, "ascii", "backslashreplace"),
            "tls_version": flow.client_conn.tls_version,
            "timestamp_start": flow.client_conn.timestamp_start,
            "timestamp_tls_setup": flow.client_conn.timestamp_tls_setup,
            "timestamp_end": flow.client_conn.timestamp_end,
        }

    if flow.server_conn:
        f["server_conn"] = {
            "id": flow.server_conn.id,
            "peername": flow.server_conn.peername,
            "sockname": flow.server_conn.sockname,
            "address": flow.server_conn.address,
            "tls_established": flow.server_conn.tls_established,
            "cert": cert_to_json(flow.server_conn.certificate_list),
            "sni": flow.server_conn.sni,
            "cipher": flow.server_conn.cipher,
            "alpn": always_str(flow.server_conn.alpn, "ascii", "backslashreplace"),
            "tls_version": flow.server_conn.tls_version,
            "timestamp_start": flow.server_conn.timestamp_start,
            "timestamp_tcp_setup": flow.server_conn.timestamp_tcp_setup,
            "timestamp_tls_setup": flow.server_conn.timestamp_tls_setup,
            "timestamp_end": flow.server_conn.timestamp_end,
        }
    if flow.error:
        f["error"] = flow.error.get_state()

    if isinstance(flow, HTTPFlow):
        content_length: int | None
        content_hash: str | None

        if flow.request.raw_content is not None:
            content_length = len(flow.request.raw_content)
            content_hash = hashlib.sha256(flow.request.raw_content).hexdigest()
        else:
            content_length = None
            content_hash = None
        f["request"] = {
            "method": flow.request.method,
            "scheme": flow.request.scheme,
            "host": flow.request.host,
            "port": flow.request.port,
            "path": flow.request.path,
            "http_version": flow.request.http_version,
            "headers": tuple(flow.request.headers.items(True)),
            "contentLength": content_length,
            "contentHash": content_hash,
            "timestamp_start": flow.request.timestamp_start,
            "timestamp_end": flow.request.timestamp_end,
            "pretty_host": flow.request.pretty_host,
        }
        if flow.response:
            if flow.response.raw_content is not None:
                content_length = len(flow.response.raw_content)
                content_hash = hashlib.sha256(flow.response.raw_content).hexdigest()
            else:
                content_length = None
                content_hash = None
            f["response"] = {
                "http_version": flow.response.http_version,
                "status_code": flow.response.status_code,
                "reason": flow.response.reason,
                "headers": tuple(flow.response.headers.items(True)),
                "contentLength": content_length,
                "contentHash": content_hash,
                "timestamp_start": flow.response.timestamp_start,
                "timestamp_end": flow.response.timestamp_end,
            }
            if flow.response.data.trailers:
                f["response"]["trailers"] = tuple(
                    flow.response.data.trailers.items(True)
                )

        if flow.websocket:
            f["websocket"] = {
                "messages_meta": {
                    "contentLength": sum(
                        len(x.content) for x in flow.websocket.messages
                    ),
                    "count": len(flow.websocket.messages),
                    "timestamp_last": flow.websocket.messages[-1].timestamp
                    if flow.websocket.messages
                    else None,
                },
                "closed_by_client": flow.websocket.closed_by_client,
                "close_code": flow.websocket.close_code,
                "close_reason": flow.websocket.close_reason,
                "timestamp_end": flow.websocket.timestamp_end,
            }
    elif isinstance(flow, (TCPFlow, UDPFlow)):
        f["messages_meta"] = {
            "contentLength": sum(len(x.content) for x in flow.messages),
            "count": len(flow.messages),
            "timestamp_last": flow.messages[-1].timestamp if flow.messages else None,
        }
    elif isinstance(flow, DNSFlow):
        f["request"] = flow.request.to_json()
        if flow.response:
            f["response"] = flow.response.to_json()

    return f


def logentry_to_json(e: log.LogEntry) -> dict:
    return {
        "id": id(e),  # we just need some kind of id.
        "message": e.msg,
        "level": e.level,
    }


class APIError(tornado.web.HTTPError):
    pass


class AuthRequestHandler(tornado.web.RequestHandler):
    AUTH_COOKIE_VALUE = b"y"

    def __init_subclass__(cls, **kwargs):
        """Automatically wrap all request handlers with `_require_auth`."""
        for method in cls.SUPPORTED_METHODS:
            method = method.lower()
            fn = getattr(cls, method)
            if fn is not tornado.web.RequestHandler._unimplemented_method:
                setattr(cls, method, AuthRequestHandler._require_auth(fn))

    def auth_fail(self, invalid_password: bool) -> None:
        """
        Will be called when returning a 403.
        May write a login form as the response.
        """

    @staticmethod
    def _require_auth[**P, R](
        fn: Callable[Concatenate[AuthRequestHandler, P], R],
    ) -> Callable[Concatenate[AuthRequestHandler, P], R | None]:
        @functools.wraps(fn)
        def wrapper(
            self: AuthRequestHandler, *args: P.args, **kwargs: P.kwargs
        ) -> R | None:
            if not self.current_user:
                password = ""
                if auth_header := self.request.headers.get("Authorization"):
                    auth_scheme, _, auth_params = auth_header.partition(" ")
                    if auth_scheme == "Bearer":
                        password = auth_params

                if not password:
                    password = self.get_argument("token", default="")

                if not self.settings["is_valid_password"](password):
                    self.set_status(403)
                    self.auth_fail(bool(password))
                    return None
                self.set_signed_cookie(
                    self.settings["auth_cookie_name"](),
                    self.AUTH_COOKIE_VALUE,
                    expires_days=400,
                    httponly=True,
                    samesite="Strict",
                )
            return fn(self, *args, **kwargs)

        return wrapper

    def get_current_user(self) -> bool:
        return (
            self.get_signed_cookie(self.settings["auth_cookie_name"](), min_version=2)
            == self.AUTH_COOKIE_VALUE
        )


class RequestHandler(AuthRequestHandler):
    application: Application

    def write(self, chunk: str | bytes | dict | list):
        # Writing arrays on the top level is ok nowadays.
        # http://flask.pocoo.org/docs/0.11/security/#json-security
        if isinstance(chunk, list):
            chunk = tornado.escape.json_encode(chunk)
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        super().write(chunk)

    def set_default_headers(self):
        super().set_default_headers()
        self.set_header("Server", version.MITMPROXY)
        self.set_header("X-Frame-Options", "DENY")
        self.add_header("X-XSS-Protection", "1; mode=block")
        self.add_header("X-Content-Type-Options", "nosniff")
        self.add_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "connect-src 'self' ws:; "
            "style-src   'self' 'unsafe-inline'",
        )

    @property
    def json(self):
        if not self.request.headers.get("Content-Type", "").startswith(
            "application/json"
        ):
            raise APIError(400, "Invalid Content-Type, expected application/json.")
        try:
            return json.loads(self.request.body.decode())
        except Exception as e:
            raise APIError(400, f"Malformed JSON: {e}")

    @property
    def filecontents(self):
        """
        Accept either a multipart/form file upload or just take the plain request body.

        """
        if self.request.files:
            return next(iter(self.request.files.values()))[0].body
        else:
            return self.request.body

    @property
    def view(self) -> mitmproxy.addons.view.View:
        return self.application.master.view

    @property
    def master(self) -> mitmproxy.tools.web.master.WebMaster:
        return self.application.master

    @property
    def flow(self) -> mitmproxy.flow.Flow:
        flow_id = str(self.path_kwargs["flow_id"])
        # FIXME: Add a facility to addon.view to safely access the store
        flow = self.view.get_by_id(flow_id)
        if flow:
            return flow
        else:
            raise APIError(404, "Flow not found.")

    def write_error(self, status_code: int, **kwargs):
        if "exc_info" in kwargs and isinstance(kwargs["exc_info"][1], APIError):
            self.finish(kwargs["exc_info"][1].log_message)
        else:
            super().write_error(status_code, **kwargs)


class IndexHandler(RequestHandler):
    def _is_fetch_mode_navigate(self) -> bool:
        # Forbid access for non-navigate fetch modes so that they can't obtain xsrf_token.
        return self.request.headers.get("Sec-Fetch-Mode", "navigate") == "navigate"

    def auth_fail(self, invalid_password: bool) -> None:
        # For mitmweb, we only write a login form for IndexHandler,
        # which has additional Sec-Fetch-Mode protections.
        if self._is_fetch_mode_navigate():
            self.render("login.html", invalid_password=invalid_password)

    def get(self):
        # Forbid access for non-navigate fetch modes so that they can't obtain xsrf_token.
        if self._is_fetch_mode_navigate():
            self.render("index.html", xsrf_token=self.xsrf_token)
        else:
            raise APIError(
                status_codes.PRECONDITION_FAILED,
                f"Unexpected Sec-Fetch-Mode header: {self.request.headers.get('Sec-Fetch-Mode')}",
            )

    post = get  # login form


class FilterHelp(RequestHandler):
    def get(self):
        self.write(dict(commands=flowfilter.help))


class WebSocketEventBroadcaster(tornado.websocket.WebSocketHandler, AuthRequestHandler):
    # raise an error if inherited class doesn't specify its own instance.
    connections: ClassVar[set[WebSocketEventBroadcaster]]

    _send_queue: asyncio.Queue[bytes]
    _send_task: asyncio.Task[None]

    def open(self, *args, **kwargs):
        self.connections.add(self)
        self._send_queue = asyncio.Queue()
        # Python 3.13+: use _send_queue.shutdown() and we can use keep_ref=True here.
        self._send_task = asyncio_utils.create_task(
            self.send_task(),
            name="WebSocket send task",
            keep_ref=False,
        )

    def on_close(self):
        self.connections.discard(self)
        self._send_task.cancel()

    @classmethod
    def broadcast(cls, **kwargs):
        message = cls._json_dumps(kwargs)
        for conn in cls.connections:
            conn.send(message)

    def send(self, message: bytes):
        self._send_queue.put_nowait(message)

    async def send_task(self):
        while True:
            message = await self._send_queue.get()
            try:
                await self.write_message(message)
            except tornado.websocket.WebSocketClosedError:
                self.on_close()

    @staticmethod
    def _json_dumps(d):
        return json.dumps(d, ensure_ascii=False).encode("utf8", "surrogateescape")


class ClientConnection(WebSocketEventBroadcaster):
    connections: ClassVar[set[ClientConnection]] = set()  # type: ignore
    application: Application

    def __init__(self, application: Application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.filters: dict[str, flowfilter.TFilter] = {}  # filters per connection

    @classmethod
    def broadcast_flow_reset(cls) -> None:
        for conn in cls.connections:
            conn.send(cls._json_dumps({"type": "flows/reset"}))
            for name, expr in conn.filters.copy().items():
                conn.update_filter(name, expr.pattern)

    @classmethod
    def broadcast_flow(
        cls,
        type: Literal["flows/add", "flows/update"],
        f: mitmproxy.flow.Flow,
    ) -> None:
        flow_json = flow_to_json(f)
        for conn in cls.connections:
            conn._broadcast_flow(type, f, flow_json)

    def _broadcast_flow(
        self,
        type: Literal["flows/add", "flows/update"],
        f: mitmproxy.flow.Flow,
        flow_json: dict,  # Passing the flow_json dictionary to avoid recalculating it for each client
    ) -> None:
        filters = {name: bool(expr(f)) for name, expr in self.filters.items()}
        message = self._json_dumps(
            {
                "type": type,
                "payload": {
                    "flow": flow_json,
                    "matching_filters": filters,
                },
            },
        )
        self.send(message)

    def update_filter(self, name: str, expr: str) -> None:
        if expr:
            filt = flowfilter.parse(expr)
            self.filters[name] = filt
            matching_flow_ids = [f.id for f in self.application.master.view if filt(f)]
        else:
            self.filters.pop(name, None)
            matching_flow_ids = None

        message = self._json_dumps(
            {
                "type": "flows/filterUpdate",
                "payload": {
                    "name": name,
                    "matching_flow_ids": matching_flow_ids,
                },
            },
        )
        self.send(message=message)

    async def on_message(self, message: str | bytes):
        try:
            data = json.loads(message)
            match data["type"]:
                case "flows/updateFilter":
                    self.update_filter(data["payload"]["name"], data["payload"]["expr"])
                case other:
                    raise ValueError(f"Unsupported command: {other}")
        except Exception as e:
            logger.error(f"Error processing message from {self}: {e}")
            self.close(code=1011, reason="Internal server error.")


class Flows(RequestHandler):
    def get(self):
        self.write([flow_to_json(f) for f in self.view])


class DumpFlows(RequestHandler):
    def get(self) -> None:
        self.set_header("Content-Disposition", "attachment; filename=flows")
        self.set_header("Content-Type", "application/octet-stream")

        match: Callable[[mitmproxy.flow.Flow], bool]
        try:
            match = flowfilter.parse(self.request.arguments["filter"][0].decode())
        except ValueError:  # thrown py flowfilter.parse if filter is invalid
            raise APIError(400, f"Invalid filter argument / regex")
        except (
            KeyError,
            IndexError,
        ):  # Key+Index: ["filter"][0] can fail, if it's not set

            def match(_) -> bool:
                return True

        with BytesIO() as bio:
            fw = io.FlowWriter(bio)
            for f in self.view:
                if match(f):
                    fw.add(f)
            self.write(bio.getvalue())

    async def post(self):
        self.view.clear()
        bio = BytesIO(self.filecontents)
        for f in io.FlowReader(bio).stream():
            await self.master.load_flow(f)
        bio.close()


class ClearAll(RequestHandler):
    def post(self):
        self.view.clear()
        self.master.events.clear()


class ResumeFlows(RequestHandler):
    def post(self):
        for f in self.view:
            if not f.intercepted:
                continue
            f.resume()
            self.view.update([f])


class KillFlows(RequestHandler):
    def post(self):
        for f in self.view:
            if f.killable:
                f.kill()
                self.view.update([f])


class ResumeFlow(RequestHandler):
    def post(self, flow_id):
        self.flow.resume()
        self.view.update([self.flow])


class KillFlow(RequestHandler):
    def post(self, flow_id):
        if self.flow.killable:
            self.flow.kill()
            self.view.update([self.flow])


class FlowHandler(RequestHandler):
    def delete(self, flow_id):
        if self.flow.killable:
            self.flow.kill()
        self.view.remove([self.flow])

    def put(self, flow_id) -> None:
        flow: mitmproxy.flow.Flow = self.flow
        flow.backup()
        try:
            for a, b in self.json.items():
                if a == "request" and hasattr(flow, "request"):
                    request: mitmproxy.http.Request = flow.request
                    for k, v in b.items():
                        if k in ["method", "scheme", "host", "path", "http_version"]:
                            setattr(request, k, str(v))
                        elif k == "port":
                            request.port = int(v)
                        elif k == "headers":
                            request.headers.clear()
                            for header in v:
                                request.headers.add(*header)
                        elif k == "trailers":
                            if request.trailers is not None:
                                request.trailers.clear()
                            else:
                                request.trailers = mitmproxy.http.Headers()
                            for trailer in v:
                                request.trailers.add(*trailer)
                        elif k == "content":
                            request.text = v
                        else:
                            raise APIError(400, f"Unknown update request.{k}: {v}")

                elif a == "response" and hasattr(flow, "response"):
                    response: mitmproxy.http.Response = flow.response
                    for k, v in b.items():
                        if k in ["msg", "http_version"]:
                            setattr(response, k, str(v))
                        elif k == "code":
                            response.status_code = int(v)
                        elif k == "headers":
                            response.headers.clear()
                            for header in v:
                                response.headers.add(*header)
                        elif k == "trailers":
                            if response.trailers is not None:
                                response.trailers.clear()
                            else:
                                response.trailers = mitmproxy.http.Headers()
                            for trailer in v:
                                response.trailers.add(*trailer)
                        elif k == "content":
                            response.text = v
                        else:
                            raise APIError(400, f"Unknown update response.{k}: {v}")
                elif a == "marked":
                    flow.marked = b
                elif a == "comment":
                    flow.comment = b
                else:
                    raise APIError(400, f"Unknown update {a}: {b}")
        except APIError:
            flow.revert()
            raise
        self.view.update([flow])


class DuplicateFlow(RequestHandler):
    def post(self, flow_id):
        f = self.flow.copy()
        self.view.add([f])
        self.write(f.id)


class RevertFlow(RequestHandler):
    def post(self, flow_id):
        if self.flow.modified():
            self.flow.revert()
            self.view.update([self.flow])


class ReplayFlow(RequestHandler):
    def post(self, flow_id):
        self.master.commands.call("replay.client", [self.flow])


class FlowContent(RequestHandler):
    def post(self, flow_id, message):
        self.flow.backup()
        message = getattr(self.flow, message)
        message.content = self.filecontents
        self.view.update([self.flow])

    def get(self, flow_id, message):
        message = getattr(self.flow, message)
        assert isinstance(self.flow, HTTPFlow)

        original_cd = message.headers.get("Content-Disposition", None)
        filename = None
        if original_cd:
            if m := re.search(r'filename=([-\w" .()]+)', original_cd):
                filename = m.group(1)
        if not filename:
            filename = self.flow.request.path.split("?")[0].split("/")[-1]

        filename = re.sub(r'[^-\w" .()]', "", filename)
        cd = f"attachment; {filename=!s}"
        self.set_header("Content-Disposition", cd)
        self.set_header("Content-Type", "application/text")
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("X-Frame-Options", "DENY")
        self.write(message.get_content(strict=False))


class FlowContentView(RequestHandler):
    def message_to_json(
        self,
        view_name: str,
        message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
        flow: HTTPFlow | TCPFlow | UDPFlow,
        max_lines: int | None = None,
        from_client: bool | None = None,
        timestamp: float | None = None,
    ):
        if view_name and view_name.lower() == "auto":
            view_name = "auto"
        pretty = contentviews.prettify_message(message, flow, view_name=view_name)
        if max_lines:
            pretty.text = cut_after_n_lines(pretty.text, max_lines)

        ret: dict[str, Any] = dict(
            text=pretty.text,
            view_name=pretty.view_name,
            syntax_highlight=pretty.syntax_highlight,
            description=pretty.description,
        )
        if from_client is not None:
            ret["from_client"] = from_client
        if timestamp is not None:
            ret["timestamp"] = timestamp
        return ret

    def get(self, flow_id, message, content_view) -> None:
        flow = self.flow
        assert isinstance(flow, (HTTPFlow, TCPFlow, UDPFlow))

        if self.request.arguments.get("lines"):
            max_lines = int(self.request.arguments["lines"][0])
        else:
            max_lines = None

        if message == "messages":
            messages: list[TCPMessage] | list[UDPMessage] | list[WebSocketMessage]
            if isinstance(flow, HTTPFlow) and flow.websocket:
                messages = flow.websocket.messages
            elif isinstance(flow, (TCPFlow, UDPFlow)):
                messages = flow.messages
            else:
                raise APIError(400, f"This flow has no messages.")
            msgs = []
            for m in messages:
                d = self.message_to_json(
                    view_name=content_view,
                    message=m,
                    flow=flow,
                    max_lines=max_lines,
                    from_client=m.from_client,
                    timestamp=m.timestamp,
                )
                msgs.append(d)
                if max_lines:
                    max_lines -= d["text"].count("\n") + 1
                    assert max_lines is not None
                    if max_lines <= 0:
                        break
            self.write(msgs)
        else:
            message = getattr(self.flow, message)
            self.write(self.message_to_json(content_view, message, flow, max_lines))


class Commands(RequestHandler):
    def get(self) -> None:
        commands = {}
        for name, cmd in self.master.commands.commands.items():
            commands[name] = {
                "help": cmd.help,
                "parameters": [
                    {
                        "name": param.name,
                        "type": command.typename(param.type),
                        "kind": str(param.kind),
                    }
                    for param in cmd.parameters
                ],
                "return_type": command.typename(cmd.return_type)
                if cmd.return_type
                else None,
                "signature_help": cmd.signature_help(),
            }
        self.write(commands)


class ExecuteCommand(RequestHandler):
    def post(self, cmd: str):
        # TODO: We should parse query strings here, this API is painful.
        try:
            args = self.json["arguments"]
        except APIError:
            args = []
        try:
            result = self.master.commands.call_strings(cmd, args)
        except Exception as e:
            self.write({"error": str(e)})
        else:
            self.write(
                {
                    "value": result,
                    # "type": command.typename(type(result)) if result is not None else "none"
                }
            )


class Events(RequestHandler):
    def get(self):
        self.write([logentry_to_json(e) for e in self.master.events.data])


class Options(RequestHandler):
    def get(self):
        self.write(optmanager.dump_dicts(self.master.options))

    def put(self):
        update = self.json
        try:
            self.master.options.update(**update)
        except Exception as err:
            raise APIError(400, f"{err}")


class SaveOptions(RequestHandler):
    def post(self):
        # try:
        #     optmanager.save(self.master.options, CONFIG_PATH, True)
        # except Exception as err:
        #     raise APIError(400, "{}".format(err))
        pass


class State(RequestHandler):
    # Separate method for testability.
    @staticmethod
    def get_json(master: mitmproxy.tools.web.master.WebMaster):
        return {
            "version": version.VERSION,
            "contentViews": [
                v for v in contentviews.registry.available_views() if v != "query"
            ],
            "servers": {
                s.mode.full_spec: s.to_json() for s in master.proxyserver.servers
            },
            "platform": sys.platform,
            "localModeUnavailable": mitmproxy_rs.local.LocalRedirector.unavailable_reason(),
        }

    def get(self):
        self.write(State.get_json(self.master))


class ProcessList(RequestHandler):
    @staticmethod
    def get_json():
        processes = mitmproxy_rs.process_info.active_executables()
        return [
            {
                "is_visible": process.is_visible,
                "executable": str(process.executable),
                "is_system": process.is_system,
                "display_name": process.display_name,
            }
            for process in processes
        ]

    def get(self):
        self.write(ProcessList.get_json())


class ProcessImage(RequestHandler):
    def get(self):
        path = self.get_query_argument("path", None)

        if not path:
            raise APIError(400, "Missing 'path' parameter.")

        try:
            icon_bytes = mitmproxy_rs.process_info.executable_icon(path)
        except Exception:
            icon_bytes = TRANSPARENT_PNG

        self.set_header("Content-Type", "image/png")
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("Cache-Control", "max-age=604800")
        self.write(icon_bytes)


class GZipContentAndFlowFiles(tornado.web.GZipContentEncoding):
    CONTENT_TYPES = {
        "application/octet-stream",
        *tornado.web.GZipContentEncoding.CONTENT_TYPES,
    }


handlers = [
    (r"/", IndexHandler),
    (r"/filter-help(?:\.json)?", FilterHelp),
    (r"/updates", ClientConnection),
    (r"/commands(?:\.json)?", Commands),
    (r"/commands/(?P<cmd>[a-z.]+)", ExecuteCommand),
    (r"/events(?:\.json)?", Events),
    (r"/flows(?:\.json)?", Flows),
    (r"/flows/dump", DumpFlows),
    (r"/flows/resume", ResumeFlows),
    (r"/flows/kill", KillFlows),
    (r"/flows/(?P<flow_id>[0-9a-f\-]+)", FlowHandler),
    (r"/flows/(?P<flow_id>[0-9a-f\-]+)/resume", ResumeFlow),
    (r"/flows/(?P<flow_id>[0-9a-f\-]+)/kill", KillFlow),
    (r"/flows/(?P<flow_id>[0-9a-f\-]+)/duplicate", DuplicateFlow),
    (r"/flows/(?P<flow_id>[0-9a-f\-]+)/replay", ReplayFlow),
    (r"/flows/(?P<flow_id>[0-9a-f\-]+)/revert", RevertFlow),
    (r"/flows/(?P<flow_id>[0-9a-f\-]+)/(?P<message>request|response|messages)/content.data", FlowContent),
    (r"/flows/(?P<flow_id>[0-9a-f\-]+)/(?P<message>request|response|messages)/content/(?P<content_view>[0-9a-zA-Z\-\_%]+)(?:\.json)?", FlowContentView),
    (r"/clear", ClearAll),
    (r"/options(?:\.json)?", Options),
    (r"/options/save", SaveOptions),
    (r"/state(?:\.json)?", State),
    (r"/processes", ProcessList),
    (r"/executable-icon", ProcessImage),
]  # fmt: skip


class Application(tornado.web.Application):
    master: mitmproxy.tools.web.master.WebMaster

    def __init__(
        self, master: mitmproxy.tools.web.master.WebMaster, debug: bool
    ) -> None:
        self.master = master
        auth_addon: WebAuth = master.addons.get("webauth")
        super().__init__(
            handlers=handlers,  # type: ignore  # https://github.com/tornadoweb/tornado/pull/3455
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            xsrf_cookie_kwargs=dict(httponly=True, samesite="Strict"),
            cookie_secret=secrets.token_bytes(32),
            debug=debug,
            autoreload=False,
            transforms=[GZipContentAndFlowFiles],
            is_valid_password=auth_addon.is_valid_password,
            auth_cookie_name=auth_addon.auth_cookie_name,
        )
