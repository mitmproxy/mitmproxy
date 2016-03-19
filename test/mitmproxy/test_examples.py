import glob
import json
import os
from contextlib import contextmanager

from mitmproxy import utils, script
from mitmproxy.proxy import config
from netlib import tutils as netutils
from netlib.http import Headers
from . import tservers, tutils

example_dir = utils.Data(__name__).path("../../examples")


class DummyContext(object):
    """Emulate script.ScriptContext() functionality."""

    contentview = None

    def log(self, *args, **kwargs):
        pass

    def add_contentview(self, view_obj):
        self.contentview = view_obj

    def remove_contentview(self, view_obj):
        self.contentview = None


@contextmanager
def example(command):
    command = os.path.join(example_dir, command)
    ctx = DummyContext()
    with script.Script(command, ctx) as s:
        yield s


def test_load_scripts():
    scripts = glob.glob("%s/*.py" % example_dir)

    tmaster = tservers.TestMaster(config.ProxyConfig())

    for f in scripts:
        if "har_extractor" in f:
            continue
        if "flowwriter" in f:
            f += " -"
        if "iframe_injector" in f:
            f += " foo"  # one argument required
        if "filt" in f:
            f += " ~a"
        if "modify_response_body" in f:
            f += " foo bar"  # two arguments required

        s = script.Script(f, script.ScriptContext(tmaster))
        try:
            s.load()
        except Exception as v:
            if "ImportError" not in str(v):
                raise
        else:
            s.unload()


def test_add_header():
    flow = tutils.tflow(resp=netutils.tresp())
    with example("add_header.py") as ex:
        ex.run("response", flow)
        assert flow.response.headers["newheader"] == "foo"


def test_custom_contentviews():
    with example("custom_contentviews.py") as ex:
        pig = ex.ctx.contentview
        _, fmt = pig("<html>test!</html>")
        assert any('esttay!' in val[0][1] for val in fmt)
        assert not pig("gobbledygook")


def test_iframe_injector():
    with tutils.raises(script.ScriptException):
        with example("iframe_injector.py") as ex:
            pass

    flow = tutils.tflow(resp=netutils.tresp(content="<html>mitmproxy</html>"))
    with example("iframe_injector.py http://example.org/evil_iframe") as ex:
        ex.run("response", flow)
        content = flow.response.content
        assert 'iframe' in content and 'evil_iframe' in content


def test_modify_form():
    form_header = Headers(content_type="application/x-www-form-urlencoded")
    flow = tutils.tflow(req=netutils.treq(headers=form_header))
    with example("modify_form.py") as ex:
        ex.run("request", flow)
        assert flow.request.urlencoded_form["mitmproxy"] == ["rocks"]


def test_modify_querystring():
    flow = tutils.tflow(req=netutils.treq(path="/search?q=term"))
    with example("modify_querystring.py") as ex:
        ex.run("request", flow)
        assert flow.request.query["mitmproxy"] == ["rocks"]


def test_modify_response_body():
    with tutils.raises(script.ScriptException):
        with example("modify_response_body.py") as ex:
            pass

    flow = tutils.tflow(resp=netutils.tresp(content="I <3 mitmproxy"))
    with example("modify_response_body.py mitmproxy rocks") as ex:
        assert ex.ctx.old == "mitmproxy" and ex.ctx.new == "rocks"
        ex.run("response", flow)
        assert flow.response.content == "I <3 rocks"


def test_redirect_requests():
    flow = tutils.tflow(req=netutils.treq(host="example.org"))
    with example("redirect_requests.py") as ex:
        ex.run("request", flow)
        assert flow.request.host == "mitmproxy.org"


def test_har_extractor():
    with tutils.raises(script.ScriptException):
        with example("har_extractor.py") as ex:
            pass

    times = dict(
        timestamp_start=746203272,
        timestamp_end=746203272,
    )

    flow = tutils.tflow(
        req=netutils.treq(**times),
        resp=netutils.tresp(**times)
    )

    with example("har_extractor.py -") as ex:
        ex.run("response", flow)

        with open(tutils.test_data.path("data/har_extractor.har")) as fp:
            test_data = json.load(fp)
            assert json.loads(ex.ctx.HARLog.json()) == test_data["test_response"]
