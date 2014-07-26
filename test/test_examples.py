import glob
from libmproxy import utils, script
from libmproxy.proxy import config
import tservers


def test_load_scripts():

    example_dir = utils.Data("libmproxy").path("../examples")
    scripts = glob.glob("%s/*.py" % example_dir)

    tmaster = tservers.TestMaster(config.ProxyConfig())

    for f in scripts:
        if "modify_response_body" in f:
            f += " foo bar"  # two arguments required
        script.Script(f, tmaster)  # Loads the script file.