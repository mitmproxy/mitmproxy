import tempfile
import re
import shutil
import requests
import io
import urllib


from mitmproxy.net import tcp
from mitmproxy.test import tutils

from pathod import language
from pathod import pathoc
from pathod import pathod
from pathod import test
from pathod.pathod import CA_CERT_NAME


def treader(bytes):
    """
        Construct a tcp.Read object from bytes.
    """
    fp = io.BytesIO(bytes)
    return tcp.Reader(fp)


class DaemonTests:
    nohang = False
    ssl = False
    timeout = None
    hexdump = False
    ssloptions = None
    nocraft = False
    explain = True

    @classmethod
    def setup_class(cls):
        opts = cls.ssloptions or {}
        cls.confdir = tempfile.mkdtemp()
        opts["confdir"] = cls.confdir
        so = pathod.SSLOptions(**opts)
        cls.d = test.Daemon(
            staticdir=tutils.test_data.path("pathod/data"),
            anchors=[
                (re.compile("/anchor/.*"), "202:da")
            ],
            ssl=cls.ssl,
            ssloptions=so,
            sizelimit=1 * 1024 * 1024,
            nohang=cls.nohang,
            timeout=cls.timeout,
            hexdump=cls.hexdump,
            nocraft=cls.nocraft,
            logreq=True,
            logresp=True,
            explain=cls.explain
        )

    @classmethod
    def teardown_class(cls):
        cls.d.shutdown()
        shutil.rmtree(cls.confdir)

    def teardown(self):
        self.d.wait_for_silence()
        self.d.clear_log()

    def _getpath(self, path, params=None):
        scheme = "https" if self.ssl else "http"
        resp = requests.get(
            "%s://localhost:%s/%s" % (
                scheme,
                self.d.port,
                path
            ),
            verify=os.path.join(self.d.thread.server.ssloptions.confdir, CA_CERT_NAME),
            params=params
        )
        return resp

    def getpath(self, path, params=None):
        logfp = io.StringIO()
        c = pathoc.Pathoc(
            ("localhost", self.d.port),
            ssl=self.ssl,
            fp=logfp,
        )
        with c.connect():
            if params:
                path = path + "?" + urllib.parse.urlencode(params)
            resp = c.request("get:%s" % path)
            return resp

    def get(self, spec):
        logfp = io.StringIO()
        c = pathoc.Pathoc(
            ("localhost", self.d.port),
            ssl=self.ssl,
            fp=logfp,
        )
        with c.connect():
            resp = c.request(
                "get:/p/%s" % urllib.parse.quote(spec)
            )
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
        logfp = io.StringIO()
        c = pathoc.Pathoc(
            ("localhost", self.d.port),
            ssl=ssl,
            ws_read_limit=ws_read_limit,
            timeout=timeout,
            fp=logfp,
            use_http2=use_http2,
        )
        with c.connect(connect_to):
            ret = []
            for i in specs:
                resp = c.request(i)
                if resp:
                    ret.append(resp)
            for frm in c.wait():
                ret.append(frm)
            c.stop()
            return ret, logfp.getvalue()


def render(r, settings=language.Settings()):
    r = r.resolve(settings)
    s = io.BytesIO()
    assert language.serve(r, s, settings)
    return s.getvalue()
