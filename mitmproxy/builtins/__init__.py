from __future__ import absolute_import, print_function, division

from mitmproxy.builtins import anticache
from mitmproxy.builtins import anticomp
from mitmproxy.builtins import filestreamer
from mitmproxy.builtins import stickyauth
from mitmproxy.builtins import stickycookie
from mitmproxy.builtins import script
from mitmproxy.builtins import replace
from mitmproxy.builtins import setheaders
from mitmproxy.builtins import serverplayback


def default_addons():
    return [
        anticache.AntiCache(),
        anticomp.AntiComp(),
        stickyauth.StickyAuth(),
        stickycookie.StickyCookie(),
        script.ScriptLoader(),
        filestreamer.FileStreamer(),
        replace.Replace(),
        setheaders.SetHeaders(),
        serverplayback.ServerPlayback()
    ]
