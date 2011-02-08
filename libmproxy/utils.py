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
import re, os, subprocess, datetime, textwrap, errno

def format_timestamp(s):
    d = datetime.datetime.fromtimestamp(s)
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


def cleanBin(s):
    parts = []
    for i in s:
        o = ord(i)
        if o > 31 and o < 127:
            parts.append(i)
        else:
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


def isStringLike(anobj):
    try:
        # Avoid succeeding expensively if anobj is large.
        anobj[:0]+''
    except:
        return 0
    else:
        return 1


def isSequenceLike(anobj):
    """
        Is anobj a non-string sequence type (list, tuple, iterator, or
        similar)?  Crude, but mostly effective.
    """
    if not hasattr(anobj, "next"):
        if isStringLike(anobj):
            return 0
        try:
            anobj[:0]
        except:
            return 0
    return 1


def _caseless(s):
    return s.lower()


def try_del(dict, key):
    try:
        del dict[key]
    except KeyError:
        pass


class MultiDict:
    """
        Simple wrapper around a dictionary to make holding multiple objects per
        key easier.

        Note that this class assumes that keys are strings.

        Keys have no order, but the order in which values are added to a key is
        preserved.
    """
    # This ridiculous bit of subterfuge is needed to prevent the class from
    # treating this as a bound method.
    _helper = (str,)
    def __init__(self):
        self._d = dict()

    def copy(self):
        m = self.__class__()
        m._d = self._d.copy()
        return m

    def clear(self):
        return self._d.clear()

    def get(self, key, d=None):
        key = self._helper[0](key)
        return self._d.get(key, d)

    def __eq__(self, other):
        return dict(self) == dict(other)

    def __delitem__(self, key):
        self._d.__delitem__(key)

    def __getitem__(self, key):
        key = self._helper[0](key)
        return self._d.__getitem__(key)
    
    def __setitem__(self, key, value):
        if not isSequenceLike(value):
            raise ValueError, "Cannot insert non-sequence."
        key = self._helper[0](key)
        return self._d.__setitem__(key, value)

    def has_key(self, key):
        key = self._helper[0](key)
        return self._d.has_key(key)

    def keys(self):
        return self._d.keys()

    def extend(self, key, value):
        if not self.has_key(key):
            self[key] = []
        self[key].extend(value)

    def append(self, key, value):
        self.extend(key, [value])

    def itemPairs(self):
        """
            Yield all possible pairs of items.
        """
        for i in self.keys():
            for j in self[i]:
                yield (i, j)

    def get_state(self):
        return list(self.itemPairs())

    @classmethod
    def from_state(klass, state):
        md = klass()
        for i in state:
            md.append(*i)
        return md


class Headers(MultiDict):
    """
        A dictionary-like class for keeping track of HTTP headers.

        It is case insensitive, and __repr__ formats the headers correcty for
        output to the server.
    """
    _helper = (_caseless,)
    def __repr__(self):
        """
            Returns a string containing a formatted header string.
        """
        headerElements = []
        for key in sorted(self.keys()):
            for val in self[key]:
                headerElements.append(key + ": " + val)
        headerElements.append("")
        return "\r\n".join(headerElements)

    def match_re(self, expr):
        """
            Match the regular expression against each header (key, value) pair.
        """
        for k, v in self.itemPairs():
            s = "%s: %s"%(k, v)
            if re.search(expr, s):
                return True
        return False

    def read(self, fp):
        """
            Read a set of headers from a file pointer. Stop once a blank line
            is reached.
        """
        name = ''
        while 1:
            line = fp.readline()
            if not line or line == '\r\n' or line == '\n':
                break
            if line[0] in ' \t':
                # continued header
                self[name][-1] = self[name][-1] + '\r\n ' + line.strip()
            else:
                i = line.find(':')
                # We're being liberal in what we accept, here.
                if i > 0:
                    name = line[:i]
                    value = line[i+1:].strip()
                    if self.has_key(name):
                        # merge value
                        self.append(name, value)
                    else:
                        self[name] = [value]


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
data = Data(__name__)


def make_openssl_conf(path, countryName=None, stateOrProvinceName=None, localityName=None, organizationName=None, organizationalUnitName=None, commonName=None, emailAddress=None, ca=False):
    cnf = open(path, "w")
    cnf.write("[ req ]\n")
    cnf.write("prompt = no\n")
    cnf.write("distinguished_name = req_distinguished_name\n")
    if ca:
        cnf.write("x509_extensions = v3_ca # The extentions to add to the self signed cert\n")
    cnf.write("\n")
    cnf.write("[ req_distinguished_name ]\n")
    if countryName is not None:
        cnf.write("countryName                    = %s\n" % (countryName) )
        cnf.write("stateOrProvinceName            = %s\n" % (stateOrProvinceName) )
        cnf.write("localityName                   = %s\n" % (localityName) )
        cnf.write("organizationName               = %s\n" % (organizationName) )
        cnf.write("organizationalUnitName         = %s\n" % (organizationalUnitName) )
        cnf.write("commonName                     = %s\n" % (commonName) )
        cnf.write("emailAddress                   = %s\n" % (emailAddress) )
        cnf.write("\n")
    cnf.write("[ v3_ca ]\n")
    cnf.write("subjectKeyIdentifier=hash\n")
    cnf.write("authorityKeyIdentifier=keyid:always,issuer\n")
    if ca:
        cnf.write("basicConstraints = critical,CA:true\n")
        cnf.write("keyUsage = cRLSign, keyCertSign\n")
        #cnf.write("nsCertType = sslCA, emailCA\n")
    #cnf.write("subjectAltName=email:copy\n")
    #cnf.write("issuerAltName=issuer:copy\n")

def make_bogus_cert(certpath, countryName=None, stateOrProvinceName=None, localityName=None, organizationName="mitmproxy", organizationalUnitName=None, commonName="Dummy Certificate", emailAddress=None, ca=None, newca=False):
    # Generates a bogus certificate like so:
    # openssl req -config template -x509 -nodes -days 9999 -newkey rsa:1024 \
    # -keyout cert.pem -out cert.pem 

    (path, ext) = os.path.splitext(certpath)
    d = os.path.dirname(path)
    if not os.path.exists(d):
        os.makedirs(d)
    
    cnf = open(path+".cnf", "w")
    cnf.write("[ req ]\n")
    cnf.write("prompt = no\n")
    cnf.write("distinguished_name = req_distinguished_name\n")
    if newca:
        cnf.write("x509_extensions = v3_ca\n")
        cnf.write("req_extensions = v3_ca_req\n")
    else:
        cnf.write("x509_extensions = v3_cert\n")
        cnf.write("req_extensions = v3_cert_req\n")
    cnf.write("\n")
    cnf.write("[ req_distinguished_name ]\n")
    if countryName is not None:
        cnf.write("countryName                    = %s\n" % (countryName) )
    if stateOrProvinceName is not None:
        cnf.write("stateOrProvinceName            = %s\n" % (stateOrProvinceName) )
    if localityName is not None:
        cnf.write("localityName                   = %s\n" % (localityName) )
    if organizationName is not None:
        cnf.write("organizationName               = %s\n" % (organizationName) )
    if organizationalUnitName is not None:
        cnf.write("organizationalUnitName         = %s\n" % (organizationalUnitName) )
    if commonName is not None:
        cnf.write("commonName                     = %s\n" % (commonName) )
    if emailAddress is not None:
        cnf.write("emailAddress                   = %s\n" % (emailAddress) )
    cnf.write("\n")
    cnf.write("[ v3_ca ]\n")
    cnf.write("subjectKeyIdentifier=hash\n")
    cnf.write("authorityKeyIdentifier=keyid:always,issuer\n")
    cnf.write("basicConstraints = critical,CA:true\n")
    cnf.write("keyUsage = cRLSign, keyCertSign\n")
    cnf.write("nsCertType = sslCA\n")
    #cnf.write("subjectAltName=email:copy\n")
    #cnf.write("issuerAltName=issuer:copy\n")
    cnf.write("\n")
    cnf.write("[ v3_ca_req ]\n")
    cnf.write("basicConstraints = critical,CA:true\n")
    cnf.write("keyUsage = cRLSign, keyCertSign\n")
    cnf.write("nsCertType = sslCA\n")
    #cnf.write("subjectAltName=email:copy\n")
    cnf.write("\n")
    cnf.write("[ v3_cert ]\n")
    cnf.write("basicConstraints = CA:false\n")
    cnf.write("keyUsage = nonRepudiation, digitalSignature, keyEncipherment\n")
    cnf.write("nsCertType = server\n")
    cnf.write("subjectKeyIdentifier=hash\n")
    cnf.write("authorityKeyIdentifier=keyid:always,issuer\n")
    cnf.write("\n")
    cnf.write("[ v3_cert_req ]\n")
    cnf.write("basicConstraints = CA:false\n")
    cnf.write("keyUsage = nonRepudiation, digitalSignature, keyEncipherment\n")
    cnf.write("nsCertType = server\n")
    cnf.write("\n")

    cnf.close()
 
    if ca is None:
        # Create a new selfsigned certificate + key
        cmd = [
            "openssl",
            "req",
            "-new",
            "-x509",
            "-config", path+".cnf",
            "-nodes",
            "-days", "9999",
            "-out", certpath,
            "-newkey", "rsa:1024",
            "-keyout", certpath,
        ]
        #print " ".join(cmd)
        subprocess.call(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
    else:
        # Create a dummy signed certificate. Uses same key as the signing CA
        cmd = [
            "openssl",
            "req",
            "-new",
            "-config", path+".cnf",
            "-out", path+".req",
            "-key", ca,
        ]
        #print " ".join(cmd)
        subprocess.call(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
        cmd = [
            "openssl",
            "x509",
            "-req",
            "-in", path+".req",
            "-days", "9999",
            "-out", certpath,
            "-CA", ca,
            "-CAcreateserial",
            "-extfile", path+".cnf"
        ]
        if newca:
            cmd.extend([
                "-extensions", "v3_ca",
            ])
        else:
            cmd.extend([
                "-extensions", "v3_cert",
            ])
        
        #print " ".join(cmd)
        subprocess.call(
            cmd,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE
        )
    
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            raise

