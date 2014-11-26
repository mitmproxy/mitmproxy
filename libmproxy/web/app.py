import os.path
import tornado.web
import tornado.websocket
import logging
import json
from .. import flow


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


class WebSocketEventBroadcaster(tornado.websocket.WebSocketHandler):
    connections = None  # raise an error if inherited class doesn't specify its own instance.

    def open(self):
        self.connections.add(self)

    def on_close(self):
        self.connections.remove(self)

    @classmethod
    def broadcast(cls, type, data):
        message = json.dumps(
            {
                "type": type,
                "data": data
            }
        )
        for conn in cls.connections:
            try:
                conn.write_message(message)
            except:
                logging.error("Error sending message", exc_info=True)


class FlowsHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(dict(
            flows=[f.get_state(short=True) for f in self.application.state.flows]
        ))


class FlowUpdates(WebSocketEventBroadcaster):
    connections = set()


class ClientConnection(WebSocketEventBroadcaster):
    connections = set()


class Application(tornado.web.Application):
    def __init__(self, state, debug):
        self.state = state
        handlers = [
            (r"/", IndexHandler),
            (r"/updates", ClientConnection),
            (r"/flows", FlowsHandler),
            (r"/flows/updates", FlowUpdates),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            debug=debug,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

