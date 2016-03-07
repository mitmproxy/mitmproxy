import glob
import os
from contextlib import contextmanager

from mitmproxy import utils, script
from mitmproxy.proxy import config
from netlib import tutils as netutils
from netlib.http import Headers
from . import tservers, tutils

example_dir = utils.Data(__name__).path("../../examples")


@contextmanager
def example(command):
    command = os.path.join(example_dir, command)
    # tmaster = tservers.TestMaster(config.ProxyConfig())
    # ctx = script.ScriptContext(tmaster)
    ctx = DummyContext()
    s = script.Script(command, ctx)
    yield s
    s.unload()


class DummyContext(object):
    """Emulate script.ScriptContext() functionality."""

    def log(self, *args, **kwargs):
        pass


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
        try:
            s = script.Script(f, script.ScriptContext(tmaster))  # Loads the script file.
        except Exception as v:
            if "ImportError" not in str(v):
                raise
        else:
            s.unload()


def test_add_header():
    flow = tutils.tflow(resp=netutils.tresp())
    add_header.response({}, flow)
    assert flow.response.headers["newheader"] == "foo"


def test_modify_form():
    form_header = Headers(content_type="application/x-www-form-urlencoded")
    flow = tutils.tflow(req=netutils.treq(headers=form_header))
    modify_form.request({}, flow)
    assert flow.request.urlencoded_form["mitmproxy"] == ["rocks"]


def test_modify_querystring():
    flow = tutils.tflow(req=netutils.treq(path="/search?q=term"))
    modify_querystring.request({}, flow)
    assert flow.request.query["mitmproxy"] == ["rocks"]


def test_modify_response_body():
    ctx = DummyContext()
    tutils.raises(ValueError, modify_response_body.start, ctx, [])

    modify_response_body.start(ctx, ["modify-response-body.py", "mitmproxy", "rocks"])
    assert ctx.old == "mitmproxy" and ctx.new == "rocks"

    flow = tutils.tflow(resp=netutils.tresp(content="I <3 mitmproxy"))
    modify_response_body.response(ctx, flow)
    assert flow.response.content == "I <3 rocks"


def test_custom_contentviews():
    pig = custom_contentviews.ViewPigLatin()
    _, fmt = pig("<html>test!</html>")
    assert any('esttay!' in val[0][1] for val in fmt)
    assert not pig("gobbledygook")


def test_iframe_injector():
    ctx = DummyContext()
    tutils.raises(ValueError, iframe_injector.start, ctx, [])

    flow = tutils.tflow(resp=netutils.tresp(content="<html>Kungfu Panda 3</html>"))
    ctx.iframe_url = "http://example.org/evil_iframe"
    iframe_injector.response(ctx, flow)

    content = flow.response.content
    assert 'iframe' in content and ctx.iframe_url in content


def test_redirect_requests():
    flow = tutils.tflow(req=netutils.treq(host="example.org"))
    redirect_requests.request({}, flow)
    assert flow.request.host == "mitmproxy.org"
