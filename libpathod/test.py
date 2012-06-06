import threading
import requests
import Queue
import pathod

class PaThread(threading.Thread):
    def __init__(self, q, app):
        threading.Thread.__init__(self)
        self.q = q
        self.app = app
        self.port = None

    def run(self):
        self.server, self.port = pathod.make_server(self.app, 0, "127.0.0.1", None)
        self.q.put(self.port)
        pathod.run(self.server)


class Daemon:
    def __init__(self, staticdir=None, anchors=()):
        self.app = pathod.make_app(staticdir=staticdir, anchors=anchors)
        self.q = Queue.Queue()
        self.thread = PaThread(self.q, self.app)
        self.thread.start()
        self.port = self.q.get(True, 5)

    def clear(self):
        pass

    def shutdown(self):
        requests.post("http://localhost:%s/api/shutdown"%self.port)
