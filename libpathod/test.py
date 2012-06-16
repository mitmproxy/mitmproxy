import json, threading, Queue
import requests
import pathod, utils
import tutils

IFACE = "127.0.0.1"

class Daemon:
    def __init__(self, staticdir=None, anchors=(), ssl=None):
        self.app = pathod.make_app(staticdir=staticdir, anchors=anchors)
        self.q = Queue.Queue()
        self.thread = PaThread(self.q, self.app, ssl)
        self.thread.start()
        self.port = self.q.get(True, 5)
        self.urlbase = "%s://%s:%s"%("https" if ssl else "http", IFACE, self.port)

    def info(self):
        resp = requests.get("%s/api/info"%self.urlbase, verify=False)
        return resp.json

    def shutdown(self):
        requests.post("%s/api/shutdown"%self.urlbase, verify=False)
        self.thread.join()


class PaThread(threading.Thread):
    def __init__(self, q, app, ssl):
        threading.Thread.__init__(self)
        self.q, self.app, self.ssl = q, app, ssl
        self.port = None

    def run(self):
        if self.ssl is True:
            ssloptions = dict(
                 keyfile = utils.data.path("resources/server.key"),
                 certfile = utils.data.path("resources/server.crt"),
            )
        else:
            ssloptions = self.ssl
        self.server, self.port = pathod.make_server(self.app, 0, IFACE, ssloptions)
        self.q.put(self.port)
        pathod.run(self.server)
