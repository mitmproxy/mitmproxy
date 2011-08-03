import os.path, threading, Queue
import libpry
from libmproxy import proxy, filt, flow, controller
import serv, sslserv
import random

def treq(conn=None):
    if not conn:
        conn = flow.ClientConnect(("address", 22))
    headers = flow.Headers()
    headers["header"] = ["qvalue"]
    return flow.Request(conn, "host", 80, "http", "GET", "/path", headers, "content")


def tresp(req=None):
    if not req:
        req = treq()
    headers = flow.Headers()
    headers["header_response"] = ["svalue"]
    return flow.Response(req, 200, "message", headers, "content_response")


def tflow():
    r = treq()
    return flow.Flow(r)


def tflow_full():
    r = treq()
    f = flow.Flow(r)
    f.response = tresp(r)
    return f


def tflow_err():
    r = treq()
    f = flow.Flow(r)
    f.error = flow.Error(r, "error")
    return f


# Yes, the random ports are horrible. During development, sockets are often not
# properly closed during error conditions, which means you have to wait until
# you can re-bind to the same port. This is a pain in the ass, so we just pick
# a random port and keep moving.
PROXL_PORT = random.randint(10000, 20000)
HTTP_PORT = random.randint(20000, 30000)
HTTPS_PORT = random.randint(30000, 40000)


class TestMaster(controller.Master):
    def __init__(self, port, testq):
        serv = proxy.ProxyServer(proxy.SSLConfig("data/testkey.pem"), port)
        controller.Master.__init__(self, serv)
        self.testq = testq
        self.log = []

    def clear(self):
        self.log = []

    def handle(self, m):
        self.log.append(m)
        m._ack()


class ProxyThread(threading.Thread):
    def __init__(self, port, testq):
        self.tmaster = TestMaster(port, testq)
        controller.should_exit = False
        threading.Thread.__init__(self)

    def run(self):
        self.tmaster.run()

    def shutdown(self):
        self.tmaster.shutdown()


class ServerThread(threading.Thread):
    def __init__(self, server):
        self.server = server
        threading.Thread.__init__(self)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class TestServers(libpry.TestContainer):
    def setUpAll(self):
        self.tqueue = Queue.Queue()
        # We don't make any concurrent requests, so we can access
        # the attributes on this object safely.
        self.proxthread = ProxyThread(PROXL_PORT, self.tqueue)
        self.threads = [
            ServerThread(serv.make(HTTP_PORT)),
            ServerThread(sslserv.make(HTTPS_PORT)),
            self.proxthread
        ]
        for i in self.threads:
            i.start()

    def setUp(self):
        self.proxthread.tmaster.clear()

    def tearDownAll(self):
        for i in self.threads:
            i.shutdown()


class ProxTest(libpry.AutoTree):
    def log(self):
        pthread = self.findAttr("proxthread")
        return pthread.tmaster.log

