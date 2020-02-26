import os
import re
import typing

from OpenSSL import crypto

from mitmproxy import certs
from mitmproxy import exceptions
from mitmproxy import options as moptions
from mitmproxy.net import server_spec


class HostMatcher:
    def __init__(self, handle, patterns=tuple()):
        self.handle = handle
        self.patterns = list(patterns)
        self.regexes = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def __call__(self, address):
        if not address:
            return False
        host = "%s:%s" % address
        if self.handle in ["ignore", "tcp"]:
            return any(rex.search(host) for rex in self.regexes)
        else:  # self.handle == "allow"
            return not any(rex.search(host) for rex in self.regexes)

    def __bool__(self):
        return bool(self.patterns)


class ProxyConfig:

    def __init__(self, options: moptions.Options) -> None:
        self.options = options

        self.certstore: certs.CertStore
        self.check_filter: typing.Optional[HostMatcher] = None
        self.check_tcp: typing.Optional[HostMatcher] = None
        self.upstream_server: typing.Optional[server_spec.ServerSpec] = None
        self.configure(options, set(options.keys()))
        options.changed.connect(self.configure)

    def configure(self, options: moptions.Options, updated: typing.Any) -> None:
        if options.allow_hosts and options.ignore_hosts:
            raise exceptions.OptionsError("--ignore-hosts and --allow-hosts are mutually "
                                          "exclusive; please choose one.")

        if options.ignore_hosts:
            self.check_filter = HostMatcher("ignore", options.ignore_hosts)
        elif options.allow_hosts:
            self.check_filter = HostMatcher("allow", options.allow_hosts)
        else:
            self.check_filter = HostMatcher(False)
        if "tcp_hosts" in updated:
            self.check_tcp = HostMatcher("tcp", options.tcp_hosts)

        certstore_path = os.path.expanduser(options.confdir)
        if not os.path.exists(os.path.dirname(certstore_path)):
            raise exceptions.OptionsError(
                "Certificate Authority parent directory does not exist: %s" %
                os.path.dirname(certstore_path)
            )
        key_size = options.key_size
        self.certstore = certs.CertStore.from_store(
            certstore_path,
            moptions.CONF_BASENAME,
            key_size
        )

        for c in options.certs:
            parts = c.split("=", 1)
            if len(parts) == 1:
                parts = ["*", parts[0]]

            cert = os.path.expanduser(parts[1])
            if not os.path.exists(cert):
                raise exceptions.OptionsError(
                    "Certificate file does not exist: %s" % cert
                )
            try:
                self.certstore.add_cert_file(parts[0], cert)
            except crypto.Error:
                raise exceptions.OptionsError(
                    "Invalid certificate format: %s" % cert
                )
        m = options.mode
        if m.startswith("upstream:") or m.startswith("reverse:"):
            _, spec = server_spec.parse_with_mode(options.mode)
            self.upstream_server = spec
