import os
from codecs import open

import re
from setuptools import setup, find_packages

# Based on https://github.com/pypa/sampleproject/blob/master/setup.py
# and https://python-packaging-user-guide.readthedocs.org/

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

with open(os.path.join(here, "mitmproxy", "version.py")) as f:
    match = re.search(r'VERSION = "(.+?)"', f.read())
    assert match
    VERSION = match.group(1)

setup(
    name="mitmproxy",
    version=VERSION,
    description="An interactive, SSL/TLS-capable intercepting proxy for HTTP/1, HTTP/2, and WebSockets.",
    long_description=long_description,
    url="http://mitmproxy.org",
    author="Aldo Cortesi",
    author_email="aldo@corte.si",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console :: Curses",
        "Operating System :: MacOS",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Security",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: Proxy Servers",
        "Topic :: System :: Networking :: Monitoring",
        "Topic :: Software Development :: Testing",
        "Typing :: Typed",
    ],
    packages=find_packages(include=[
        "mitmproxy", "mitmproxy.*",
        "pathod", "pathod.*",
    ]),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            "mitmproxy = mitmproxy.tools.main:mitmproxy",
            "mitmdump = mitmproxy.tools.main:mitmdump",
            "mitmweb = mitmproxy.tools.main:mitmweb",
            "pathod = pathod.pathod_cmdline:go_pathod",
            "pathoc = pathod.pathoc_cmdline:go_pathoc"
        ]
    },
    # https://packaging.python.org/en/latest/requirements/#install-requires
    # It is not considered best practice to use install_requires to pin dependencies to specific versions.
    install_requires=[
        "blinker>=1.4, <1.5",
        "Brotli>=1.0,<1.1",
        "certifi>=2019.9.11",  # no semver here - this should always be on the last release!
        "click>=7.0,<8",
        "cryptography>=2.9,<3.0",
        "flask>=1.1.1,<1.2",
        "h2>=3.2.0,<4",
        "hyperframe>=5.1.0,<6",
        "kaitaistruct>=0.7,<0.9",
        "ldap3>=2.6.1,<2.8",
        "msgpack>=1.0.0, <1.1.0",
        "native-web-app>=1.0.0, <1.1.0",
        "passlib>=1.6.5, <1.8",
        "protobuf>=3.6.0, <3.12",
        "pyasn1>=0.3.1,<0.5",
        "pyOpenSSL>=19.1.0,<19.2",
        "pyparsing>=2.4.2,<2.5",
        "pyperclip>=1.6.0,<1.9",
        "ruamel.yaml>=0.16,<0.17",
        "sortedcontainers>=2.1.0,<2.2",
        "tornado>=4.3,<7",
        "urwid>=2.1.1,<2.2",
        "wsproto>=0.14,<0.16",
        "publicsuffix2>=2.20190812,<3",
        "zstandard>=0.11,<0.14",
    ],
    extras_require={
        ':sys_platform == "win32"': [
            "pydivert>=2.0.3,<2.2",
        ],
        ':python_version == "3.6"': [
            "dataclasses>=0.7",
        ],
        'dev': [
            "asynctest>=0.12.0",
            "Flask>=1.0,<1.2",
            "hypothesis>=5.8,<5.9",
            "parver>=0.1,<2.0",
            "pytest-asyncio>=0.10.0,<0.11",
            "pytest-cov>=2.7.1,<3",
            "pytest-timeout>=1.3.3,<2",
            "pytest-xdist>=1.29,<2",
            "pytest>=5.1.3,<6",
            "requests>=2.9.1,<3",
            "tox>=3.5,<3.15",
        ]
    }
)
