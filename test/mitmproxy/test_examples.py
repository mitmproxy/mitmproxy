import glob

from mitmproxy import utils, script
from mitmproxy.proxy import config
from netlib import tutils as netutils
from netlib.http import Headers
from . import tservers, tutils

from examples import (
    modify_form,

)


def test_load_scripts():
    example_dir = utils.Data(__name__).path("../../examples")
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


def test_modify_form():
    form_header = Headers(content_type="application/x-www-form-urlencoded")
    flow = tutils.tflow(req=netutils.treq(headers=form_header))
    modify_form.request({}, flow)
    assert flow.request.urlencoded_form["mitmproxy"] == ["rocks"]

