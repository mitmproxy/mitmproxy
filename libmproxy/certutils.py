import os, ssl, hashlib, socket, time, datetime
from pyasn1.type import univ, constraint, char, namedtype, tag
from pyasn1.codec.der.decoder import decode
import OpenSSL

CERT_SLEEP_TIME = 1
CERT_EXPIRY = str(365 * 3)


def create_ca():
    key = OpenSSL.crypto.PKey()
    key.generate_key(OpenSSL.crypto.TYPE_RSA, 1024)
    ca = OpenSSL.crypto.X509()
    ca.set_serial_number(int(time.time()*10000))
    ca.set_version(2)
    ca.get_subject().CN = "mitmproxy"
    ca.get_subject().O = "mitmproxy"
    ca.gmtime_adj_notBefore(0)
    ca.gmtime_adj_notAfter(24 * 60 * 60 * 720)
    ca.set_issuer(ca.get_subject())
    ca.set_pubkey(key)
    ca.add_extensions([
      OpenSSL.crypto.X509Extension("basicConstraints", True,
                                   "CA:TRUE"),
      OpenSSL.crypto.X509Extension("nsCertType", True,
                                   "sslCA"),
      OpenSSL.crypto.X509Extension("extendedKeyUsage", True,
                                    "serverAuth,clientAuth,emailProtection,timeStamping,msCodeInd,msCodeCom,msCTLSign,msSGC,msEFS,nsSGC"
                                    ),
      OpenSSL.crypto.X509Extension("keyUsage", False,
                                   "keyCertSign, cRLSign"),
      OpenSSL.crypto.X509Extension("subjectKeyIdentifier", False, "hash",
                                   subject=ca),
      ])
    ca.sign(key, "sha1")
    return key, ca


def dummy_ca(path):
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    if path.endswith(".pem"):
        basename, _ = os.path.splitext(path)
    else:
        basename = path

    key, ca = create_ca()

    # Dump the CA plus private key
    f = open(path, "w")
    f.write(OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM, key))
    f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca))
    f.close()

    # Dump the certificate in PEM format
    f = open(os.path.join(dirname, basename + "-cert.pem"), "w")
    f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca))
    f.close()

    # Create a .cer file with the same contents for Android
    f = open(os.path.join(dirname, basename + "-cert.cer"), "w")
    f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, ca))
    f.close()

    # Dump the certificate in PKCS12 format for Windows devices
    f = open(os.path.join(dirname, basename + "-cert.p12"), "w")
    p12 = OpenSSL.crypto.PKCS12()
    p12.set_certificate(ca)
    f.write(p12.export())
    f.close()
    return True


def dummy_cert(certdir, ca, commonname, sans):
    """
        certdir: Certificate directory.
        ca: Path to the certificate authority file, or None.
        commonname: Common name for the generated certificate.

        Returns cert path if operation succeeded, None if not.
    """
    namehash = hashlib.sha256(commonname).hexdigest()
    certpath = os.path.join(certdir, namehash + ".pem")
    if os.path.exists(certpath):
        return certpath

    ss = []
    for i in sans:
        ss.append("DNS: %s"%i)
    ss = ", ".join(ss)

    if ca:
        raw = file(ca, "r").read()
        ca = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, raw)
        key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, raw)
    else:
        key, ca = create_ca()

    req = OpenSSL.crypto.X509Req()
    subj = req.get_subject()
    subj.CN = commonname
    req.set_pubkey(ca.get_pubkey())
    req.sign(key, "sha1")
    if ss:
        req.add_extensions([OpenSSL.crypto.X509Extension("subjectAltName", True, ss)])

    cert = OpenSSL.crypto.X509()
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(60 * 60 * 24 * 30)
    cert.set_issuer(ca.get_subject())
    cert.set_subject(req.get_subject())
    cert.set_serial_number(int(time.time()*10000))
    if ss:
        cert.add_extensions([OpenSSL.crypto.X509Extension("subjectAltName", True, ss)])
    cert.set_pubkey(req.get_pubkey())
    cert.sign(key, "sha1")

    f = open(certpath, "w")
    f.write(OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_PEM, cert))
    f.close()

    return certpath


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
    def __init__(self, pemtxt):
        """
            Returns a (common name, [subject alternative names]) tuple.
        """
        self.cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, pemtxt)

    @classmethod
    def from_der(klass, der):
        pem = ssl.DER_cert_to_PEM_cert(der)
        return klass(pem)

    def digest(self, name):
        return self.cert.digest(name)

    @property
    def issuer(self):
        return self.cert.get_issuer().get_components()

    @property
    def notbefore(self):
        t = self.cert.get_notBefore()
        return datetime.datetime.strptime(t, "%Y%m%d%H%M%SZ")

    @property
    def notafter(self):
        t = self.cert.get_notAfter()
        return datetime.datetime.strptime(t, "%Y%m%d%H%M%SZ")

    @property
    def has_expired(self):
        return self.cert.has_expired()

    @property
    def subject(self):
        return self.cert.get_subject().get_components()

    @property
    def serial(self):
        return self.cert.get_serial_number()

    @property
    def keyinfo(self):
        pk = self.cert.get_pubkey()
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
        cn = None
        for i in self.subject:
            if i[0] == "CN":
                cn = i[1]
        return cn

    @property
    def altnames(self):
        altnames = []
        for i in range(self.cert.get_extension_count()):
            ext = self.cert.get_extension(i)
            if ext.get_short_name() == "subjectAltName":
                dec = decode(ext.get_data(), asn1Spec=_GeneralNames())
                for i in dec[0]:
                    altnames.append(i[0].asOctets())
        return altnames


# begin nocover
def get_remote_cert(host, port):
    addr = socket.gethostbyname(host)
    s = ssl.get_server_certificate((addr, port))
    return SSLCert(s)
# end nocover

