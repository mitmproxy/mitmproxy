import os
import ssl
import time
import datetime
import ipaddress
import sys
import typing
import contextlib

from pyasn1.type import univ, constraint, char, namedtype, tag
from pyasn1.codec.der.decoder import decode
from pyasn1.error import PyAsn1Error
import OpenSSL

from mitmproxy.coretypes import serializable

# Default expiry must not be too long: https://github.com/mitmproxy/mitmproxy/issues/815
DEFAULT_EXP = 94608000  # = 60 * 60 * 24 * 365 * 3 = 3 years
DEFAULT_EXP_DUMMY_CERT = 31536000  # = 60 * 60 * 24 * 365 = 1 year

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


def create_ca(organization, cn, exp, key_size):
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, key_size)
    cert = OpenSSL.crypto.X509()
    cert.set_serial_number(int(time.time() * 10000))
    cert.set_version(2)
    cert.get_subject().CN = cn
    cert.get_subject().O = organization
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


def dummy_cert(privkey, cacert, commonname, sans, organization):
    """
        Generates a dummy certificate.

        privkey: CA private key
        cacert: CA certificate
        commonname: Common name for the generated certificate.
        sans: A list of Subject Alternate Names.
        organization: Organization name for the generated certificate.

        Returns cert if operation succeeded, None if not.
    """
    ss = []
    for i in sans:
        try:
            ipaddress.ip_address(i.decode("ascii"))
        except ValueError:
            ss.append(b"DNS:%s" % i)
        else:
            ss.append(b"IP:%s" % i)
    ss = b", ".join(ss)

    cert = OpenSSL.crypto.X509()
    cert.gmtime_adj_notBefore(-3600 * 48)
    cert.gmtime_adj_notAfter(DEFAULT_EXP_DUMMY_CERT)
    cert.set_issuer(cacert.get_subject())
    is_valid_commonname = (
        commonname is not None and len(commonname) < 64
    )
    if is_valid_commonname:
        cert.get_subject().CN = commonname
    if organization is not None:
        cert.get_subject().O = organization
    cert.set_serial_number(int(time.time() * 10000))
    if ss:
        cert.set_version(2)
        cert.add_extensions(
            [OpenSSL.crypto.X509Extension(
                b"subjectAltName",
                # RFC 5280 §4.2.1.6: subjectAltName is critical if subject is empty.
                not is_valid_commonname,
                ss
            )]
        )
    cert.add_extensions([
        OpenSSL.crypto.X509Extension(
            b"extendedKeyUsage",
            False,
            b"serverAuth,clientAuth"
        )
    ])
    cert.set_pubkey(cacert.get_pubkey())
    cert.sign(privkey, "sha256")
    return Cert(cert)


class CertStoreEntry:

    def __init__(self, cert, privatekey, chain_file):
        self.cert = cert
        self.privatekey = privatekey
        self.chain_file = chain_file


TCustomCertId = bytes  # manually provided certs (e.g. mitmproxy's --certs)
TGeneratedCertId = typing.Tuple[typing.Optional[bytes], typing.Tuple[bytes, ...]]  # (common_name, sans)
TCertId = typing.Union[TCustomCertId, TGeneratedCertId]


class CertStore:

    """
        Implements an in-memory certificate store.
    """
    STORE_CAP = 100

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
        self.certs: typing.Dict[TCertId, CertStoreEntry] = {}
        self.expire_queue = []

    def expire(self, entry):
        self.expire_queue.append(entry)
        if len(self.expire_queue) > self.STORE_CAP:
            d = self.expire_queue.pop(0)
            self.certs = {k: v for k, v in self.certs.items() if v != d}

    @staticmethod
    def load_dhparam(path):

        # mitmproxy<=0.10 doesn't generate a dhparam file.
        # Create it now if necessary.
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
    def from_store(cls, path, basename, key_size):
        ca_path = os.path.join(path, basename + "-ca.pem")
        if not os.path.exists(ca_path):
            key, ca = cls.create_store(path, basename, key_size)
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
    @contextlib.contextmanager
    def umask_secret():
        """
            Context to temporarily set umask to its original value bitor 0o77.
            Useful when writing private keys to disk so that only the owner
            will be able to read them.
        """
        original_umask = os.umask(0)
        os.umask(original_umask | 0o77)
        try:
            yield
        finally:
            os.umask(original_umask)

    @staticmethod
    def create_store(path, basename, key_size, organization=None, cn=None, expiry=DEFAULT_EXP):
        if not os.path.exists(path):
            os.makedirs(path)

        organization = organization or basename
        cn = cn or basename

        key, ca = create_ca(organization=organization, cn=cn, exp=expiry, key_size=key_size)
        # Dump the CA plus private key
        with CertStore.umask_secret(), open(os.path.join(path, basename + "-ca.pem"), "wb") as f:
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
            f.write(p12.export())

        # Dump the certificate and key in a PKCS12 format for Windows devices
        with CertStore.umask_secret(), open(os.path.join(path, basename + "-ca.p12"), "wb") as f:
            p12 = OpenSSL.crypto.PKCS12()
            p12.set_certificate(ca)
            p12.set_privatekey(key)
            f.write(p12.export())

        with open(os.path.join(path, basename + "-dhparam.pem"), "wb") as f:
            f.write(DEFAULT_DHPARAM)

        return key, ca

    def add_cert_file(self, spec: str, path: str) -> None:
        with open(path, "rb") as f:
            raw = f.read()
        cert = Cert(
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
            spec.encode("idna")
        )

    def add_cert(self, entry: CertStoreEntry, *names: bytes):
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
    def asterisk_forms(dn: bytes) -> typing.List[bytes]:
        """
        Return all asterisk forms for a domain. For example, for www.example.com this will return
        [b"www.example.com", b"*.example.com", b"*.com"]. The single wildcard "*" is omitted.
        """
        parts = dn.split(b".")
        ret = [dn]
        for i in range(1, len(parts)):
            ret.append(b"*." + b".".join(parts[i:]))
        return ret

    def get_cert(
            self,
            commonname: typing.Optional[bytes],
            sans: typing.List[bytes],
            organization: typing.Optional[bytes] = None
    ) -> typing.Tuple["Cert", OpenSSL.SSL.PKey, str]:
        """
            Returns an (cert, privkey, cert_chain) tuple.

            commonname: Common name for the generated certificate. Must be a
            valid, plain-ASCII, IDNA-encoded domain name.

            sans: A list of Subject Alternate Names.

            organization: Organization name for the generated certificate.
        """

        potential_keys: typing.List[TCertId] = []
        if commonname:
            potential_keys.extend(self.asterisk_forms(commonname))
        for s in sans:
            potential_keys.extend(self.asterisk_forms(s))
        potential_keys.append(b"*")
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
                    sans,
                    organization),
                privatekey=self.default_privatekey,
                chain_file=self.default_chain_file)
            self.certs[(commonname, tuple(sans))] = entry
            self.expire(entry)

        return entry.cert, entry.privatekey, entry.chain_file


class _GeneralName(univ.Choice):
    # We only care about dNSName and iPAddress
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('dNSName', char.IA5String().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)
        )),
        namedtype.NamedType('iPAddress', univ.OctetString().subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7)
        )),
    )


class _GeneralNames(univ.SequenceOf):
    componentType = _GeneralName()
    sizeSpec = univ.SequenceOf.sizeSpec + \
        constraint.ValueSizeConstraint(1, 1024)


class Cert(serializable.Serializable):

    def __init__(self, cert):
        """
            Returns a (common name, [subject alternative names]) tuple.
        """
        self.x509 = cert

    def __eq__(self, other):
        return self.digest("sha256") == other.digest("sha256")

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
    def organization(self):
        c = None
        for i in self.subject:
            if i[0] == b"O":
                c = i[1]
        return c

    @property
    def altnames(self):
        """
        Returns:
            All DNS altnames.
        """
        # tcp.TCPClient.convert_to_tls assumes that this property only contains DNS altnames for hostname verification.
        altnames = []
        for i in range(self.x509.get_extension_count()):
            ext = self.x509.get_extension(i)
            if ext.get_short_name() == b"subjectAltName":
                try:
                    dec = decode(ext.get_data(), asn1Spec=_GeneralNames())
                except PyAsn1Error:
                    continue
                for i in dec[0]:
                    if i[0].hasValue():
                        e = i[0].asOctets()
                        altnames.append(e)

        return altnames
