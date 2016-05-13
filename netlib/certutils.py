from __future__ import (absolute_import, print_function, division)
import os
import ssl
import time
import datetime
from six.moves import filter
import ipaddress

import sys
from pyasn1.type import univ, constraint, char, namedtype, tag
from pyasn1.codec.der.decoder import decode
from pyasn1.error import PyAsn1Error
import OpenSSL

from .utils import Serializable

# Default expiry must not be too long: https://github.com/mitmproxy/mitmproxy/issues/815

DEFAULT_EXP = 94608000  # = 24 * 60 * 60 * 365 * 3
# Generated with "openssl dhparam". It's too slow to generate this on startup.
DEFAULT_DHPARAM = b"""
-----BEGIN DH PARAMETERS-----
MIICCAKCAgEAyT6LzpwVFS3gryIo29J5icvgxCnCebcdSe/NHMkD8dKJf8suFCg3
O2+dguLakSVif/t6dhImxInJk230HmfC8q93hdcg/j8rLGJYDKu3ik6H//BAHKIv
j5O9yjU3rXCfmVJQic2Nne39sg3CreAepEts2TvYHhVv3TEAzEqCtOuTjgDv0ntJ
Gwpj+BJBRQGG9NvprX1YGJ7WOFBP/hWU7d6tgvE6Xa7T/u9QIKpYHMIkcN/l3ZFB
chZEqVlyrcngtSXCROTPcDOQ6Q8QzhaBJS+Z6rcsd7X+haiQqvoFcmaJ08Ks6LQC
ZIL2EtYJw8V8z7C0igVEBIADZBI6OTbuuhDwRw//zU1uq52Oc48CIZlGxTYG/Evq
o9EWAXUYVzWkDSTeBH1r4z/qLPE2cnhtMxbFxuvK53jGB0emy2y1Ei6IhKshJ5qX
IB/aE7SSHyQ3MDHHkCmQJCsOd4Mo26YX61NZ+n501XjqpCBQ2+DfZCBh8Va2wDyv
A2Ryg9SUz8j0AXViRNMJgJrr446yro/FuJZwnQcO3WQnXeqSBnURqKjmqkeFP+d8
6mk2tqJaY507lRNqtGlLnj7f5RNoBFJDCLBNurVgfvq9TCVWKDIFD4vZRjCrnl6I
rD693XKIHUCWOjMh1if6omGXKHH40QuME2gNa50+YPn1iYDl88uDbbMCAQI=
-----END DH PARAMETERS-----
"""


def create_ca(o, cn, exp):
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
    cert = OpenSSL.crypto.X509()
    cert.set_serial_number(int(time.time() * 10000))
    cert.set_version(2)
    cert.get_subject().CN = cn
    cert.get_subject().O = o
    cert.gmtime_adj_notBefore(-3600 * 48)
    cert.gmtime_adj_notAfter(exp)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.add_extensions([
        OpenSSL.crypto.X509Extension(
            b"basicConstraints",
            True,
            b"CA:TRUE"
        ),
        OpenSSL.crypto.X509Extension(
            b"nsCertType",
            False,
            b"sslCA"
        ),
        OpenSSL.crypto.X509Extension(
            b"extendedKeyUsage",
            False,
            b"serverAuth,clientAuth,emailProtection,timeStamping,msCodeInd,msCodeCom,msCTLSign,msSGC,msEFS,nsSGC"
        ),
        OpenSSL.crypto.X509Extension(
            b"keyUsage",
            True,
            b"keyCertSign, cRLSign"
        ),
        OpenSSL.crypto.X509Extension(
            b"subjectKeyIdentifier",
            False,
            b"hash",
            subject=cert
        ),
    ])
    cert.sign(key, "sha256")
    return key, cert


def dummy_cert(privkey, cacert, commonname, sans):
    """
        Generates a dummy certificate.

        privkey: CA private key
        cacert: CA certificate
        commonname: Common name for the generated certificate.
        sans: A list of Subject Alternate Names.

        Returns cert if operation succeeded, None if not.
    """
    ss = []
    for i in sans:
        try:
            ipaddress.ip_address(i.decode("ascii"))
        except ValueError:
            ss.append(b"DNS: %s" % i)
        else:
            ss.append(b"IP: %s" % i)
    ss = b", ".join(ss)

    cert = OpenSSL.crypto.X509()
    cert.gmtime_adj_notBefore(-3600 * 48)
    cert.gmtime_adj_notAfter(DEFAULT_EXP)
    cert.set_issuer(cacert.get_subject())
    if commonname is not None:
        cert.get_subject().CN = commonname
    cert.set_serial_number(int(time.time() * 10000))
    if ss:
        cert.set_version(2)
        cert.add_extensions(
            [OpenSSL.crypto.X509Extension(b"subjectAltName", False, ss)])
    cert.set_pubkey(cacert.get_pubkey())
    cert.sign(privkey, "sha256")
    return SSLCert(cert)


# DNTree did not pass TestCertStore.test_sans_change and is temporarily replaced by a simple dict.
#
# class _Node(UserDict.UserDict):
#     def __init__(self):
#         UserDict.UserDict.__init__(self)
#         self.value = None
#
#
# class DNTree:
#     """
#         Domain store that knows about wildcards. DNS wildcards are very
#         restricted - the only valid variety is an asterisk on the left-most
#         domain component, i.e.:
#
#             *.foo.com
#     """
#     def __init__(self):
#         self.d = _Node()
#
#     def add(self, dn, cert):
#         parts = dn.split(".")
#         parts.reverse()
#         current = self.d
#         for i in parts:
#             current = current.setdefault(i, _Node())
#         current.value = cert
#
#     def get(self, dn):
#         parts = dn.split(".")
#         current = self.d
#         for i in reversed(parts):
#             if i in current:
#                 current = current[i]
#             elif "*" in current:
#                 return current["*"].value
#             else:
#                 return None
#         return current.value


class CertStoreEntry(object):

    def __init__(self, cert, privatekey, chain_file):
        self.cert = cert
        self.privatekey = privatekey
        self.chain_file = chain_file


class CertStore(object):

    """
        Implements an in-memory certificate store.
    """

    def __init__(
            self,
            default_privatekey,
            default_ca,
            default_chain_file,
            dhparams):
        self.default_privatekey = default_privatekey
        self.default_ca = default_ca
        self.default_chain_file = default_chain_file
        self.dhparams = dhparams
        self.certs = dict()

    @staticmethod
    def load_dhparam(path):

        # netlib<=0.10 doesn't generate a dhparam file.
        # Create it now if neccessary.
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(DEFAULT_DHPARAM)

        bio = OpenSSL.SSL._lib.BIO_new_file(path.encode(sys.getfilesystemencoding()), b"r")
        if bio != OpenSSL.SSL._ffi.NULL:
            bio = OpenSSL.SSL._ffi.gc(bio, OpenSSL.SSL._lib.BIO_free)
            dh = OpenSSL.SSL._lib.PEM_read_bio_DHparams(
                bio,
                OpenSSL.SSL._ffi.NULL,
                OpenSSL.SSL._ffi.NULL,
                OpenSSL.SSL._ffi.NULL)
            dh = OpenSSL.SSL._ffi.gc(dh, OpenSSL.SSL._lib.DH_free)
            return dh

    @classmethod
    def from_store(cls, path, basename):
        ca_path = os.path.join(path, basename + "-ca.pem")
        if not os.path.exists(ca_path):
            key, ca = cls.create_store(path, basename)
        else:
            with open(ca_path, "rb") as f:
                raw = f.read()
            ca = OpenSSL.crypto.load_certificate(
                OpenSSL.crypto.FILETYPE_PEM,
                raw)
            key = OpenSSL.crypto.load_privatekey(
                OpenSSL.crypto.FILETYPE_PEM,
                raw)
        dh_path = os.path.join(path, basename + "-dhparam.pem")
        dh = cls.load_dhparam(dh_path)
        return cls(key, ca, ca_path, dh)

    @staticmethod
    def create_store(path, basename, o=None, cn=None, expiry=DEFAULT_EXP):
        if not os.path.exists(path):
            os.makedirs(path)

        o = o or basename
        cn = cn or basename

        key, ca = create_ca(o=o, cn=cn, exp=expiry)
        # Dump the CA plus private key
        with open(os.path.join(path, basename + "-ca.pem"), "wb") as f:
            f.write(
                OpenSSL.crypto.dump_privatekey(
                    OpenSSL.crypto.FILETYPE_PEM,
                    key))
            f.write(
                OpenSSL.crypto.dump_certificate(
                    OpenSSL.crypto.FILETYPE_PEM,
                    ca))

        # Dump the certificate in PEM format
        with open(os.path.join(path, basename + "-ca-cert.pem"), "wb") as f:
            f.write(
                OpenSSL.crypto.dump_certificate(
                    OpenSSL.crypto.FILETYPE_PEM,
                    ca))

        # Create a .cer file with the same contents for Android
        with open(os.path.join(path, basename + "-ca-cert.cer"), "wb") as f:
            f.write(
                OpenSSL.crypto.dump_certificate(
                    OpenSSL.crypto.FILETYPE_PEM,
                    ca))

        # Dump the certificate in PKCS12 format for Windows devices
        with open(os.path.join(path, basename + "-ca-cert.p12"), "wb") as f:
            p12 = OpenSSL.crypto.PKCS12()
            p12.set_certificate(ca)
            p12.set_privatekey(key)
            f.write(p12.export())

        with open(os.path.join(path, basename + "-dhparam.pem"), "wb") as f:
            f.write(DEFAULT_DHPARAM)

        return key, ca

    def add_cert_file(self, spec, path):
        with open(path, "rb") as f:
            raw = f.read()
        cert = SSLCert(
            OpenSSL.crypto.load_certificate(
                OpenSSL.crypto.FILETYPE_PEM,
                raw))
        try:
            privatekey = OpenSSL.crypto.load_privatekey(
                OpenSSL.crypto.FILETYPE_PEM,
                raw)
        except Exception:
            privatekey = self.default_privatekey
        self.add_cert(
            CertStoreEntry(cert, privatekey, path),
            spec
        )

    def add_cert(self, entry, *names):
        """
            Adds a cert to the certstore. We register the CN in the cert plus
            any SANs, and also the list of names provided as an argument.
        """
        if entry.cert.cn:
            self.certs[entry.cert.cn] = entry
        for i in entry.cert.altnames:
            self.certs[i] = entry
        for i in names:
            self.certs[i] = entry

    @staticmethod
    def asterisk_forms(dn):
        if dn is None:
            return []
        parts = dn.split(b".")
        parts.reverse()
        curr_dn = b""
        dn_forms = [b"*"]
        for part in parts[:-1]:
            curr_dn = b"." + part + curr_dn  # .example.com
            dn_forms.append(b"*" + curr_dn)   # *.example.com
        if parts[-1] != b"*":
            dn_forms.append(parts[-1] + curr_dn)
        return dn_forms

    def get_cert(self, commonname, sans):
        """
            Returns an (cert, privkey, cert_chain) tuple.

            commonname: Common name for the generated certificate. Must be a
            valid, plain-ASCII, IDNA-encoded domain name.

            sans: A list of Subject Alternate Names.
        """

        potential_keys = self.asterisk_forms(commonname)
        for s in sans:
            potential_keys.extend(self.asterisk_forms(s))
        potential_keys.append((commonname, tuple(sans)))

        name = next(
            filter(lambda key: key in self.certs, potential_keys),
            None
        )
        if name:
            entry = self.certs[name]
        else:
            entry = CertStoreEntry(
                cert=dummy_cert(
                    self.default_privatekey,
                    self.default_ca,
                    commonname,
                    sans),
                privatekey=self.default_privatekey,
                chain_file=self.default_chain_file)
            self.certs[(commonname, tuple(sans))] = entry

        return entry.cert, entry.privatekey, entry.chain_file


class _GeneralName(univ.Choice):
    # We are only interested in dNSNames. We use a default handler to ignore
    # other types.
    # TODO: We should also handle iPAddresses.
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('dNSName', char.IA5String().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)
        )
        ),
    )


class _GeneralNames(univ.SequenceOf):
    componentType = _GeneralName()
    sizeSpec = univ.SequenceOf.sizeSpec + \
        constraint.ValueSizeConstraint(1, 1024)


class SSLCert(Serializable):

    def __init__(self, cert):
        """
            Returns a (common name, [subject alternative names]) tuple.
        """
        self.x509 = cert

    def __eq__(self, other):
        return self.digest("sha256") == other.digest("sha256")

    def __ne__(self, other):
        return not self.__eq__(other)

    def get_state(self):
        return self.to_pem()

    def set_state(self, state):
        self.x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, state)

    @classmethod
    def from_state(cls, state):
        return cls.from_pem(state)

    @classmethod
    def from_pem(cls, txt):
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, txt)
        return cls(x509)

    @classmethod
    def from_der(cls, der):
        pem = ssl.DER_cert_to_PEM_cert(der)
        return cls.from_pem(pem)

    def to_pem(self):
        return OpenSSL.crypto.dump_certificate(
            OpenSSL.crypto.FILETYPE_PEM,
            self.x509)

    def digest(self, name):
        return self.x509.digest(name)

    @property
    def issuer(self):
        return self.x509.get_issuer().get_components()

    @property
    def notbefore(self):
        t = self.x509.get_notBefore()
        return datetime.datetime.strptime(t.decode("ascii"), "%Y%m%d%H%M%SZ")

    @property
    def notafter(self):
        t = self.x509.get_notAfter()
        return datetime.datetime.strptime(t.decode("ascii"), "%Y%m%d%H%M%SZ")

    @property
    def has_expired(self):
        return self.x509.has_expired()

    @property
    def subject(self):
        return self.x509.get_subject().get_components()

    @property
    def serial(self):
        return self.x509.get_serial_number()

    @property
    def keyinfo(self):
        pk = self.x509.get_pubkey()
        types = {
            OpenSSL.crypto.TYPE_RSA: "RSA",
            OpenSSL.crypto.TYPE_DSA: "DSA",
        }
        return (
            types.get(pk.type(), "UNKNOWN"),
            pk.bits()
        )

    @property
    def cn(self):
        c = None
        for i in self.subject:
            if i[0] == b"CN":
                c = i[1]
        return c

    @property
    def altnames(self):
        """
        Returns:
            All DNS altnames.
        """
        # tcp.TCPClient.convert_to_ssl assumes that this property only contains DNS altnames for hostname verification.
        altnames = []
        for i in range(self.x509.get_extension_count()):
            ext = self.x509.get_extension(i)
            if ext.get_short_name() == b"subjectAltName":
                try:
                    dec = decode(ext.get_data(), asn1Spec=_GeneralNames())
                except PyAsn1Error:
                    continue
                for i in dec[0]:
                    altnames.append(i[0].asOctets())
        return altnames
