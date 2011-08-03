# Copyright (C) 2010  Aldo Cortesi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import re, os, subprocess, datetime, urlparse, string
import time, functools, cgi, textwrap
import json

CERT_SLEEP_TIME = 1
CERT_EXPIRY = str(365 * 3)

def timestamp():
    """
        Returns a serializable UTC timestamp.
    """
    return time.time()


def format_timestamp(s):
    s = time.localtime(s)
    d = datetime.datetime.fromtimestamp(time.mktime(s))
    return d.strftime("%Y-%m-%d %H:%M:%S")


def isBin(s):
    """
        Does this string have any non-ASCII characters?
    """
    for i in s:
        i = ord(i)
        if i < 9:
            return True
        elif i > 13 and i < 32:
            return True
        elif i > 126:
            return True
    return False


def isXML(s):
    for i in s:
        if i in "\n \t":
            continue
        elif i == "<":
            return True
        else:
            return False


def cleanBin(s):
    parts = []
    for i in s:
        o = ord(i)
        if o > 31 and o < 127:
            parts.append(i)
        else:
            if i not in "\n\r\t":
                parts.append(".")
    return "".join(parts)


TAG = r"""
        <\s*
        (?!\s*[!"])
        (?P<close>\s*\/)?
        (?P<name>\w+)
        (
            [^'"\t >]+ |
            "[^\"]*"['\"]* |
            '[^']*'['\"]* |
            \s+
        )*
        (?P<selfcont>\s*\/\s*)?
        \s*>
      """
UNI = set(["br", "hr", "img", "input", "area", "link"])
INDENT = " "*4
def pretty_xmlish(s):
    """
        A robust pretty-printer for XML-ish data.
        Returns a list of lines.
    """
    s = cleanBin(s)
    data, offset, indent, prev = [], 0, 0, None
    for i in re.finditer(TAG, s, re.VERBOSE|re.MULTILINE):
        start, end = i.span()
        name = i.group("name")
        if start > offset:
            txt = []
            for x in textwrap.dedent(s[offset:start]).split("\n"):
                if x.strip():
                    txt.append(indent*INDENT + x)
            data.extend(txt)
        if i.group("close") and not (name in UNI and name==prev):
            indent = max(indent - 1, 0)
        data.append(indent*INDENT + i.group().strip())
        offset = end
        if not any([i.group("close"), i.group("selfcont"), name in UNI]):
            indent += 1
        prev = name
    trail = s[offset:]
    if trail.strip():
        data.append(s[offset:])
    return data


def pretty_json(s):
    try:
        p = json.loads(s)
    except ValueError:
        return None
    return json.dumps(p, sort_keys=True, indent=4).split("\n")


def urldecode(s):
    return cgi.parse_qsl(s)


def hexdump(s):
    """
        Returns a set of typles:
            (offset, hex, str)
    """
    parts = []
    for i in range(0, len(s), 16):
        o = "%.10x"%i
        part = s[i:i+16]
        x = " ".join(["%.2x"%ord(i) for i in part])
        if len(part) < 16:
            x += " "
            x += " ".join(["  " for i in range(16-len(part))])
        parts.append(
            (o, x, cleanBin(part))
        )
    return parts


def del_all(dict, keys):
    for key in keys:
        if key in dict:
            del dict[key]



def pretty_size(size):
    suffixes = [
        ("B",   2**10),
        ("kB",   2**20),
        ("M",   2**30),
    ]
    for suf, lim in suffixes:
        if size >= lim:
            continue
        else:
            x = round(size/float(lim/2**10), 2)
            if x == int(x):
                x = int(x)
            return str(x) + suf


class Data:
    def __init__(self, name):
        m = __import__(name)
        dirname, _ = os.path.split(m.__file__)
        self.dirname = os.path.abspath(dirname)

    def path(self, path):
        """
            Returns a path to the package data housed at 'path' under this
            module.Path can be a path to a file, or to a directory.

            This function will raise ValueError if the path does not exist.
        """
        fullpath = os.path.join(self.dirname, path)
        if not os.path.exists(fullpath):
            raise ValueError, "dataPath: %s does not exist."%fullpath
        return fullpath
pkg_data = Data(__name__)


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
        "-config", pkg_data.path("resources/ca.cnf"),
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


def dummy_cert(certdir, ca, commonname):
    """
        certdir: Certificate directory.
        ca: Path to the certificate authority file, or None.
        commonname: Common name for the generated certificate.

        Returns cert path if operation succeeded, None if not.
    """
    certpath = os.path.join(certdir, commonname + ".pem")
    if os.path.exists(certpath):
        return certpath

    confpath = os.path.join(certdir, commonname + ".cnf")
    reqpath = os.path.join(certdir, commonname + ".req")

    template = open(pkg_data.path("resources/cert.cnf")).read()
    f = open(confpath, "w")
    f.write(template%(dict(commonname=commonname)))
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
            "-extensions", "v3_cert",
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


class LRUCache:
    """
        A decorator that implements a self-expiring LRU cache for class
        methods (not functions!).

        Cache data is tracked as attributes on the object itself. There is
        therefore a separate cache for each object instance.
    """
    def __init__(self, size=100):
        self.size = size

    def __call__(self, f):
        cacheName = "_cached_%s"%f.__name__
        cacheListName = "_cachelist_%s"%f.__name__
        size = self.size

        @functools.wraps(f)
        def wrap(self, *args):
            if not hasattr(self, cacheName):
                setattr(self, cacheName, {})
                setattr(self, cacheListName, [])
            cache = getattr(self, cacheName)
            cacheList = getattr(self, cacheListName)
            if cache.has_key(args):
                cacheList.remove(args)
                cacheList.insert(0, args)
                return cache[args]
            else:
                ret = f(self, *args)
                cacheList.insert(0, args)
                cache[args] = ret
                if len(cacheList) > size:
                    d = cacheList.pop()
                    cache.pop(d)
                return ret
        return wrap


def parse_url(url):
    """
        Returns a (scheme, host, port, path) tuple, or None on error.
    """
    scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
    if not scheme:
        return None
    if ':' in netloc:
        host, port = string.split(netloc, ':')
        port = int(port)
    else:
        host = netloc
        if scheme == "https":
            port = 443
        else:
            port = 80
    path = urlparse.urlunparse(('', '', path, params, query, fragment))
    if not path.startswith("/"):
        path = "/" + path
    return scheme, host, port, path


