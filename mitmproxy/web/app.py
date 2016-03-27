import os.path
import re

import six
import tornado.web
import tornado.websocket
import logging
import json
import base64

from .. import version, filt


def _strip_content(flow_state):
    """
    Remove flow message content and cert to save transmission space.

    Args:
        flow_state: The original flow state. Will be left unmodified
    """
    for attr in ("request", "response"):
        if attr in flow_state:
            message = flow_state[attr]
            if message is None:
                continue
            if message["content"]:
                message["contentLength"] = len(message["content"])
            else:
                message["contentLength"] = None
            del message["content"]

    if "backup" in flow_state:
        del flow_state["backup"]
        flow_state["modified"] = True

    flow_state.get("server_conn", {}).pop("cert", None)

    return flow_state


class APIError(tornado.web.HTTPError):
    pass


class BasicAuth(object):

    def set_auth_headers(self):
        self.set_status(401)
        self.set_header('WWW-Authenticate', 'Basic realm=MITMWeb')
        self._transforms = []
        self.finish()

    def prepare(self):
        wauthenticator = self.application.settings['wauthenticator']
        if wauthenticator:
            auth_header = self.request.headers.get('Authorization')
            if auth_header is None or not auth_header.startswith('Basic '):
                self.set_auth_headers()
            else:
                self.auth_decoded = base64.decodestring(auth_header[6:])
                self.username, self.password = self.auth_decoded.split(':', 2)
                if not wauthenticator.test(self.username, self.password):
                    self.set_auth_headers()
                    raise APIError(401, "Invalid username or password.")


class RequestHandler(BasicAuth, tornado.web.RequestHandler):

    def set_default_headers(self):
        super(RequestHandler, self).set_default_headers()
        self.set_header("Server", version.NAMEVERSION)
        self.set_header("X-Frame-Options", "DENY")
        self.add_header("X-XSS-Protection", "1; mode=block")
        self.add_header("X-Content-Type-Options", "nosniff")
        self.add_header(
            "Content-Security-Policy",
            "default-src 'self'; "
            "connect-src 'self' ws://* ; "
            "style-src   'self' 'unsafe-inline'"
        )

    @property
    def json(self):
        if not self.request.headers.get("Content-Type").startswith("application/json"):
            return None
        return json.loads(self.request.body)

    @property
    def state(self):
        return self.application.master.state

    @property
    def master(self):
        return self.application.master

    @property
    def flow(self):
        flow_id = str(self.path_kwargs["flow_id"])
        flow = self.state.flows.get(flow_id)
        if flow:
            return flow
        else:
            raise APIError(400, "Flow not found.")

    def write_error(self, status_code, **kwargs):
        if "exc_info" in kwargs and isinstance(kwargs["exc_info"][1], APIError):
            self.finish(kwargs["exc_info"][1].log_message)
        else:
            super(RequestHandler, self).write_error(status_code, **kwargs)


class IndexHandler(RequestHandler):

    def get(self):
        _ = self.xsrf_token  # https://github.com/tornadoweb/tornado/issues/645
        self.render("index.html")


class FiltHelp(RequestHandler):

    def get(self):
        self.write(dict(
            commands=filt.help
        ))


class WebSocketEventBroadcaster(BasicAuth, tornado.websocket.WebSocketHandler):
    # raise an error if inherited class doesn't specify its own instance.
    connections = None

    def open(self):
        self.connections.add(self)

    def on_close(self):
        self.connections.remove(self)

    @classmethod
    def broadcast(cls, **kwargs):
        message = json.dumps(kwargs, ensure_ascii=False)

        for conn in cls.connections:
            try:
                conn.write_message(message)
            except:
                logging.error("Error sending message", exc_info=True)


class ClientConnection(WebSocketEventBroadcaster):
    connections = set()


class Flows(RequestHandler):

    def get(self):
        self.write(dict(
            data=[_strip_content(f.get_state()) for f in self.state.flows]
        ))


class ClearAll(RequestHandler):

    def post(self):
        self.state.clear()


class AcceptFlows(RequestHandler):

    def post(self):
        self.state.flows.accept_all(self.master)


class AcceptFlow(RequestHandler):

    def post(self, flow_id):
        self.flow.accept_intercept(self.master)


class FlowHandler(RequestHandler):

    def delete(self, flow_id):
        self.flow.kill(self.master)
        self.state.delete_flow(self.flow)

    def put(self, flow_id):
        flow = self.flow
        flow.backup()
        for a, b in six.iteritems(self.json):

            if a == "request":
                request = flow.request
                for k, v in six.iteritems(b):
                    if k in ["method", "scheme", "host", "path", "http_version"]:
                        setattr(request, k, str(v))
                    elif k == "port":
                        request.port = int(v)
                    elif k == "headers":
                        request.headers.set_state(v)
                    else:
                        print "Warning: Unknown update {}.{}: {}".format(a, k, v)

            elif a == "response":
                response = flow.response
                for k, v in six.iteritems(b):
                    if k == "msg":
                        response.msg = str(v)
                    elif k == "code":
                        response.status_code = int(v)
                    elif k == "http_version":
                        response.http_version = str(v)
                    elif k == "headers":
                        response.headers.set_state(v)
                    else:
                        print "Warning: Unknown update {}.{}: {}".format(a, k, v)
            else:
                print "Warning: Unknown update {}: {}".format(a, b)
        self.state.update_flow(flow)


class DuplicateFlow(RequestHandler):

    def post(self, flow_id):
        self.master.duplicate_flow(self.flow)


class RevertFlow(RequestHandler):

    def post(self, flow_id):
        self.state.revert(self.flow)


class ReplayFlow(RequestHandler):

    def post(self, flow_id):
        self.flow.backup()
        self.flow.response = None
        self.state.update_flow(self.flow)

        r = self.master.replay_request(self.flow)
        if r:
            raise APIError(400, r)


class FlowContent(RequestHandler):

    def get(self, flow_id, message):
        message = getattr(self.flow, message)

        if not message.content:
            raise APIError(400, "No content.")

        content_encoding = message.headers.get("Content-Encoding", None)
        if content_encoding:
            content_encoding = re.sub(r"[^\w]", "", content_encoding)
            self.set_header("Content-Encoding", content_encoding)

        original_cd = message.headers.get("Content-Disposition", None)
        filename = None
        if original_cd:
            filename = re.search("filename=([\w\" \.\-\(\)]+)", original_cd)
            if filename:
                filename = filename.group(1)
        if not filename:
            filename = self.flow.request.path.split("?")[0].split("/")[-1]

        filename = re.sub(r"[^\w\" \.\-\(\)]", "", filename)
        cd = "attachment; filename={}".format(filename)
        self.set_header("Content-Disposition", cd)
        self.set_header("Content-Type", "application/text")
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("X-Frame-Options", "DENY")
        self.write(message.content)


class Events(RequestHandler):

    def get(self):
        self.write(dict(
            data=list(self.state.events)
        ))


class Settings(RequestHandler):

    def get(self):
        self.write(dict(
            data=dict(
                version=version.VERSION,
                mode=str(self.master.server.config.mode),
                intercept=self.state.intercept_txt
            )
        ))

    def put(self):
        update = {}
        for k, v in six.iteritems(self.json):
            if k == "intercept":
                self.state.set_intercept(v)
                update[k] = v
            else:
                print("Warning: Unknown setting {}: {}".format(k, v))

        ClientConnection.broadcast(
            type="settings",
            cmd="update",
            data=update
        )


class Application(tornado.web.Application):

    def __init__(self, master, debug, wauthenticator):
        self.master = master
        handlers = [
            (r"/", IndexHandler),
            (r"/filter-help", FiltHelp),
            (r"/updates", ClientConnection),
            (r"/events", Events),
            (r"/flows", Flows),
            (r"/flows/accept", AcceptFlows),
            (r"/flows/(?P<flow_id>[0-9a-f\-]+)", FlowHandler),
            (r"/flows/(?P<flow_id>[0-9a-f\-]+)/accept", AcceptFlow),
            (r"/flows/(?P<flow_id>[0-9a-f\-]+)/duplicate", DuplicateFlow),
            (r"/flows/(?P<flow_id>[0-9a-f\-]+)/replay", ReplayFlow),
            (r"/flows/(?P<flow_id>[0-9a-f\-]+)/revert", RevertFlow),
            (r"/flows/(?P<flow_id>[0-9a-f\-]+)/(?P<message>request|response)/content", FlowContent),
            (r"/settings", Settings),
            (r"/clear", ClearAll),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret=os.urandom(256),
            debug=debug,
            wauthenticator=wauthenticator,
        )
        super(Application, self).__init__(handlers, **settings)
