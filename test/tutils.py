import tempfile, os, shutil
from contextlib import contextmanager
from libpathod import utils, test, pathoc
import requests

class DaemonTests:
    noweb = False
    noapi = False
    nohang = False
    ssl = False
    @classmethod
    def setUpAll(self):
        self.d = test.Daemon(
            staticdir=test_data.path("data"),
            anchors=[("/anchor/.*", "202")],
            ssl = self.ssl,
            sizelimit=1*1024*1024,
            noweb = self.noweb,
            noapi = self.noapi,
            nohang = self.nohang
        )

    @classmethod
    def tearDownAll(self):
        self.d.shutdown()

    def setUp(self):
        if not (self.noweb or self.noapi):
            self.d.clear_log()

    def getpath(self, path, params=None):
        scheme = "https" if self.ssl else "http"
        return requests.get(
            "%s://localhost:%s/%s"%(scheme, self.d.port, path), verify=False, params=params
        )

    def get(self, spec):
        return requests.get(self.d.p(spec), verify=False)

    def pathoc(self, spec, timeout=None):
        c = pathoc.Pathoc("localhost", self.d.port)
        c.connect()
        if self.ssl:
            c.convert_to_ssl()
        if timeout:
            c.settimeout(timeout)
        return c.request(spec)



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
