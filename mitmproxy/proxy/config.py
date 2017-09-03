import os
import re
import typing

from OpenSSL import SSL, crypto

from mitmproxy import exceptions
from mitmproxy import options as moptions
from mitmproxy import certs
from mitmproxy.net import tls
from mitmproxy.net import server_spec

CONF_BASENAME = "mitmproxy"


class HostMatcher:

    def __init__(self, patterns=tuple()):
        self.patterns = list(patterns)
        self.regexes = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def __call__(self, address):
        if not address:
            return False
        host = "%s:%s" % address
        if any(rex.search(host) for rex in self.regexes):
            return True
        else:
            return False

    def __bool__(self):
        return bool(self.patterns)


class ProxyConfig:

    def __init__(self, options: moptions.Options) -> None:
        self.options = options

        self.check_ignore = None  # type: HostMatcher
        self.check_tcp = None  # type: HostMatcher
        self.certstore = None  # type: certs.CertStore
        self.client_certs = None  # type: str
        self.openssl_verification_mode_server = None  # type: int
        self.upstream_server = None  # type: typing.Optional[server_spec.ServerSpec]
        self.configure(options, set(options.keys()))
        options.changed.connect(self.configure)

    def configure(self, options: moptions.Options, updated: typing.Any) -> None:
        if options.add_upstream_certs_to_client_chain and not options.ssl_insecure:
            raise exceptions.OptionsError(
                "The verify-upstream-cert requires certificate verification to be disabled. "
                "If upstream certificates are verified then extra upstream certificates are "
                "not available for inclusion to the client chain."
            )

        if options.ssl_insecure:
            self.openssl_verification_mode_server = SSL.VERIFY_NONE
        else:
            self.openssl_verification_mode_server = SSL.VERIFY_PEER

        if "ignore_hosts" in updated:
            self.check_ignore = HostMatcher(options.ignore_hosts)
        if "tcp_hosts" in updated:
            self.check_tcp = HostMatcher(options.tcp_hosts)

        self.openssl_method_client, self.openssl_options_client = \
            tls.VERSION_CHOICES[options.ssl_version_client]
        self.openssl_method_server, self.openssl_options_server = \
            tls.VERSION_CHOICES[options.ssl_version_server]

        certstore_path = os.path.expanduser(options.cadir)
        if not os.path.exists(os.path.dirname(certstore_path)):
            raise exceptions.OptionsError(
                "Certificate Authority parent directory does not exist: %s" %
                os.path.dirname(options.cadir)
            )
        self.certstore = certs.CertStore.from_store(
            certstore_path,
            CONF_BASENAME
        )

        if options.client_certs:
            client_certs = os.path.expanduser(options.client_certs)
            if not os.path.exists(client_certs):
                raise exceptions.OptionsError(
                    "Client certificate path does not exist: %s" %
                    options.client_certs
                )
            self.client_certs = client_certs

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
