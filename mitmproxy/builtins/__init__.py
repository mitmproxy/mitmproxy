from mitmproxy.builtins import anticache
from mitmproxy.builtins import anticomp
from mitmproxy.builtins import clientplayback
from mitmproxy.builtins import filestreamer
from mitmproxy.builtins import onboarding
from mitmproxy.builtins import replace
from mitmproxy.builtins import script
from mitmproxy.builtins import setheaders
from mitmproxy.builtins import serverplayback
from mitmproxy.builtins import stickyauth
from mitmproxy.builtins import stickycookie
from mitmproxy.builtins import streambodies


def default_addons():
    return [
        onboarding.Onboarding(),
        anticache.AntiCache(),
        anticomp.AntiComp(),
        stickyauth.StickyAuth(),
        stickycookie.StickyCookie(),
        script.ScriptLoader(),
        filestreamer.FileStreamer(),
        streambodies.StreamBodies(),
        replace.Replace(),
        setheaders.SetHeaders(),
        serverplayback.ServerPlayback(),
        clientplayback.ClientPlayback(),
    ]
