import glob
from libmproxy import utils, script
from libmproxy.proxy import config
import tservers


def test_load_scripts():
    example_dir = utils.Data("libmproxy").path("../examples")
    scripts = glob.glob("%s/*.py" % example_dir)

    tmaster = tservers.TestMaster(config.ProxyConfig())

    for f in scripts:
        if "har_extractor" in f or "flowwriter" in f:
            f += " -"
        if "iframe_injector" in f:
            f += " foo"  # one argument required
        if "filt" in f:
            f += " ~a"
        if "modify_response_body" in f:
            f += " foo bar"  # two arguments required
        try:
            s = script.Script(f, tmaster)  # Loads the script file.
        except Exception as v:
            if not "ImportError" in str(v):
                raise
        else:
            s.unload()
