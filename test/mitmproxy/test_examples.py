import json

import sys
import os.path
from mitmproxy.flow import master
from mitmproxy.flow import state
from mitmproxy import options
from mitmproxy import contentviews
from mitmproxy.builtins import script
import netlib.utils
from netlib import tutils as netutils
from netlib.http import Headers
from . import tutils, mastertest

example_dir = netlib.utils.Data(__name__).push("../../examples")


class ScriptError(Exception):
    pass


class RaiseMaster(master.FlowMaster):
    def add_event(self, e, level):
        if level in ("warn", "error"):
            raise ScriptError(e)


def tscript(cmd, args=""):
    cmd = example_dir.path(cmd) + " " + args
    m = RaiseMaster(options.Options(), None, state.State())
    sc = script.Script(cmd)
    m.addons.add(sc)
    return m, sc


class TestScripts(mastertest.MasterTest):
    def test_add_header(self):
        m, _ = tscript("add_header.py")
        f = tutils.tflow(resp=netutils.tresp())
        self.invoke(m, "response", f)
        assert f.response.headers["newheader"] == "foo"

    def test_custom_contentviews(self):
        m, sc = tscript("custom_contentviews.py")
        pig = contentviews.get("pig_latin_HTML")
        _, fmt = pig(b"<html>test!</html>")
        assert any(b'esttay!' in val[0][1] for val in fmt)
        assert not pig(b"gobbledygook")

    def test_iframe_injector(self):
        with tutils.raises(ScriptError):
            tscript("iframe_injector.py")

        m, sc = tscript("iframe_injector.py", "http://example.org/evil_iframe")
        flow = tutils.tflow(resp=netutils.tresp(content=b"<html>mitmproxy</html>"))
        self.invoke(m, "response", flow)
        content = flow.response.content
        assert b'iframe' in content and b'evil_iframe' in content

    def test_modify_form(self):
        m, sc = tscript("modify_form.py")

        form_header = Headers(content_type="application/x-www-form-urlencoded")
        f = tutils.tflow(req=netutils.treq(headers=form_header))
        self.invoke(m, "request", f)

        assert f.request.urlencoded_form[b"mitmproxy"] == b"rocks"

        f.request.headers["content-type"] = ""
        self.invoke(m, "request", f)
        assert list(f.request.urlencoded_form.items()) == [(b"foo", b"bar")]

    def test_modify_querystring(self):
        m, sc = tscript("modify_querystring.py")
        f = tutils.tflow(req=netutils.treq(path="/search?q=term"))

        self.invoke(m, "request", f)
        assert f.request.query["mitmproxy"] == "rocks"

        f.request.path = "/"
        self.invoke(m, "request", f)
        assert f.request.query["mitmproxy"] == "rocks"

    def test_modify_response_body(self):
        with tutils.raises(ScriptError):
            tscript("modify_response_body.py")

        m, sc = tscript("modify_response_body.py", "mitmproxy rocks")
        f = tutils.tflow(resp=netutils.tresp(content=b"I <3 mitmproxy"))
        self.invoke(m, "response", f)
        assert f.response.content == b"I <3 rocks"

    def test_redirect_requests(self):
        m, sc = tscript("redirect_requests.py")
        f = tutils.tflow(req=netutils.treq(host="example.org"))
        self.invoke(m, "request", f)
        assert f.request.host == "mitmproxy.org"

    def test_har_extractor(self):
        if sys.version_info >= (3, 0):
            with tutils.raises("does not work on Python 3"):
                tscript("har_extractor.py")
            return

        with tutils.raises(ScriptError):
            tscript("har_extractor.py")

        with tutils.tmpdir() as tdir:
            times = dict(
                timestamp_start=746203272,
                timestamp_end=746203272,
            )

            path = os.path.join(tdir, "file")
            m, sc = tscript("har_extractor.py", path)
            f = tutils.tflow(
                req=netutils.treq(**times),
                resp=netutils.tresp(**times)
            )
            self.invoke(m, "response", f)
            m.addons.remove(sc)

            fp = open(path, "rb")
            test_data = json.load(fp)
            assert len(test_data["log"]["pages"]) == 1
