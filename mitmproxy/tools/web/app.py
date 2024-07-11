from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os.path
import re
from collections.abc import Callable
from collections.abc import Sequence
from io import BytesIO
from itertools import islice
from typing import ClassVar

import tornado.escape
import tornado.web
import tornado.websocket

import mitmproxy.flow
import mitmproxy.tools.web.master
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
from mitmproxy.tcp import TCPFlow
from mitmproxy.tcp import TCPMessage
from mitmproxy.udp import UDPFlow
from mitmproxy.udp import UDPMessage
from mitmproxy.utils.emoji import emoji
from mitmproxy.utils.strutils import always_str
from mitmproxy.websocket import WebSocketMessage


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


class RequestHandler(tornado.web.RequestHandler):
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
            raise APIError(400, f"Malformed JSON: {str(e)}")

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
    def get(self):
        token = self.xsrf_token  # https://github.com/tornadoweb/tornado/issues/645
        assert token
        self.render("index.html")


class FilterHelp(RequestHandler):
    def get(self):
        self.write(dict(commands=flowfilter.help))


class WebSocketEventBroadcaster(tornado.websocket.WebSocketHandler):
    # raise an error if inherited class doesn't specify its own instance.
    connections: ClassVar[set[WebSocketEventBroadcaster]]
    _send_tasks: ClassVar[set[asyncio.Task]] = set()

    def open(self):
        self.connections.add(self)

    def on_close(self):
        self.connections.discard(self)

    @classmethod
    def send(cls, conn: WebSocketEventBroadcaster, message: bytes) -> None:
        async def wrapper():
            try:
                await conn.write_message(message)
            except tornado.websocket.WebSocketClosedError:
                cls.connections.discard(conn)

        t = asyncio.create_task(wrapper())
        cls._send_tasks.add(t)
        t.add_done_callback(cls._send_tasks.remove)

    @classmethod
    def broadcast(cls, **kwargs):
        message = json.dumps(kwargs, ensure_ascii=False).encode(
            "utf8", "surrogateescape"
        )

        for conn in cls.connections.copy():
            cls.send(conn, message)


class ClientConnection(WebSocketEventBroadcaster):
    connections: ClassVar[set] = set()


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
        cd = f"attachment; filename={filename}"
        self.set_header("Content-Disposition", cd)
        self.set_header("Content-Type", "application/text")
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("X-Frame-Options", "DENY")
        self.write(message.get_content(strict=False))


class FlowContentView(RequestHandler):
    def message_to_json(
        self,
        viewname: str,
        message: http.Message | TCPMessage | UDPMessage | WebSocketMessage,
        flow: HTTPFlow | TCPFlow | UDPFlow,
        max_lines: int | None = None,
    ):
        description, lines, error = contentviews.get_message_content_view(
            viewname, message, flow
        )
        if error:
            logging.error(error)
        if max_lines:
            lines = islice(lines, max_lines)

        return dict(
            lines=list(lines),
            description=description,
        )

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
                d = self.message_to_json(content_view, m, flow, max_lines)
                d["from_client"] = m.from_client
                d["timestamp"] = m.timestamp
                msgs.append(d)
                if max_lines:
                    max_lines -= len(d["lines"])
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


class DnsRebind(RequestHandler):
    def get(self):
        raise tornado.web.HTTPError(
            403,
            reason="To protect against DNS rebinding, mitmweb can only be accessed by IP at the moment. "
            "(https://github.com/mitmproxy/mitmproxy/issues/3234)",
        )


class State(RequestHandler):
    # Separate method for testability.
    @staticmethod
    def get_json(master: mitmproxy.tools.web.master.WebMaster):
        return {
            "version": version.VERSION,
            "contentViews": [v.name for v in contentviews.views if v.name != "Query"],
            "servers": [s.to_json() for s in master.proxyserver.servers],
        }

    def get(self):
        self.write(State.get_json(self.master))


class GZipContentAndFlowFiles(tornado.web.GZipContentEncoding):
    CONTENT_TYPES = {
        "application/octet-stream",
        *tornado.web.GZipContentEncoding.CONTENT_TYPES,
    }


class Application(tornado.web.Application):
    master: mitmproxy.tools.web.master.WebMaster

    def __init__(
        self, master: mitmproxy.tools.web.master.WebMaster, debug: bool
    ) -> None:
        self.master = master
        super().__init__(
            default_host="dns-rebind-protection",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret=os.urandom(256),
            debug=debug,
            autoreload=False,
            transforms=[GZipContentAndFlowFiles],
        )

        self.add_handlers("dns-rebind-protection", [(r"/.*", DnsRebind)])
        self.add_handlers(
            # make mitmweb accessible by IP only to prevent DNS rebinding.
            r"^(localhost|[0-9.]+|\[[0-9a-fA-F:]+\])$",
            [
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
                (
                    r"/flows/(?P<flow_id>[0-9a-f\-]+)/(?P<message>request|response|messages)/content.data",
                    FlowContent,
                ),
                (
                    r"/flows/(?P<flow_id>[0-9a-f\-]+)/(?P<message>request|response|messages)/"
                    r"content/(?P<content_view>[0-9a-zA-Z\-\_%]+)(?:\.json)?",
                    FlowContentView,
                ),
                (r"/clear", ClearAll),
                (r"/options(?:\.json)?", Options),
                (r"/options/save", SaveOptions),
                (r"/state(?:\.json)?", State),
            ],
        )
