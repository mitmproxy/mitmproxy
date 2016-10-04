import os.path
import threading
import tempfile
import flask
import mock
import sys

from mitmproxy.proxy.config import ProxyConfig
from mitmproxy.proxy.server import ProxyServer
import pathod.test
import pathod.pathoc
from mitmproxy import flow, controller, options
from mitmproxy import builtins
import netlib.exceptions

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

    def __init__(self, opts, config):
        s = ProxyServer(config)
        state = flow.State()
        flow.FlowMaster.__init__(self, opts, s, state)
        self.addons.add(*builtins.default_addons())
        self.apps.add(testapp, "testapp", 80)
        self.apps.add(errapp, "errapp", 80)
        self.clear_log()

    def clear_log(self):
        self.tlog = []

    @controller.handler
    def log(self, e):
        self.tlog.append(e.msg)


class ProxyThread(threading.Thread):

    def __init__(self, tmaster):
        threading.Thread.__init__(self)
        self.tmaster = tmaster
        self.name = "ProxyThread (%s:%s)" % (
            tmaster.server.address.host, tmaster.server.address.port
        )
        controller.should_exit = False

    @property
    def port(self):
        return self.tmaster.server.address.port

    @property
    def tlog(self):
        return self.tmaster.tlog

    def run(self):
        self.tmaster.run()

    def shutdown(self):
        self.tmaster.shutdown()


class ProxyTestBase(object):
    # Test Configuration
    ssl = None
    ssloptions = False
    masterclass = TestMaster

    add_upstream_certs_to_client_chain = False

    @classmethod
    def setup_class(cls):
        cls.server = pathod.test.Daemon(
            ssl=cls.ssl,
            ssloptions=cls.ssloptions)
        cls.server2 = pathod.test.Daemon(
            ssl=cls.ssl,
            ssloptions=cls.ssloptions)

        opts = cls.get_options()
        cls.config = ProxyConfig(opts)
        tmaster = cls.masterclass(opts, cls.config)
        tmaster.start_app(options.APP_HOST, options.APP_PORT)
        cls.proxy = ProxyThread(tmaster)
        cls.proxy.start()

    @classmethod
    def teardown_class(cls):
        # perf: we want to run tests in parallell
        # should this ever cause an error, travis should catch it.
        # shutil.rmtree(cls.cadir)
        cls.proxy.shutdown()
        cls.server.shutdown()
        cls.server2.shutdown()

    def teardown(self):
        try:
            self.server.wait_for_silence()
        except netlib.exceptions.Timeout:
            # FIXME: Track down the Windows sync issues
            if sys.platform != "win32":
                raise

    def setup(self):
        self.master.clear_log()
        self.master.state.clear()
        self.server.clear_log()
        self.server2.clear_log()

    @property
    def master(self):
        return self.proxy.tmaster

    @classmethod
    def get_options(cls):
        cls.cadir = os.path.join(tempfile.gettempdir(), "mitmproxy")
        return options.Options(
            listen_port=0,
            cadir=cls.cadir,
            add_upstream_certs_to_client_chain=cls.add_upstream_certs_to_client_chain,
            ssl_insecure=True,
        )


class LazyPathoc(pathod.pathoc.Pathoc):
    def __init__(self, lazy_connect, *args, **kwargs):
        self.lazy_connect = lazy_connect
        pathod.pathoc.Pathoc.__init__(self, *args, **kwargs)

    def connect(self):
        return pathod.pathoc.Pathoc.connect(self, self.lazy_connect)


class HTTPProxyTest(ProxyTestBase):

    def pathoc_raw(self):
        return pathod.pathoc.Pathoc(("127.0.0.1", self.proxy.port), fp=None)

    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        if self.ssl:
            conn = ("127.0.0.1", self.server.port)
        else:
            conn = None
        return LazyPathoc(
            conn,
            ("localhost", self.proxy.port), ssl=self.ssl, sni=sni, fp=None
        )

    def pathod(self, spec, sni=None):
        """
            Constructs a pathod GET request, with the appropriate base and proxy.
        """
        p = self.pathoc(sni=sni)
        if self.ssl:
            q = "get:'/p/%s'" % spec
        else:
            q = "get:'%s/p/%s'" % (self.server.urlbase, spec)
        with p.connect():
            return p.request(q)

    def app(self, page):
        if self.ssl:
            p = pathod.pathoc.Pathoc(
                ("127.0.0.1", self.proxy.port), True, fp=None
            )
            with p.connect((options.APP_HOST, options.APP_PORT)):
                return p.request("get:'%s'" % page)
        else:
            p = self.pathoc()
            with p.connect():
                return p.request("get:'http://%s%s'" % (options.APP_HOST, page))


class TResolver:

    def __init__(self, port):
        self.port = port

    def original_addr(self, sock):
        return ("127.0.0.1", self.port)


class TransparentProxyTest(ProxyTestBase):
    ssl = None
    resolver = TResolver

    @classmethod
    def setup_class(cls):
        super(TransparentProxyTest, cls).setup_class()

        cls._resolver = mock.patch(
            "mitmproxy.platform.resolver",
            new=lambda: cls.resolver(cls.server.port)
        )
        cls._resolver.start()

    @classmethod
    def teardown_class(cls):
        cls._resolver.stop()
        super(TransparentProxyTest, cls).teardown_class()

    @classmethod
    def get_options(cls):
        opts = ProxyTestBase.get_options()
        opts.mode = "transparent"
        return opts

    def pathod(self, spec, sni=None):
        """
            Constructs a pathod GET request, with the appropriate base and proxy.
        """
        if self.ssl:
            p = self.pathoc(sni=sni)
            q = "get:'/p/%s'" % spec
        else:
            p = self.pathoc()
            q = "get:'/p/%s'" % spec
        with p.connect():
            return p.request(q)

    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = pathod.pathoc.Pathoc(
            ("localhost", self.proxy.port), ssl=self.ssl, sni=sni, fp=None
        )
        return p


class ReverseProxyTest(ProxyTestBase):
    ssl = None

    @classmethod
    def get_options(cls):
        opts = ProxyTestBase.get_options()
        opts.upstream_server = "".join(
            [
                "https" if cls.ssl else "http",
                "://",
                "127.0.0.1:",
                str(cls.server.port)
            ]
        )
        opts.mode = "reverse"
        return opts

    def pathoc(self, sni=None):
        """
            Returns a connected Pathoc instance.
        """
        p = pathod.pathoc.Pathoc(
            ("localhost", self.proxy.port), ssl=self.ssl, sni=sni, fp=None
        )
        return p

    def pathod(self, spec, sni=None):
        """
            Constructs a pathod GET request, with the appropriate base and proxy.
        """
        if self.ssl:
            p = self.pathoc(sni=sni)
            q = "get:'/p/%s'" % spec
        else:
            p = self.pathoc()
            q = "get:'/p/%s'" % spec
        with p.connect():
            return p.request(q)


class SocksModeTest(HTTPProxyTest):

    @classmethod
    def get_options(cls):
        opts = ProxyTestBase.get_options()
        opts.mode = "socks5"
        return opts


class ChainProxyTest(ProxyTestBase):

    """
    Chain three instances of mitmproxy in a row to test upstream mode.
    Proxy order is cls.proxy -> cls.chain[0] -> cls.chain[1]
    cls.proxy and cls.chain[0] are in upstream mode,
    cls.chain[1] is in regular mode.
    """
    chain = None
    n = 2

    @classmethod
    def setup_class(cls):
        cls.chain = []
        super(ChainProxyTest, cls).setup_class()
        for _ in range(cls.n):
            opts = cls.get_options()
            config = ProxyConfig(opts)
            tmaster = cls.masterclass(opts, config)
            proxy = ProxyThread(tmaster)
            proxy.start()
            cls.chain.insert(0, proxy)

        # Patch the orginal proxy to upstream mode
        opts = cls.get_options()
        cls.config = cls.proxy.tmaster.config = cls.proxy.tmaster.server.config = ProxyConfig(opts)

    @classmethod
    def teardown_class(cls):
        super(ChainProxyTest, cls).teardown_class()
        for proxy in cls.chain:
            proxy.shutdown()

    def setup(self):
        super(ChainProxyTest, self).setup()
        for proxy in self.chain:
            proxy.tmaster.clear_log()
            proxy.tmaster.state.clear()

    @classmethod
    def get_options(cls):
        opts = super(ChainProxyTest, cls).get_options()
        if cls.chain:  # First proxy is in normal mode.
            opts.update(
                mode="upstream",
                upstream_server="http://127.0.0.1:%s" % cls.chain[0].port
            )
        return opts


class HTTPUpstreamProxyTest(ChainProxyTest, HTTPProxyTest):
    pass
