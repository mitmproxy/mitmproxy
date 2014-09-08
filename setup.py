from distutils.core import setup
import fnmatch, os.path
from libmproxy import version


def pdir():
    dirname, _ = os.path.split(__file__)
    return os.path.abspath(dirname)


def _fnmatch(name, patternList):
    for i in patternList:
        if fnmatch.fnmatch(name, i):
            return True
    return False


def _splitAll(path):
    parts = []
    h = path
    while 1:
        if not h:
            break
        h, t = os.path.split(h)
        parts.append(t)
    parts.reverse()
    return parts


def findPackages(path, dataExclude=[]):
    """
        Recursively find all packages and data directories rooted at path. Note
        that only data _directories_ and their contents are returned -
        non-Python files at module scope are not, and should be manually
        included.

        dataExclude is a list of fnmatch-compatible expressions for files and
        directories that should not be included in pakcage_data.

        Returns a (packages, package_data) tuple, ready to be passed to the
        corresponding distutils.core.setup arguments.
    """
    packages = []
    datadirs = []
    for root, dirs, files in os.walk(path, topdown=True):
        if "__init__.py" in files:
            p = _splitAll(root)
            packages.append(".".join(p))
        else:
            dirs[:] = []
            if packages:
                datadirs.append(root)

    # Now we recurse into the data directories
    package_data = {}
    for i in datadirs:
        if not _fnmatch(i, dataExclude):
            parts = _splitAll(i)
            module = ".".join(parts[:-1])
            acc = package_data.get(module, [])
            for root, dirs, files in os.walk(i, topdown=True):
                sub = os.path.join(*_splitAll(root)[1:])
                if not _fnmatch(sub, dataExclude):
                    for fname in files:
                        path = os.path.join(sub, fname)
                        if not _fnmatch(path, dataExclude):
                            acc.append(path)
                else:
                    dirs[:] = []
            package_data[module] = acc
    return packages, package_data


with open(os.path.join(pdir(), "README.txt")) as f:
    long_description = f.read()
packages, package_data = findPackages("libmproxy")


scripts = ["mitmdump"]
if os.name != "nt":
    scripts.append("mitmproxy")

deps = {
    "netlib>=%s" % version.MINORVERSION,
    "pyasn1>0.1.2",
    "requests>=2.4.0",
    "pyOpenSSL>=0.14",
    "Flask>=0.10.1"
}
script_deps = {
    "mitmproxy": {
        "urwid>=1.1",
        "lxml>=3.3.6",
        "Pillow>=2.3.0",
    },
    "mitmdump": set()
}
for script in scripts:
    deps.update(script_deps[script])
if os.name == "nt":
    deps.add("pydivert>=0.0.4")  # Transparent proxying on Windows
console_scripts = ["%s = libmproxy.main:%s" % (s, s) for s in scripts]



setup(
    name="mitmproxy",
    version=version.VERSION,
    description="An interactive, SSL-capable, man-in-the-middle HTTP proxy for penetration testers and software developers.",
    long_description=long_description,
    author="Aldo Cortesi",
    author_email="aldo@corte.si",
    url="http://mitmproxy.org",
    packages=packages,
    package_data=package_data,
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Console :: Curses",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Topic :: Security",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: Proxy Servers",
        "Topic :: Software Development :: Testing"
    ],
    entry_points={
        'console_scripts': console_scripts
    },
    install_requires=list(deps),
    extras_require={
        'dev': [
            "mock>=1.0.1",
            "nose>=1.3.0",
            "nose-cov>=1.6",
            "coveralls>=0.4.1",
            "pathod>=%s" % version.MINORVERSION
        ],
        'contentviews': [
            "pyamf>=0.6.1",
            "protobuf>=2.5.0",
            "cssutils>=1.0"
        ]
    }
)
