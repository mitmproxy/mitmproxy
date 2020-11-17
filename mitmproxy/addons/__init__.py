from mitmproxy.addons import anticache
from mitmproxy.addons import anticomp
from mitmproxy.addons import block
from mitmproxy.addons import browser
from mitmproxy.addons import check_ca
from mitmproxy.addons import clientplayback
from mitmproxy.addons import command_history
from mitmproxy.addons import core
from mitmproxy.addons import cut
from mitmproxy.addons import disable_h2c
from mitmproxy.addons import export
from mitmproxy.addons import next_layer
from mitmproxy.addons import onboarding
from mitmproxy.addons import proxyserver
from mitmproxy.addons import proxyauth
from mitmproxy.addons import script
from mitmproxy.addons import serverplayback
from mitmproxy.addons import mapremote
from mitmproxy.addons import maplocal
from mitmproxy.addons import modifybody
from mitmproxy.addons import modifyheaders
from mitmproxy.addons import stickyauth
from mitmproxy.addons import stickycookie
from mitmproxy.addons import streambodies
from mitmproxy.addons import save
from mitmproxy.addons import tlsconfig
from mitmproxy.addons import upstream_auth
from mitmproxy.utils import compat

if compat.new_proxy_core:  # pragma: no cover
    from mitmproxy.addons import clientplayback_sansio as clientplayback  # noqa


def default_addons():
    return [
        core.Core(),
        browser.Browser(),
        block.Block(),
        anticache.AntiCache(),
        anticomp.AntiComp(),
        check_ca.CheckCA(),
        clientplayback.ClientPlayback(),
        command_history.CommandHistory(),
        cut.Cut(),
        disable_h2c.DisableH2C(),
        export.Export(),
        next_layer.NextLayer(),
        onboarding.Onboarding(),
        proxyauth.ProxyAuth(),
        proxyserver.Proxyserver(),
        script.ScriptLoader(),
        serverplayback.ServerPlayback(),
        mapremote.MapRemote(),
        maplocal.MapLocal(),
        modifybody.ModifyBody(),
        modifyheaders.ModifyHeaders(),
        stickyauth.StickyAuth(),
        stickycookie.StickyCookie(),
        streambodies.StreamBodies(),
        save.Save(),
        tlsconfig.TlsConfig(),
        upstream_auth.UpstreamAuth(),
    ]
