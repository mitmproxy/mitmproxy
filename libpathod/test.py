import json, threading, Queue
import requests
import pathod

IFACE = "127.0.0.1"

class PaThread(threading.Thread):
    def __init__(self, q, app):
        threading.Thread.__init__(self)
        self.q = q
        self.app = app
        self.port = None

    def run(self):
        self.server, self.port = pathod.make_server(self.app, 0, IFACE, None)
        self.q.put(self.port)
        pathod.run(self.server)


class Daemon:
    def __init__(self, staticdir=None, anchors=()):
        self.app = pathod.make_app(staticdir=staticdir, anchors=anchors)
        self.q = Queue.Queue()
        self.thread = PaThread(self.q, self.app)
        self.thread.start()
        self.port = self.q.get(True, 5)
        self.urlbase = "http://%s:%s"%(IFACE, self.port)

    def info(self):
        resp = requests.get("%s/api/info"%self.urlbase)
        if resp.ok:
            return json.loads(resp.read())

    def shutdown(self):
        requests.post("%s/api/shutdown"%self.urlbase)
