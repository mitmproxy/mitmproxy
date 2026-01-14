from mitmproxy.addons import core
from mitmproxy.addons import next_layer
from mitmproxy.addons import proxyauth
from mitmproxy.addons import proxyserver
from mitmproxy.addons import save
from mitmproxy.addons import savehar
from mitmproxy.addons import tlsconfig


def default_addons():
    return [
        core.Core(),
        proxyauth.ProxyAuth(),
        proxyserver.Proxyserver(),
        next_layer.NextLayer(),
        save.Save(),
        savehar.SaveHar(),
        tlsconfig.TlsConfig(),
    ]
