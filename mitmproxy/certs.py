import contextlib
import datetime
import ipaddress
import os
import ssl
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional, Union, Dict, List

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import NameOID, ExtendedKeyUsageOID
from pyasn1.codec.der.decoder import decode
from pyasn1.error import PyAsn1Error
from pyasn1.type import univ, constraint, char, namedtype, tag

import OpenSSL
from mitmproxy.coretypes import serializable

# Default expiry must not be too long: https://github.com/mitmproxy/mitmproxy/issues/815
CA_EXPIRY = datetime.timedelta(days=3 * 365)
CERT_EXPIRY = datetime.timedelta(days=365)

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


def create_ca(
        organization: str,
        cn: str,
        key_size: int,
) -> Tuple[rsa.RSAPrivateKeyWithSerialization, x509.Certificate]:
    now = datetime.datetime.now()

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )  # type: ignore
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization)
    ])
    builder = x509.CertificateBuilder()
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.subject_name(name)
    builder = builder.not_valid_before(now - datetime.timedelta(days=2))
    builder = builder.not_valid_after(now + CA_EXPIRY)
    builder = builder.issuer_name(name)
    builder = builder.public_key(private_key.public_key())
    builder = builder.add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
    builder = builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
    builder = builder.add_extension(
        x509.KeyUsage(
            digital_signature=False,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=True,
            crl_sign=True,
            encipher_only=False,
            decipher_only=False,
        ), critical=True)
    builder = builder.add_extension(x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()), critical=False)
    cert = builder.sign(private_key=private_key, algorithm=hashes.SHA256())  # type: ignore
    return private_key, cert


def dummy_cert(
        privkey: OpenSSL.crypto.PKey,
        cacert: OpenSSL.crypto.X509,
        commonname: Optional[bytes],
        sans: List[bytes],
        organization: Optional[bytes] = None,
) -> "Cert":
    """
        Generates a dummy certificate.

        privkey: CA private key
        cacert: CA certificate
        commonname: Common name for the generated certificate.
        sans: A list of Subject Alternate Names.
        organization: Organization name for the generated certificate.

        Returns cert if operation succeeded, None if not.
    """
    XX_privkey = privkey.to_cryptography_key()
    XX_cacert: x509.Certificate = cacert.to_cryptography()
    XX_commonname: Optional[str] = commonname.decode("idna") if commonname else None
    XX_organization: Optional[str] = organization.decode() if organization else None
    XX_sans: List[str] = [x.decode("ascii") for x in sans]

    builder = x509.CertificateBuilder()
    builder = builder.issuer_name(XX_cacert.subject)
    builder = builder.add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
    builder = builder.public_key(XX_cacert.public_key())

    now = datetime.datetime.now()
    builder = builder.not_valid_before(now - datetime.timedelta(days=2))
    builder = builder.not_valid_after(now + CERT_EXPIRY)

    subject = []
    is_valid_commonname = (
            XX_commonname is not None and len(XX_commonname) < 64
    )
    if is_valid_commonname:
        assert XX_commonname is not None
        subject.append(x509.NameAttribute(NameOID.COMMON_NAME, XX_commonname))
    if XX_organization is not None:
        assert XX_organization is not None
        subject.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, XX_organization))
    builder = builder.subject_name(x509.Name(subject))
    builder = builder.serial_number(x509.random_serial_number())

    ss: List[x509.GeneralName] = []
    for x in XX_sans:
        try:
            ip = ipaddress.ip_address(x)
        except ValueError:
            ss.append(x509.DNSName(x))
        else:
            ss.append(x509.IPAddress(ip))
    # RFC 5280 §4.2.1.6: subjectAltName is critical if subject is empty.
    builder = builder.add_extension(x509.SubjectAlternativeName(ss), critical=not is_valid_commonname)
    cert = builder.sign(private_key=XX_privkey, algorithm=hashes.SHA256())  # type: ignore
    return Cert(OpenSSL.crypto.X509.from_cryptography(cert))


@dataclass
class CertStoreEntry:
    cert: OpenSSL.crypto.X509
    # cert: x509.Certificate
    privatekey: OpenSSL.crypto.PKey
    # privatekey: rsa.RSAPrivateKey
    chain_file: str


TCustomCertId = bytes  # manually provided certs (e.g. mitmproxy's --certs)
TGeneratedCertId = Tuple[Optional[bytes], Tuple[bytes, ...]]  # (common_name, sans)
TCertId = Union[TCustomCertId, TGeneratedCertId]


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
        self.certs: Dict[TCertId, CertStoreEntry] = {}
        self.expire_queue = []

    def expire(self, entry):
        self.expire_queue.append(entry)
        if len(self.expire_queue) > self.STORE_CAP:
            d = self.expire_queue.pop(0)
            self.certs = {k: v for k, v in self.certs.items() if v != d}

    @staticmethod
    def load_dhparam(path: str):

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
    def from_store(cls, path: Union[Path, str], basename: str, key_size,
                   passphrase: Optional[bytes] = None) -> "CertStore":
        path = Path(path)
        ca_file = path / f"{basename}-ca.pem"
        dhparam_file = path / f"{basename}-dhparam.pem"
        if not ca_file.exists():
            cls.create_store(path, basename, key_size)
        return cls.from_files(ca_file, dhparam_file, passphrase)

    @classmethod
    def from_files(cls, ca_file: Path, dhparam_file: Path, passphrase: Optional[bytes] = None) -> "CertStore":
        raw = ca_file.read_bytes()
        ca = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_PEM,
            raw
        )
        key = OpenSSL.crypto.load_privatekey(
            OpenSSL.crypto.FILETYPE_PEM,
            raw,
            passphrase
        )
        dh = cls.load_dhparam(str(dhparam_file))
        return cls(key, ca, str(ca_file), dh)

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
    def create_store(path: Path, basename: str, key_size: int, organization=None, cn=None) -> None:
        path.mkdir(parents=True, exist_ok=True)

        organization = organization or basename
        cn = cn or basename

        key: rsa.RSAPrivateKeyWithSerialization
        ca: x509.Certificate
        key, ca = create_ca(organization=organization, cn=cn, key_size=key_size)
        # Dump the CA plus private key
        with CertStore.umask_secret(), (path / f"{basename}-ca.pem").open("wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))
            f.write(ca.public_bytes(serialization.Encoding.PEM))

        # Dump the certificate in PEM format
        with (path / f"{basename}-ca-cert.pem").open("wb") as f:
            f.write(ca.public_bytes(serialization.Encoding.PEM))

        # Create a .cer file with the same contents for Android
        with (path / f"{basename}-ca-cert.cer").open("wb") as f:
            f.write(ca.public_bytes(serialization.Encoding.PEM))

        # Dump the certificate in PKCS12 format for Windows devices
        with (path / f"{basename}-ca-cert.p12").open("wb") as f:
            f.write(pkcs12.serialize_key_and_certificates(  # type: ignore
                name=basename.encode(),
                key=None,
                cert=ca,
                cas=None,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        # Dump the certificate and key in a PKCS12 format for Windows devices
        with CertStore.umask_secret(), (path / f"{basename}-ca.p12").open("wb") as f:
            f.write(pkcs12.serialize_key_and_certificates(  # type: ignore
                name=basename.encode(),
                key=key,
                cert=ca,
                cas=None,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        with (path / f"{basename}-dhparam.pem").open("wb") as f:
            f.write(DEFAULT_DHPARAM)

    def add_cert_file(self, spec: str, path: str, passphrase: Optional[bytes] = None) -> None:
        with open(path, "rb") as f:
            raw = f.read()
        cert = Cert(
            OpenSSL.crypto.load_certificate(
                OpenSSL.crypto.FILETYPE_PEM,
                raw))
        try:
            privatekey = OpenSSL.crypto.load_privatekey(
                OpenSSL.crypto.FILETYPE_PEM,
                raw,
                passphrase)
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
    def asterisk_forms(dn: bytes) -> List[bytes]:
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
            commonname: Optional[bytes],
            sans: List[bytes],
            organization: Optional[bytes] = None
    ) -> Tuple["Cert", OpenSSL.SSL.PKey, str]:
        """
            Returns an (cert, privkey, cert_chain) tuple.

            commonname: Common name for the generated certificate. Must be a
            valid, plain-ASCII, IDNA-encoded domain name.

            sans: A list of Subject Alternate Names.

            organization: Organization name for the generated certificate.
        """

        potential_keys: List[TCertId] = []
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
    sizeSpec = (
            univ.SequenceOf.sizeSpec +
            constraint.ValueSizeConstraint(1, 1024)
    )


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
    def cn(self) -> Optional[bytes]:
        c = None
        for i in self.subject:
            if i[0] == b"CN":
                c = i[1]
        return c

    @property
    def organization(self) -> Optional[bytes]:
        c = None
        for i in self.subject:
            if i[0] == b"O":
                c = i[1]
        return c

    @property
    def altnames(self) -> List[bytes]:
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
                for x in dec[0]:
                    if x[0].hasValue():
                        e = x[0].asOctets()
                        altnames.append(e)

        return altnames
