import glob
import mock
from libmproxy import utils, script
from libmproxy.proxy import config
import tservers

@mock.patch.dict("sys.modules", {"bs4": mock.Mock()})
def test_load_scripts():
    example_dir = utils.Data("libmproxy").path("../examples")
    scripts = glob.glob("%s/*.py" % example_dir)

    tmaster = tservers.TestMaster(config.ProxyConfig())

    for f in scripts:
        if "iframe_injector" in f:
            f += " foo"  # one argument required
        if "modify_response_body" in f:
            f += " foo bar"  # two arguments required
        script.Script(f, tmaster)  # Loads the script file.