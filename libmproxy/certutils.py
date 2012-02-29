import subprocess, os, tempfile, ssl, hashlib, socket, re
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
    f = tempfile.NamedTemporaryFile()
    f.write(s)
    f.flush()
    p = subprocess.Popen(
        [
            "openssl",
            "x509",
            "-in", f.name,
            "-text",
            "-noout"
        ],
        stdout = subprocess.PIPE
    )
    out, _ = p.communicate()
    return parse_text_cert(out)


CNRE = re.compile(
    r"""
        Subject:.*CN=([^ \t\n\r\f\v/]*)
    """,
    re.VERBOSE|re.MULTILINE
)
SANRE = re.compile(
    r"""
        X509v3\ Subject\ Alternative\ Name:\s*
        (.*)$
    """,
    re.VERBOSE|re.MULTILINE
)
def parse_text_cert(txt):
    """
        Returns a (common name, [subject alternative names]) tuple.
    """
    r = re.search(CNRE, txt)
    if r:
        cn = r.group(1)
    else:
        return None

    r = re.search(SANRE, txt)
    san = []
    if r:
        for i in r.group(1).split(","):
            i = i.strip()
            k, v = i.split(":")
            if k == "DNS":
                san.append(v)
    else:
        san = []
    return (cn, san)
