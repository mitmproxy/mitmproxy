import os.path
import tornado.web
import tornado.websocket
import logging
import json


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")


class ClientConnection(tornado.websocket.WebSocketHandler):
    connections = set()

    def open(self):
        ClientConnection.connections.add(self)

    def on_close(self):
        ClientConnection.connections.remove(self)

    @classmethod
    def broadcast(cls, type, data):
        for conn in cls.connections:
            try:
                conn.write_message(
                    json.dumps(
                        {
                            "type": type,
                            "data": data
                        }
                    )
                )
            except:
                logging.error("Error sending message", exc_info=True)


class Application(tornado.web.Application):
    def __init__(self, debug):
        handlers = [
            (r"/", IndexHandler),
            (r"/updates", ClientConnection),
        ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            debug=debug,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

