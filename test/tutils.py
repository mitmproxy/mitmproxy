import threading, Queue, time
import os, shutil,tempfile
from contextlib import contextmanager
import libpry
from libmproxy import proxy, flow, controller, utils
import human_curl as hurl
import libpathod.test
import random

def treq(conn=None):
    if not conn:
        conn = flow.ClientConnect(("address", 22))
    headers = flow.ODictCaseless()
    headers["header"] = ["qvalue"]
    return flow.Request(conn, "host", 80, "http", "GET", "/path", headers, "content")


def tresp(req=None):
    if not req:
        req = treq()
    headers = flow.ODictCaseless()
    headers["header_response"] = ["svalue"]
    return flow.Response(req, 200, "message", headers, "content_response", None)


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


class TestMaster(controller.Master):
    def __init__(self, port, testq):
        s = proxy.ProxyServer(proxy.ProxyConfig(test_data.path("data/testkey.pem")), port)
        controller.Master.__init__(self, s)
        self.testq = testq
        self.log = []

    def clear(self):
        self.log = []

    def handle(self, m):
        self.log.append(m)
        m._ack()


class ProxyThread(threading.Thread):
    def __init__(self, testq):
        self.port = random.randint(10000, 20000)
        self.tmaster = TestMaster(self.port, testq)
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


class ProxTest:
    ssl = None
    @classmethod
    def setupAll(cls):
        cls.tqueue = Queue.Queue()
        # We don't make any concurrent requests, so we can access
        # the attributes on this object safely.
        cls.proxy = ProxyThread(cls.tqueue)
        cls.proxy.start()
        cls.server = libpathod.test.Daemon(ssl=cls.ssl)

    @classmethod
    def teardownAll(cls):
        cls.proxy.shutdown()
        cls.server.shutdown()

    def setUp(self):
        self.proxy.tmaster.clear()

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

    @property
    def proxies(self):
        """
            The URL base for the server instance.
        """
        return (
            ("https" if self.ssl else "http", ("127.0.0.1", self.proxy.port))
        )

    @property
    def urlbase(self):
        """
            The URL base for the server instance.
        """
        return self.server.urlbase

    def log(self):
        pthread = self.proxy
        return pthread.tmaster.log


@contextmanager
def tmpdir(*args, **kwargs):
    orig_workdir = os.getcwd()
    temp_workdir = tempfile.mkdtemp(*args, **kwargs)
    os.chdir(temp_workdir)

    yield temp_workdir

    os.chdir(orig_workdir)
    shutil.rmtree(temp_workdir)


def raises(exc, obj, *args, **kwargs):
    """
        Assert that a callable raises a specified exception.

        :exc An exception class or a string. If a class, assert that an
        exception of this type is raised. If a string, assert that the string
        occurs in the string representation of the exception, based on a
        case-insenstivie match.

        :obj A callable object.

        :args Arguments to be passsed to the callable.

        :kwargs Arguments to be passed to the callable.
    """
    try:
        apply(obj, args, kwargs)
    except Exception, v:
        if isinstance(exc, basestring):
            if exc.lower() in str(v).lower():
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s"%(
                        repr(str(exc)), v
                    )
                )
        else:
            if isinstance(v, exc):
                return
            else:
                raise AssertionError(
                    "Expected %s, but caught %s %s"%(
                        exc.__name__, v.__class__.__name__, str(v)
                    )
                )
    raise AssertionError("No exception raised.")

test_data = utils.Data(__name__)
