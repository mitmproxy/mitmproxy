import threading, Queue
import flask
import human_curl as hurl
import libpathod.test, libpathod.pathoc
from libmproxy import proxy, flow, controller
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
        s.apps.add(testapp, "testapp", 80)
        s.apps.add(errapp, "errapp", 80)
        state = flow.State()
        flow.FlowMaster.__init__(self, s, state)
        self.testq = testq

    def handle_request(self, m):
        flow.FlowMaster.handle_request(self, m)
        m.reply()

    def handle_response(self, m):
        flow.FlowMaster.handle_response(self, m)
        m.reply()


class ProxyThread(threading.Thread):
    def __init__(self, tmaster):
        threading.Thread.__init__(self)
        self.tmaster = tmaster
        controller.should_exit = False

    @property
    def port(self):
        return self.tmaster.server.port

    def run(self):
        self.tmaster.run()

    def shutdown(self):
        self.tmaster.shutdown()


class ProxTestBase:
    masterclass = TestMaster
    @classmethod
    def setupAll(cls):
        cls.tqueue = Queue.Queue()
        cls.server = libpathod.test.Daemon(ssl=cls.ssl)
        pconf = cls.get_proxy_config()
        config = proxy.ProxyConfig(
            certfile=tutils.test_data.path("data/testkey.pem"),
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

    def setUp(self):
        self.master.state.clear()

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

    @property
    def urlbase(self):
        """
            The URL base for the server instance.
        """
        return self.server.urlbase

    def last_log(self):
        return self.server.last_log()


class HTTPProxTest(ProxTestBase):
    ssl = None
    clientcerts = False
    @classmethod
    def get_proxy_config(cls):
        d = dict()
        if cls.clientcerts:
            d["clientcerts"] = tutils.test_data.path("data/clientcert")
        return d

    def pathoc(self, connect_to = None):
        """
            Returns a connected Pathoc instance.
        """
        p = libpathod.pathoc.Pathoc("localhost", self.proxy.port)
        p.connect(connect_to)
        return p

    def pathod(self, spec):
        """
            Constructs a pathod request, with the appropriate base and proxy.
        """
        return hurl.get(
            self.urlbase + "/p/" + spec,
            proxy=self.proxies,
            validate_cert=False,
            #debug=hurl.utils.stdout_debug
        )


class TResolver:
    def __init__(self, port):
        self.port = port

    def original_addr(self, sock):
        return ("127.0.0.1", self.port)


class TransparentProxTest(ProxTestBase):
    ssl = None
    @classmethod
    def get_proxy_config(cls):
        return dict(
                transparent_proxy = dict(
                    resolver = TResolver(cls.server.port),
                    sslports = []
                )
            )

    def pathod(self, spec):
        """
            Constructs a pathod request, with the appropriate base and proxy.
        """
        r = hurl.get(
            "http://127.0.0.1:%s"%self.proxy.port + "/p/" + spec,
            validate_cert=False,
            #debug=hurl.utils.stdout_debug
        )
        return r


class ReverseProxTest(ProxTestBase):
    ssl = None
    @classmethod
    def get_proxy_config(cls):
        return dict(
            reverse_proxy = (
                "https" if cls.ssl else "http",
                "127.0.0.1",
                cls.server.port
            )
        )

    def pathod(self, spec):
        """
            Constructs a pathod request, with the appropriate base and proxy.
        """
        r = hurl.get(
            "http://127.0.0.1:%s"%self.proxy.port + "/p/" + spec,
            validate_cert=False,
            #debug=hurl.utils.stdout_debug
        )
        return r

