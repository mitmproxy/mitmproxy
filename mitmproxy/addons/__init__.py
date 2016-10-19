from mitmproxy.addons import anticache
from mitmproxy.addons import anticomp
from mitmproxy.addons import clientplayback
from mitmproxy.addons import filestreamer
from mitmproxy.addons import onboarding
from mitmproxy.addons import replace
from mitmproxy.addons import script
from mitmproxy.addons import setheaders
from mitmproxy.addons import serverplayback
from mitmproxy.addons import stickyauth
from mitmproxy.addons import stickycookie
from mitmproxy.addons import streambodies


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
