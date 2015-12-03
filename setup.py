from setuptools import setup, find_packages
from codecs import open
import os
import sys
from libmproxy import version

# Based on https://github.com/pypa/sampleproject/blob/master/setup.py
# and https://python-packaging-user-guide.readthedocs.org/

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Core dependencies
deps = {
    "netlib>=%s, <%s" % (version.MINORVERSION, version.NEXT_MINORVERSION),
    "tornado>=4.3.0, <4.4",
    "configargparse>=0.10.0, <0.11",
    "pyperclip>=1.5.22, <1.6",
    "blinker>=1.4, <1.5",
    "pyparsing>=2.0.5, <2.1",
    "html2text==2015.11.4",
    "construct>=2.5.2, <2.6",
    "six>=1.10.0, <1.11",
    "lxml==3.4.4",  # there are no Windows wheels for 3.5!
    "Pillow>=3.0.0, <3.1",
    "watchdog>=0.8.3, <0.9",
}
# A script -> additional dependencies dict.
scripts = {
    "mitmproxy": {
        "urwid>=1.3.1, <1.4",
    },
    "mitmdump": {
        "click>=6.2, <6.3",
    },
    "mitmweb": set()
}
# Developer dependencies
dev_deps = {
    "mock>=1.0.1",
    "pytest>=2.8.0",
    "pytest-xdist>=1.13.1",
    "pytest-cov>=2.1.0",
    "coveralls>=0.4.1",
    "pathod>=%s, <%s" % (version.MINORVERSION, version.NEXT_MINORVERSION),
    "sphinx>=1.3.1",
    "sphinx-autobuild>=0.5.2",
    "sphinxcontrib-documentedlist>=0.2",
}
example_deps = {
    "pytz==2015.7",
    "harparser>=0.2, <0.3",
    "beautifulsoup4>=4.4.1, <4.5",
}
# Add *all* script dependencies to developer dependencies.
for script_deps in scripts.values():
    dev_deps.update(script_deps)

# Remove mitmproxy for Windows support.
if os.name == "nt":
    del scripts["mitmproxy"]
    deps.add("pydivert>=0.0.7")  # Transparent proxying on Windows

# Add dependencies for available scripts as core dependencies.
for script_deps in scripts.values():
    deps.update(script_deps)

if sys.version_info < (3, 4):
    example_deps.add("enum34>=1.0.4, <1.1")

console_scripts = ["%s = libmproxy.main:%s" % (s, s) for s in scripts.keys()]

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
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Security",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: Proxy Servers",
        "Topic :: Software Development :: Testing"
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': console_scripts},
    install_requires=list(deps),
    extras_require={
        'dev': list(dev_deps),
        'contentviews': [
            "pyamf>=0.7.2, <0.8",
            "protobuf>=2.6.1, <2.7",
            "cssutils>=1.0.1, <1.1"
        ],
        'examples': list(example_deps)
    }
)
