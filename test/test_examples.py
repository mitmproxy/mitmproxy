from libmproxy import utils, script
import glob
from libmproxy.proxy import config
import tservers

example_dir = utils.Data("libmproxy").path("../examples")
scripts = glob.glob("%s/*.py" % example_dir)

tmaster = tservers.TestMaster(config.ProxyConfig())

for f in scripts:
    script.Script(f, tmaster)  # Loads the script file.