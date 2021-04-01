import mitmproxy
from mitmproxy import ctx
from mitmproxy.certs import Cert
import ipaddress
import OpenSSL
import time


# Certificate for client connection is generated in dummy_cert() in certs.py. Monkeypatching
# the function to generate test cases for SSL Pinning.

def monkey_dummy_cert(privkey, cacert, commonname, sans):
    ss = []
    for i in sans:
        try:
            ipaddress.ip_address(i.decode("ascii"))
        except ValueError:
            # Change values in Certificate's Alt Name as well.
            if ctx.options.certwrongCN:
                ss.append(b"DNS:%sm" % i)
            else:
                ss.append(b"DNS:%s" % i)
        else:
            ss.append(b"IP:%s" % i)
    ss = b", ".join(ss)

    cert = OpenSSL.crypto.X509()
    if ctx.options.certbeginon:
        # Set certificate start time somewhere in the future
        cert.gmtime_adj_notBefore(3600 * 48)
    else:
        cert.gmtime_adj_notBefore(-3600 * 48)

    if ctx.options.certexpire:
        # sets the expire date of the certificate in the past.
        cert.gmtime_adj_notAfter(-3600 * 24)
    else:
        cert.gmtime_adj_notAfter(94608000)  # = 24 * 60 * 60 * 365 * 3

    cert.set_issuer(cacert.get_subject())
    if commonname is not None and len(commonname) < 64:
        if ctx.options.certwrongCN:
            # append an extra char to make certs common name different than original one.
            # APpending a char in the end of the domain name.
            new_cn = commonname + b'm'
            cert.get_subject().CN = new_cn

        else:
            cert.get_subject().CN = commonname

    cert.set_serial_number(int(time.time() * 10000))
    if ss:
        cert.set_version(2)
        cert.add_extensions(
            [OpenSSL.crypto.X509Extension(b"subjectAltName", False, ss)])
        cert.set_pubkey(cacert.get_pubkey())
        cert.sign(privkey, "sha256")
        return Cert(cert)


class CheckSSLPinning:
    def load(self, loader):
        loader.add_option(
            "certbeginon", bool, False,
            """
            Sets SSL Certificate's 'Begins On' time in future.
            """
        )
        loader.add_option(
            "certexpire", bool, False,
            """
            Sets SSL Certificate's 'Expires On' time in the past.
            """
        )

        loader.add_option(
            "certwrongCN", bool, False,
            """
            Sets SSL Certificate's CommonName(CN) different from the domain name.
            """
        )

    def clientconnect(self, layer):
        mitmproxy.certs.dummy_cert = monkey_dummy_cert
