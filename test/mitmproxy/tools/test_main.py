from mitmproxy.test import tutils
from mitmproxy.tools import main

shutdown_script = tutils.test_data.path("mitmproxy/data/addonscripts/shutdown.py")


def test_mitmweb():
    main.mitmweb([
        "--no-web-open-browser",
        "-q",
        "-s", shutdown_script
    ])


def test_mitmdump():
    main.mitmdump([
        "-q",
        "-s", shutdown_script
    ])
