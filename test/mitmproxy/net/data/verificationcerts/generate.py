"""
Generate SSL test certificates.
"""

import os
import shlex
import shutil
import subprocess
import textwrap

ROOT_CA = "trusted-root"
SUBJECT = "example.mitmproxy.org"


def do(args):
    print("> %s" % args)
    args = shlex.split(args)
    output = subprocess.check_output(args)
    return output


def genrsa(cert: str):
    do(f"openssl genrsa -out {cert}.key 2048")


def sign(cert: str, *exts: str):
    with open(f"openssl-{cert}.conf", "w") as f:
        f.write(
            textwrap.dedent(
                f"""
        authorityKeyIdentifier=keyid,issuer
        basicConstraints=CA:FALSE
        keyUsage = digitalSignature, keyEncipherment
        """
            )
            + "\n".join(exts)
        )
    do(
        f"openssl x509 -req -in {cert}.csr "
        f"-CA {ROOT_CA}.crt "
        f"-CAkey {ROOT_CA}.key "
        f"-CAcreateserial "
        f"-days 7300 "
        f"-sha256 "
        f'-extfile "openssl-{cert}.conf" '
        f"-out {cert}.crt"
    )
    os.remove(f"openssl-{cert}.conf")


def mkcert(cert, subject: str, *exts: str):
    genrsa(cert)
    do(
        f"openssl req -new -nodes -batch "
        f"-key {cert}.key "
        f"-subj /CN={subject}/O=mitmproxy "
        + "".join(f'-addext "{ext}" ' for ext in exts)
        + f"-out {cert}.csr"
    )
    sign(cert, *exts)
    os.remove(f"{cert}.csr")


# create trusted root CA
genrsa("trusted-root")
do(
    "openssl req -x509 -new -nodes -batch "
    "-key trusted-root.key "
    "-days 7300 "
    "-out trusted-root.crt"
)
h = do("openssl x509 -hash -noout -in trusted-root.crt").decode("ascii").strip()
shutil.copyfile("trusted-root.crt", f"{h}.0")

# create trusted leaf certs.
mkcert(
    "trusted-leaf",
    SUBJECT,
    f"subjectAltName = DNS:{SUBJECT}",
    "crlDistributionPoints = URI:https://trusted-root/example.crl",
)
mkcert("trusted-leaf-ip", "192.0.2.42", f"subjectAltName = IP:192.0.2.42")
mkcert(
    "trusted-client-cert",
    "client.mitmproxy.org",
    "subjectAltName = DNS:client.mitmproxy.org",
    "extendedKeyUsage = clientAuth",
)

# create self-signed cert
genrsa("self-signed")
do(
    "openssl req -x509 -new -nodes -batch "
    "-key self-signed.key "
    f'-addext "subjectAltName = DNS:{SUBJECT}" '
    "-days 7300 "
    "-out self-signed.crt"
)

for x in [
    "self-signed",
    "trusted-leaf",
    "trusted-leaf-ip",
    "trusted-root",
    "trusted-client-cert",
]:
    with open(f"{x}.crt") as crt, open(f"{x}.key") as key, open(f"{x}.pem", "w") as pem:
        pem.write(crt.read())
        pem.write(key.read())

shutil.copyfile("trusted-leaf.pem", "example.mitmproxy.org.pem")
with (
    open(f"trusted-leaf.crt") as crt,
    open(f"self-signed.key") as key,
    open(f"private-public-mismatch.pem", "w") as pem,
):
    pem.write(crt.read())
    pem.write(key.read())

with (
    open(f"trusted-leaf.pem") as crt1,
    open(f"trusted-root.crt") as crt2,
    open(f"trusted-chain.pem", "w") as pem,
):
    pem.write(crt1.read())
    pem.write(crt2.read())

with open(f"trusted-leaf.pem") as crt1, open(f"trusted-chain-invalid.pem", "w") as pem:
    pem.write(crt1.read())
    pem.write("-----BEGIN CERTIFICATE-----\nnotacert\n-----END CERTIFICATE-----\n")

mkcert("invalid-crl", SUBJECT, "crlDistributionPoints = URI://[")
os.remove("invalid-crl.key")
