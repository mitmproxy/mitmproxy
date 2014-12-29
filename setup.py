from setuptools import setup, find_packages
from codecs import open
import os
from libmproxy import version

# Based on https://github.com/pypa/sampleproject/blob/master/setup.py
# and https://python-packaging-user-guide.readthedocs.org/

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

scripts = ["mitmdump"]
if os.name != "nt":
    scripts.append("mitmproxy")

deps = {
    "netlib>=%s, <%s" % (version.MINORVERSION, version.NEXT_MINORVERSION),
    "pyasn1>0.1.2",
    "pyOpenSSL>=0.14",
    "tornado>=4.0.2",
    "configargparse>=0.9.3"
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


setup(
    name="mitmproxy",
    version=version.VERSION,
    description="An interactive, SSL-capable, man-in-the-middle HTTP proxy for penetration testers and software developers.",
    long_description=long_description,
    url="http://mitmproxy.org",
    author="Aldo Cortesi",
    author_email="aldo@corte.si",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Environment :: Console :: Curses",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Topic :: Security",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: Proxy Servers",
        "Topic :: Software Development :: Testing"
    ],
    packages=find_packages(),
    include_package_data=True,
    scripts = scripts,
    install_requires=list(deps),
    extras_require={
        'dev': [
            "mock>=1.0.1",
            "nose>=1.3.0",
            "nose-cov>=1.6",
            "coveralls>=0.4.1",
            "pathod>=%s, <%s" % (
                version.MINORVERSION, version.NEXT_MINORVERSION
            )
        ],
        'contentviews': [
            "pyamf>=0.6.1",
            "protobuf>=2.5.0",
            "cssutils>=1.0"
        ],
        'examples': [
            "pytz",
            "harparser",
            "beautifulsoup4"
        ]
    }
)
