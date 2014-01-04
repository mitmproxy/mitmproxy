import threading, Queue
import flask
import libpathod.test, libpathod.pathoc
from libmproxy import proxy, flow, controller
from libmproxy.cmdline import APP_HOST, APP_PORT
import tutils

testapp = flask.Flask(__name__)

@testapp.route("/")
def hello():
    return "testapp"

@testapp.route("/error")
def error():
    raise ValueError("An exception...")


def errapp(environ, start_response):
    raise ValueError("errapp")


class TestMaster(flow.FlowMaster):
    def __init__(self, testq, config):
        s = proxy.ProxyServer(config, 0)
        state = flow.State()
        flow.FlowMaster.__init__(self, s, state)
        self.apps.add(testapp, "testapp", 80)
        self.apps.add(errapp, "errapp", 80)
        self.testq = testq
        self.clear_log()
        self.start_app(APP_HOST, APP_PORT, False)

    def handle_request(self, m):
        flow.FlowMaster.handle_request(self, m)
        m.reply()

    def handle_response(self, m):
        flow.FlowMaster.handle_response(self, m)
        m.reply()

    def clear_log(self):
        self.log = []

    def handle_log(self, l):
        self.log.append(l.msg)
        l.reply()


class ProxyThread(threading.Thread):
    def __init__(self, tmaster):
        threading.Thread.__init__(self)
        self.tmaster = tmaster
        controller.should_exit = False

    @property
    def port(self):
        return self.tmaster.server.port

    @property
    def log(self):
        return self.tmaster.log

    def run(self):
        self.tmaster.run()

    def shutdown(self):
        self.tmaster.shutdown()


class ProxTestBase:
    # Test Configuration
    ssl = None
    ssloptions = False
    clientcerts = False
    certfile = None
    no_upstream_cert = False
    authenticator = None
    masterclass = TestMaster
    @classmethod
    def setupAll(cls):
        cls.tqueue = Queue.Queue()
        cls.server = libpathod.test.Daemon(ssl=cls.ssl, ssloptions=cls.ssloptions)
        cls.server2 = libpathod.test.Daemon(ssl=cls.ssl, ssloptions=cls.ssloptions)
        pconf = cls.get_proxy_config()
        config = proxy.ProxyConfig(
            no_upstream_cert = cls.no_upstream_cert,
            cacert = tutils.test_data.path("data/serverkey.pem"),
            authenticator = cls.authenticator,
            **pconf
        )
        tmaster = cls.masterclass(cls.tqueue, config)
        cls.proxy = ProxyThread(tmaster)
        cls.proxy.start()

    @property
    def master(cls):
        return cls.proxy.tmaster

    @classmethod
    def teardownAll(cls):
        cls.proxy.shutdown()
        cls.server.shutdown()
        cls.server2.shutdown()

    def setUp(self):
        self.master.clear_log()
        self.master.state.clear()
        self.server.clear_log()
        self.server2.clear_log()

    @property
    def scheme(self):
        return "https" if self.ssl else "http"

    @property
    def proxies(self):
        """
            The URL base for the server instance.
        """
        return (
            (self.scheme, ("127.0.0.1", self.proxy.port))
        )

    @classmethod
    def get_proxy_config(cls):
        d = dict()
        if cls.clientcerts:
            d["clientcerts"] = tutils.test_data.path("data/clientcert")
        if cls.certfile:
            d["certfile"]  =tutils.test_data.path("data/testkey.pem")
        return d


class HTTPProxTest(ProxTestBase):
    def pathoc_raw(self):
        return libpathod.pathoc.Pathoc("127.0.0.1", self.proxy.port)

    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = libpathod.pathoc.Pathoc("localhost", self.proxy.port, ssl=self.ssl, sni=sni)
        if self.ssl:
            p.connect(("127.0.0.1", self.server.port))
        else:
            p.connect()
        return p

    def pathod(self, spec, sni=None):
        """
            Constructs a pathod GET request, with the appropriate base and proxy.
        """
        p = self.pathoc(sni=sni)
        spec = spec.encode("string_escape")
        if self.ssl:
            q = "get:'/p/%s'"%spec
        else:
            q = "get:'%s/p/%s'"%(self.server.urlbase, spec)
        return p.request(q)

    def app(self, page):
        if self.ssl:
            p = libpathod.pathoc.Pathoc("127.0.0.1", self.proxy.port, True)
            print "PRE"
            p.connect((APP_HOST, APP_PORT))
            print "POST"
            return p.request("get:'/%s'"%page)
        else:
            p = self.pathoc()
            return p.request("get:'http://%s/%s'"%(APP_HOST, page))


class TResolver:
    def __init__(self, port):
        self.port = port

    def original_addr(self, sock):
        return ("127.0.0.1", self.port)


class TransparentProxTest(ProxTestBase):
    ssl = None
    resolver = TResolver
    @classmethod
    def get_proxy_config(cls):
        d = ProxTestBase.get_proxy_config()
        if cls.ssl:
            ports = [cls.server.port, cls.server2.port]
        else:
            ports = []
        d["transparent_proxy"] = dict(
            resolver = cls.resolver(cls.server.port),
            sslports = ports
        )
        return d

    def pathod(self, spec, sni=None):
        """
            Constructs a pathod GET request, with the appropriate base and proxy.
        """
        if self.ssl:
            p = self.pathoc(sni=sni)
            q = "get:'/p/%s'"%spec
        else:
            p = self.pathoc()
            q = "get:'/p/%s'"%spec
        return p.request(q)

    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = libpathod.pathoc.Pathoc("localhost", self.proxy.port, ssl=self.ssl, sni=sni)
        p.connect()
        return p


class ReverseProxTest(ProxTestBase):
    ssl = None
    @classmethod
    def get_proxy_config(cls):
        d = ProxTestBase.get_proxy_config()
        d["reverse_proxy"] = (
                "https" if cls.ssl else "http",
                "127.0.0.1",
                cls.server.port
            )
        return d

    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = libpathod.pathoc.Pathoc("localhost", self.proxy.port, ssl=self.ssl, sni=sni)
        p.connect()
        return p

    def pathod(self, spec, sni=None):
        """
            Constructs a pathod GET request, with the appropriate base and proxy.
        """
        if self.ssl:
            p = self.pathoc(sni=sni)
            q = "get:'/p/%s'"%spec
        else:
            p = self.pathoc()
            q = "get:'/p/%s'"%spec
        return p.request(q)




