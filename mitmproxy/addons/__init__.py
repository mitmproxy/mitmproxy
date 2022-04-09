from mitmproxy.addons import anticache
from mitmproxy.addons import anticomp
from mitmproxy.addons import block
from mitmproxy.addons import blocklist
from mitmproxy.addons import browser
from mitmproxy.addons import clientplayback
from mitmproxy.addons import command_history
from mitmproxy.addons import comment
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
from mitmproxy.addons import save
from mitmproxy.addons import tlsconfig
from mitmproxy.addons import upstream_auth


def default_addons():
    return [
        core.Core(),
        browser.Browser(),
        block.Block(),
        blocklist.BlockList(),
        anticache.AntiCache(),
        anticomp.AntiComp(),
        clientplayback.ClientPlayback(),
        command_history.CommandHistory(),
        comment.Comment(),
        cut.Cut(),
        disable_h2c.DisableH2C(),
        export.Export(),
        onboarding.Onboarding(),
        proxyauth.ProxyAuth(),
        proxyserver.Proxyserver(),
        script.ScriptLoader(),
        next_layer.NextLayer(),
        serverplayback.ServerPlayback(),
        mapremote.MapRemote(),
        maplocal.MapLocal(),
        modifybody.ModifyBody(),
        modifyheaders.ModifyHeaders(),
        stickyauth.StickyAuth(),
        stickycookie.StickyCookie(),
        save.Save(),
        tlsconfig.TlsConfig(),
        upstream_auth.UpstreamAuth(),
    ]
