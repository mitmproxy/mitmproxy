from mitmproxy.addons import anticache
from mitmproxy.addons import anticomp
from mitmproxy.addons import clientplayback
from mitmproxy.addons import streamfile
from mitmproxy.addons import onboarding
from mitmproxy.addons import proxyauth
from mitmproxy.addons import replace
from mitmproxy.addons import script
from mitmproxy.addons import setheaders
from mitmproxy.addons import serverplayback
from mitmproxy.addons import stickyauth
from mitmproxy.addons import stickycookie
from mitmproxy.addons import streambodies
from mitmproxy.addons import upstream_auth
from mitmproxy.addons import disable_h2c_upgrade


def default_addons():
    return [
        onboarding.Onboarding(),
        proxyauth.ProxyAuth(),
        anticache.AntiCache(),
        anticomp.AntiComp(),
        stickyauth.StickyAuth(),
        stickycookie.StickyCookie(),
        script.ScriptLoader(),
        streamfile.StreamFile(),
        streambodies.StreamBodies(),
        replace.Replace(),
        setheaders.SetHeaders(),
        serverplayback.ServerPlayback(),
        clientplayback.ClientPlayback(),
        upstream_auth.UpstreamAuth(),
        disable_h2c_upgrade.DisableH2CleartextUpgrade(),
    ]
