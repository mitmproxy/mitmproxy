from mitmproxy.addons import anticache
from mitmproxy.addons import anticomp
from mitmproxy.addons import check_alpn
from mitmproxy.addons import check_ca
from mitmproxy.addons import clientplayback
from mitmproxy.addons import core_option_validation
from mitmproxy.addons import core
from mitmproxy.addons import cut
from mitmproxy.addons import disable_h2c
from mitmproxy.addons import onboarding
from mitmproxy.addons import proxyauth
from mitmproxy.addons import replace
from mitmproxy.addons import script
from mitmproxy.addons import serverplayback
from mitmproxy.addons import setheaders
from mitmproxy.addons import stickyauth
from mitmproxy.addons import stickycookie
from mitmproxy.addons import streambodies
from mitmproxy.addons import save
from mitmproxy.addons import upstream_auth


def default_addons():
    return [
        core.Core(),
        core_option_validation.CoreOptionValidation(),
        anticache.AntiCache(),
        anticomp.AntiComp(),
        check_alpn.CheckALPN(),
        check_ca.CheckCA(),
        clientplayback.ClientPlayback(),
        cut.Cut(),
        disable_h2c.DisableH2C(),
        onboarding.Onboarding(),
        proxyauth.ProxyAuth(),
        replace.Replace(),
        script.ScriptLoader(),
        serverplayback.ServerPlayback(),
        setheaders.SetHeaders(),
        stickyauth.StickyAuth(),
        stickycookie.StickyCookie(),
        streambodies.StreamBodies(),
        save.Save(),
        upstream_auth.UpstreamAuth(),
    ]
