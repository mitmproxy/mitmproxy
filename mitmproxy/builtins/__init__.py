from __future__ import absolute_import, print_function, division

from mitmproxy.builtins import anticache
from mitmproxy.builtins import anticomp
from mitmproxy.builtins import stickyauth
from mitmproxy.builtins import stickycookie
from mitmproxy.builtins import script
from mitmproxy.builtins import stream


def default_addons():
    return [
        anticache.AntiCache(),
        anticomp.AntiComp(),
        stickyauth.StickyAuth(),
        stickycookie.StickyCookie(),
        script.ScriptLoader(),
        stream.Stream(),
    ]
