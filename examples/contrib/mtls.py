"""
Dynamically generate client certificates for mTLS traffic (instead of using a hardcoded one).

author: Garen Fang
email: fungaren@qq.com
usage:

mkdir certs

# Generate a self-signed root CA for servers.
openssl req -new -x509 -newkey rsa:2048 -nodes -utf8 -sha256 -days 36500 \
  -subj "/CN=server-ca" -outform PEM -out ./certs/server-ca.crt -keyout ./certs/server-ca.key

# Generate a self-signed root CA for clients.
openssl req -new -x509 -newkey rsa:2048 -nodes -utf8 -sha256 -days 36500 \
  -subj "/CN=client-ca" -outform PEM -out ./certs/client-ca.crt -keyout ./certs/client-ca.key

# Generate the server cert.
cat > ./certs/server-csr.conf <<EOF
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[ dn ]
CN = mtls-server

[ req_ext ]
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = example.org
DNS.2 = localhost
IP.1 = 127.0.0.1
IP.2 = 0:0:0:0:0:0:0:1

[ v3_ext ]
authorityKeyIdentifier=keyid,issuer:always
basicConstraints=CA:FALSE
keyUsage=keyEncipherment,dataEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names
EOF
openssl genrsa -out ./certs/server.key 2048
openssl req -new -key ./certs/server.key -out ./certs/server.csr -config ./certs/server-csr.conf
openssl x509 -req -in ./certs/server.csr -CA ./certs/server-ca.crt -CAkey ./certs/server-ca.key \
    -CAcreateserial -out ./certs/server.crt -days 36500 \
    -extensions v3_ext -extfile ./certs/server-csr.conf -sha256

# Generate the client cert.
cat > ./certs/client-csr.conf <<EOF
[ req ]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[ dn ]
O = world
CN = hello

[ v3_ext ]
authorityKeyIdentifier=keyid,issuer:always
basicConstraints=CA:FALSE
keyUsage=keyEncipherment,dataEncipherment
extendedKeyUsage=clientAuth
EOF
openssl genrsa -out ./certs/client.key 2048
openssl req -new -key ./certs/client.key -out ./certs/client.csr -config ./certs/client-csr.conf
openssl x509 -req -in ./certs/client.csr -CA ./certs/client-ca.crt -CAkey ./certs/client-ca.key \
    -CAcreateserial -out ./certs/client.crt -days 36500 \
    -extensions v3_ext -extfile ./certs/client-csr.conf -sha256

# Start the mTLS server
openssl s_server -port 4433 -www \
-verifyCAfile ./certs/client-ca.crt \
-cert ./certs/server.crt -key ./certs/server.key

cat ./certs/server-ca.crt ./certs/server-ca.key > ./certs/server-ca.pem
cat ./certs/client-ca.crt ./certs/client-ca.key > ./certs/client-ca.pem

# Start mitmproxy
mitmdump -p 8080 -m reverse:https://127.0.0.1:4433 -s ./mtls.py \
--set server_ca=./certs/server-ca.pem \
--set client_ca=./certs/client-ca.pem

# Start the mTLS connection. Disable TLS session cache to force curl always send client cert.
# TODO: If addons/tlsconfig.py is ready to support session resumption, this option is no longer required.
curl -kv --no-sessionid --cert ./certs/client.crt --key ./certs/client.key https://127.0.0.1:8080
"""
import logging
import os
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509 import ExtendedKeyUsageOID
from OpenSSL import crypto
from OpenSSL import SSL

from mitmproxy import addonmanager
from mitmproxy import certs
from mitmproxy import connection
from mitmproxy import ctx
from mitmproxy import exceptions
from mitmproxy import tls
from mitmproxy.addons import tlsconfig


def monkey_dummy_cert(
    privkey: rsa.RSAPrivateKey,
    cacert: x509.Certificate,
    commonname: str | None,
    sans: list[str],
    organization: str | None = None,
) -> certs.Cert:
    builder = certs.make_certificate_builder(
        privkey, cacert, commonname, sans, organization
    )

    # To generate a valid client certificate, we must add CLIENT_AUTH to ExtendKeyUsage.
    for ext in builder._extensions:
        if isinstance(ext._value, x509.ExtendedKeyUsage):
            ext._value._usages.append(ExtendedKeyUsageOID.CLIENT_AUTH)

    cert = builder.sign(private_key=privkey, algorithm=hashes.SHA256())  # type: ignore
    return certs.Cert(cert)


class MutualTLS(tlsconfig.TlsConfig):
    clientCertStore: certs.CertStore = None  # type: ignore

    def load(self, loader: addonmanager.Loader):
        loader.add_option(
            "client_ca",
            typespec=str,
            help="client CA certificate for dynamic generating client certs",
            default="",
        )
        loader.add_option(
            "server_ca",
            typespec=str,
            help="server CA certificate for dynamic generating server certs",
            default="",
        )

        certs.dummy_cert = monkey_dummy_cert

        # Must be lazy. This makes mitmproxy extract the client certificate
        # before connecting to the server.
        ctx.options.connection_strategy = "lazy"
        ctx.options.tls_request_client_cert = True

    def configure(self, updated: set[str]):
        # Override original process of loading certs.

        if ctx.options.client_ca == "":
            raise exceptions.OptionsError("client_ca is empty")
        if ctx.options.server_ca == "":
            raise exceptions.OptionsError("server_ca is empty")

        if "client_ca" in updated:
            ca_path = os.path.expanduser(ctx.options.client_ca)
            self.clientCertStore = certs.CertStore.from_files(
                ca_file=Path(ca_path),
                dhparam_file=Path(ca_path + ".dhparam.pem"),
            )
        if "server_ca" in updated:
            ca_path = os.path.expanduser(ctx.options.server_ca)
            self.certstore = certs.CertStore.from_files(
                ca_file=Path(ca_path),
                dhparam_file=Path(ca_path + ".dhparam.pem"),
            )
            ctx.options.ssl_verify_upstream_trusted_ca = ctx.options.server_ca

    def tls_start_client(self, data: tls.TlsData):
        # In this stage, mitmproxy generates a fake cert to impersonate the real server.

        super().tls_start_client(data)

        server_cert = data.ssl_conn.get_certificate()
        logging.info(
            "tls_start_client: fake server cert: %s", server_cert.get_subject()
        )

    def tls_start_server(self, data: tls.TlsData):
        # In this stage, we use the fake client cert to connect the server.

        client_certs = data.context.client.certificate_list
        if client_certs and len(client_certs) > 0:
            c = client_certs[0]
            entry = self.clientCertStore.get_cert(c.cn, [], c.organization)
            logging.info(
                "tls_start_server: client cert: CN=%s O=%s", c.cn, c.organization
            )

            def monkey_use_client_cert(context: SSL.Context, server: connection.Server):
                context.use_privatekey(
                    crypto.PKey.from_cryptography_key(entry.privatekey)
                )
                context.use_certificate(entry.cert.to_pyopenssl())

            tlsconfig.use_client_cert = monkey_use_client_cert
        else:
            logging.info("tls_start_server: no client cert")

            def monkey_use_client_cert(context: SSL.Context, server: connection.Server):
                # Here we never set the client certificate, it still provides a client cert for the
                # server, then the server will accept the request.
                # This is because mitmproxy have a LRU cache applied to
                # create_proxy_server_context() which leads to the SSL context reuse.
                pass

            tlsconfig.use_client_cert = monkey_use_client_cert

            # To address the problem, we construct a normal connection so that the server can reject
            # the anonymous request.
            data.ssl_conn = SSL.Connection(SSL.Context(SSL.TLS_CLIENT_METHOD))
            data.ssl_conn.set_connect_state()
            return

        super().tls_start_server(data)


addons = [MutualTLS()]
