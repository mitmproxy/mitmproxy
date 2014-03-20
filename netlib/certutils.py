import os, ssl, time, datetime
from pyasn1.type import univ, constraint, char, namedtype, tag
from pyasn1.codec.der.decoder import decode
from pyasn1.error import PyAsn1Error
import OpenSSL
import tcp
import UserDict

DEFAULT_EXP = 62208000 # =24 * 60 * 60 * 720
# Generated with "openssl dhparam". It's too slow to generate this on startup.
DEFAULT_DHPARAM = """-----BEGIN DH PARAMETERS-----
MIGHAoGBAOdPzMbYgoYfO3YBYauCLRlE8X1XypTiAjoeCFD0qWRx8YUsZ6Sj20W5
zsfQxlZfKovo3f2MftjkDkbI/C/tDgxoe0ZPbjy5CjdOhkzxn0oTbKTs16Rw8DyK
1LjTR65sQJkJEdgsX8TSi/cicCftJZl9CaZEaObF2bdgSgGK+PezAgEC
-----END DH PARAMETERS-----"""

def create_ca(o, cn, exp):
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 1024)
    cert = OpenSSL.crypto.X509()
    cert.set_serial_number(int(time.time()*10000))
    cert.set_version(2)
    cert.get_subject().CN = cn
    cert.get_subject().O = o
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(exp)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(key)
    cert.add_extensions([
      OpenSSL.crypto.X509Extension("basicConstraints", True,
                                   "CA:TRUE"),
      OpenSSL.crypto.X509Extension("nsCertType", False,
                                   "sslCA"),
      OpenSSL.crypto.X509Extension("extendedKeyUsage", False,
                                    "serverAuth,clientAuth,emailProtection,timeStamping,msCodeInd,msCodeCom,msCTLSign,msSGC,msEFS,nsSGC"
                                    ),
      OpenSSL.crypto.X509Extension("keyUsage", True,
                                   "keyCertSign, cRLSign"),
      OpenSSL.crypto.X509Extension("subjectKeyIdentifier", False, "hash",
                                   subject=cert),
      ])
    cert.sign(key, "sha1")
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
        ss.append("DNS: %s"%i)
    ss = ", ".join(ss)

    cert = OpenSSL.crypto.X509()
    cert.gmtime_adj_notBefore(-3600*48)
    cert.gmtime_adj_notAfter(60 * 60 * 24 * 30)
    cert.set_issuer(cacert.get_subject())
    cert.get_subject().CN = commonname
    cert.set_serial_number(int(time.time()*10000))
    if ss:
        cert.set_version(2)
        cert.add_extensions([OpenSSL.crypto.X509Extension("subjectAltName", False, ss)])
    cert.set_pubkey(cacert.get_pubkey())
    cert.sign(privkey, "sha1")
    return SSLCert(cert)


class _Node(UserDict.UserDict):
    def __init__(self):
        UserDict.UserDict.__init__(self)
        self.value = None


class DNTree:
    """
        Domain store that knows about wildcards. DNS wildcards are very
        restricted - the only valid variety is an asterisk on the left-most
        domain component, i.e.:

            *.foo.com
    """
    def __init__(self):
        self.d = _Node()

    def add(self, dn, cert):
        parts = dn.split(".")
        parts.reverse()
        current = self.d
        for i in parts:
            current = current.setdefault(i, _Node())
        current.value = cert

    def get(self, dn):
        parts = dn.split(".")
        current = self.d
        for i in reversed(parts):
            if i in current:
                current = current[i]
            elif "*" in current:
                return current["*"].value
            else:
                return None
        return current.value



class CertStore:
    """
        Implements an in-memory certificate store.
    """
    def __init__(self, privkey, cacert, dhparams=None):
        self.privkey, self.cacert = privkey, cacert
        self.dhparams = dhparams
        self.certs = DNTree()

    @classmethod
    def load_dhparam(klass, path):

        # netlib<=0.10 doesn't generate a dhparam file.
        # Create it now if neccessary.
        if not os.path.exists(path):
            with open(path, "wb") as f:
                f.write(DEFAULT_DHPARAM)

        bio = OpenSSL.SSL._lib.BIO_new_file(path, b"r")
        if bio != OpenSSL.SSL._ffi.NULL:
            bio = OpenSSL.SSL._ffi.gc(bio, OpenSSL.SSL._lib.BIO_free)
            dh = OpenSSL.SSL._lib.PEM_read_bio_DHparams(
                    bio, OpenSSL.SSL._ffi.NULL, OpenSSL.SSL._ffi.NULL, OpenSSL.SSL._ffi.NULL
                )
            dh = OpenSSL.SSL._ffi.gc(dh, OpenSSL.SSL._lib.DH_free)
            return dh
    
    @classmethod
    def from_store(klass, path, basename):
        p = os.path.join(path, basename + "-ca.pem")
        if not os.path.exists(p):
            key, ca = klass.create_store(path, basename)
        else:
            p = os.path.join(path, basename + "-ca.pem")
            raw = file(p, "rb").read()
            ca = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, raw)
            key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, raw)
        dhp = os.path.join(path, basename + "-dhparam.pem")
        dh = klass.load_dhparam(dhp)
        return klass(key, ca, dh)

    @classmethod
    def create_store(klass, path, basename, o=None, cn=None, expiry=DEFAULT_EXP):
        if not os.path.exists(path):
            os.makedirs(path)

        o = o or basename
        cn = cn or basename

        key, ca = create_ca(o=o, cn=cn, exp=expiry)
        # Dump the CA plus private key
        f = open(os.path.join(path, basename + "-ca.pem"), "wb")
        f.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key))
        f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca))
        f.close()

        # Dump the certificate in PEM format
        f = open(os.path.join(path, basename + "-ca-cert.pem"), "wb")
        f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca))
        f.close()

        # Create a .cer file with the same contents for Android
        f = open(os.path.join(path, basename + "-ca-cert.cer"), "wb")
        f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca))
        f.close()

        # Dump the certificate in PKCS12 format for Windows devices
        f = open(os.path.join(path, basename + "-ca-cert.p12"), "wb")
        p12 = OpenSSL.crypto.PKCS12()
        p12.set_certificate(ca)
        p12.set_privatekey(key)
        f.write(p12.export())
        f.close()

        f = open(os.path.join(path, basename + "-dhparam.pem"), "wb")
        f.write(DEFAULT_DHPARAM)
        f.close()
        return key, ca

    def add_cert_file(self, spec, path):
        raw = file(path, "rb").read()
        cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, raw)
        try:
            privkey = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, raw)
        except Exception:
            privkey = None
        self.add_cert(SSLCert(cert), privkey, spec)

    def add_cert(self, cert, privkey, *names):
        """
            Adds a cert to the certstore. We register the CN in the cert plus
            any SANs, and also the list of names provided as an argument.
        """
        if cert.cn:
            self.certs.add(cert.cn, (cert, privkey))
        for i in cert.altnames:
            self.certs.add(i, (cert, privkey))
        for i in names:
            self.certs.add(i, (cert, privkey))

    def get_cert(self, commonname, sans):
        """
            Returns an (cert, privkey) tuple.

            commonname: Common name for the generated certificate. Must be a
            valid, plain-ASCII, IDNA-encoded domain name.

            sans: A list of Subject Alternate Names.

            Return None if the certificate could not be found or generated.
        """
        c = self.certs.get(commonname)
        if not c:
            c = dummy_cert(self.privkey, self.cacert, commonname, sans)
            self.add_cert(c, None)
            c = (c, None)
        return (c[0], c[1] or self.privkey)

    def gen_pkey(self, cert):
        import certffi
        certffi.set_flags(self.privkey, 1)
        return self.privkey


class _GeneralName(univ.Choice):
    # We are only interested in dNSNames. We use a default handler to ignore
    # other types.
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('dNSName', char.IA5String().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)
            )
        ),
    )


class _GeneralNames(univ.SequenceOf):
    componentType = _GeneralName()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, 1024)


class SSLCert:
    def __init__(self, cert):
        """
            Returns a (common name, [subject alternative names]) tuple.
        """
        self.x509 = cert

    def __eq__(self, other):
        return self.digest("sha1") == other.digest("sha1")

    @classmethod
    def from_pem(klass, txt):
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, txt)
        return klass(x509)

    @classmethod
    def from_der(klass, der):
        pem = ssl.DER_cert_to_PEM_cert(der)
        return klass.from_pem(pem)

    def to_pem(self):
        return OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, self.x509)

    def digest(self, name):
        return self.x509.digest(name)

    @property
    def issuer(self):
        return self.x509.get_issuer().get_components()

    @property
    def notbefore(self):
        t = self.x509.get_notBefore()
        return datetime.datetime.strptime(t, "%Y%m%d%H%M%SZ")

    @property
    def notafter(self):
        t = self.x509.get_notAfter()
        return datetime.datetime.strptime(t, "%Y%m%d%H%M%SZ")

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
            if i[0] == "CN":
                c = i[1]
        return c

    @property
    def altnames(self):
        altnames = []
        for i in range(self.x509.get_extension_count()):
            ext = self.x509.get_extension(i)
            if ext.get_short_name() == "subjectAltName":
                try:
                    dec = decode(ext.get_data(), asn1Spec=_GeneralNames())
                except PyAsn1Error:
                    continue
                for i in dec[0]:
                    altnames.append(i[0].asOctets())
        return altnames



def get_remote_cert(host, port, sni):
    c = tcp.TCPClient((host, port))
    c.connect()
    c.convert_to_ssl(sni=sni)
    return c.cert
