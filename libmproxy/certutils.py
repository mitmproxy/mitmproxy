import subprocess, os, tempfile, ssl, hashlib, socket, re
from pyasn1.type import univ, constraint, char, namedtype, tag
from pyasn1.codec.der.decoder import decode
import OpenSSL
import utils

CERT_SLEEP_TIME = 1
CERT_EXPIRY = str(365 * 3)


def dummy_ca(path):
    """
        Creates a dummy CA, and writes it to path.

        This function also creates the necessary directories if they don't exist.

        Returns True if operation succeeded, False if not.
    """
    dirname = os.path.dirname(path)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    if path.endswith(".pem"):
        basename, _ = os.path.splitext(path)
    else:
        basename = path

    cmd = [
        "openssl",
        "req",
        "-new",
        "-x509",
        "-config", utils.pkg_data.path("resources/ca.cnf"),
        "-nodes",
        "-days", CERT_EXPIRY,
        "-out", path,
        "-newkey", "rsa:1024",
        "-keyout", path,
    ]
    ret = subprocess.call(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE
    )
    # begin nocover
    if ret:
        return False
    # end nocover

    cmd = [
        "openssl",
        "pkcs12",
        "-export",
        "-password", "pass:",
        "-nokeys",
        "-in", path,
        "-out", os.path.join(dirname, basename + "-cert.p12")
    ]
    ret = subprocess.call(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE
    )
    # begin nocover
    if ret:
        return False
    # end nocover
    cmd = [
        "openssl",
        "x509",
        "-in", path,
        "-out", os.path.join(dirname, basename + "-cert.pem")
    ]
    ret = subprocess.call(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE
    )
    # begin nocover
    if ret:
        return False
    # end nocover

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

    confpath = os.path.join(certdir, namehash + ".cnf")
    reqpath = os.path.join(certdir, namehash + ".req")

    template = open(utils.pkg_data.path("resources/cert.cnf")).read()

    ss = []
    for i, v in enumerate(sans):
        ss.append("DNS.%s = %s"%(i+1, v))
    ss = "\n".join(ss)

    f = open(confpath, "w")
    f.write(
        template%(
            dict(
                commonname=commonname,
                sans=ss,
                altnames="subjectAltName = @alt_names" if ss else ""
            )
        )
    )
    f.close()

    if ca:
        # Create a dummy signed certificate. Uses same key as the signing CA
        cmd = [
            "openssl",
            "req",
            "-new",
            "-config", confpath,
            "-out", reqpath,
            "-key", ca,
        ]
        ret = subprocess.call(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        if ret: return None
        cmd = [
            "openssl",
            "x509",
            "-req",
            "-in", reqpath,
            "-days", CERT_EXPIRY,
            "-out", certpath,
            "-CA", ca,
            "-CAcreateserial",
            "-extfile", confpath,
            "-extensions", "v3_cert_req",
        ]
        ret = subprocess.call(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        if ret: return None
    else:
        # Create a new selfsigned certificate + key
        cmd = [
            "openssl",
            "req",
            "-new",
            "-x509",
            "-config", confpath,
            "-nodes",
            "-days", CERT_EXPIRY,
            "-out", certpath,
            "-newkey", "rsa:1024",
            "-keyout", certpath,
        ]
        ret = subprocess.call(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        if ret: return None
    return certpath


def get_remote_cn(host, port):
    addr = socket.gethostbyname(host)
    s = ssl.get_server_certificate((addr, port))
    return parse_text_cert(s)


class GeneralName(univ.Choice):
    # We are only interested in dNSNames. We use a default handler to ignore
    # other types. 
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('dNSName', char.IA5String().subtype(
                implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)
            )
        ),
    )

class GeneralNames(univ.SequenceOf):
    componentType = GeneralName()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, 1024)



def parse_text_cert(txt):
    """
        Returns a (common name, [subject alternative names]) tuple.
    """
    cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, txt)
    cn = None
    for i in cert.get_subject().get_components():
        if i[0] == "CN":
            cn = i[1]
    altnames = []
    for i in range(cert.get_extension_count()):
        ext = cert.get_extension(i)
        if ext.get_short_name() == "subjectAltName":
            dec = decode(ext.get_data(), asn1Spec=GeneralNames())
            for i in dec[0]:
                altnames.append(i[0])
    return cn, altnames

