import tempfile
import re
import shutil
from six.moves import cStringIO as StringIO

import netlib
from pathod import utils, test, pathoc, pathod, language
from netlib import tcp
import requests

def treader(bytes):
    """
        Construct a tcp.Read object from bytes.
    """
    fp = StringIO(bytes)
    return tcp.Reader(fp)


class DaemonTests(object):
    noweb = False
    noapi = False
    nohang = False
    ssl = False
    timeout = None
    hexdump = False
    ssloptions = None
    nocraft = False

    @classmethod
    def setup_class(cls):
        opts = cls.ssloptions or {}
        cls.confdir = tempfile.mkdtemp()
        opts["confdir"] = cls.confdir
        so = pathod.SSLOptions(**opts)
        cls.d = test.Daemon(
            staticdir=test_data.path("data"),
            anchors=[
                (re.compile("/anchor/.*"), "202:da")
            ],
            ssl=cls.ssl,
            ssloptions=so,
            sizelimit=1 * 1024 * 1024,
            noweb=cls.noweb,
            noapi=cls.noapi,
            nohang=cls.nohang,
            timeout=cls.timeout,
            hexdump=cls.hexdump,
            nocraft=cls.nocraft,
            logreq=True,
            logresp=True,
            explain=True
        )

    @classmethod
    def teardown_class(cls):
        cls.d.shutdown()
        shutil.rmtree(cls.confdir)

    def teardown(self):
        if not (self.noweb or self.noapi):
            self.d.clear_log()

    def getpath(self, path, params=None):
        scheme = "https" if self.ssl else "http"
        resp = requests.get(
            "%s://localhost:%s/%s" % (
                scheme,
                self.d.port,
                path
            ),
            verify=False,
            params=params
        )
        return resp

    def get(self, spec):
        resp = requests.get(self.d.p(spec), verify=False)
        return resp

    def pathoc(
        self,
        specs,
        timeout=None,
        connect_to=None,
        ssl=None,
        ws_read_limit=None,
        use_http2=False,
    ):
        """
            Returns a (messages, text log) tuple.
        """
        if ssl is None:
            ssl = self.ssl
        logfp = StringIO()
        c = pathoc.Pathoc(
            ("localhost", self.d.port),
            ssl=ssl,
            ws_read_limit=ws_read_limit,
            timeout=timeout,
            fp=logfp,
            use_http2=use_http2,
        )
        c.connect(connect_to)
        ret = []
        for i in specs:
            resp = c.request(i)
            if resp:
                ret.append(resp)
        for frm in c.wait():
            ret.append(frm)
        c.stop()
        return ret, logfp.getvalue()


tmpdir = netlib.tutils.tmpdir

raises = netlib.tutils.raises

test_data = utils.Data(__name__)


def render(r, settings=language.Settings()):
    r = r.resolve(settings)
    s = StringIO()
    assert language.serve(r, s, settings)
    return s.getvalue()
