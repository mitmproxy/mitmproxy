import os.path
import sys
import tornado.web
import tornado.websocket
import logging
import json
from .. import flow


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        _ = self.xsrf_token  # https://github.com/tornadoweb/tornado/issues/645
        self.render("index.html")


class WebSocketEventBroadcaster(tornado.websocket.WebSocketHandler):
    connections = None  # raise an error if inherited class doesn't specify its own instance.

    def open(self):
        self.connections.add(self)

    def on_close(self):
        self.connections.remove(self)

    @classmethod
    def broadcast(cls, **kwargs):
        message = json.dumps(kwargs)
        for conn in cls.connections:
            try:
                conn.write_message(message)
            except:
                logging.error("Error sending message", exc_info=True)


class Flows(tornado.web.RequestHandler):
    def get(self):
        self.write(dict(
            data=[f.get_state(short=True) for f in self.application.state.flows]
        ))

class Events(tornado.web.RequestHandler):
    def get(self):
        self.write(dict(
            data=list(self.application.state.events)
        ))


class Settings(tornado.web.RequestHandler):
    def get(self):
        self.write(dict(
            data=dict(
                showEventLog=True
            )
        ))


class Clear(tornado.web.RequestHandler):
    def post(self):
        self.application.state.clear()


class ClientConnection(WebSocketEventBroadcaster):
    connections = set()


class Application(tornado.web.Application):
    def __init__(self, state, debug):
        self.state = state
        handlers = [
            (r"/", IndexHandler),
            (r"/updates", ClientConnection),
            (r"/events", Events),
            (r"/flows", Flows),
            (r"/settings", Settings),
            (r"/clear", Clear),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret=os.urandom(256),
            debug=debug,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

