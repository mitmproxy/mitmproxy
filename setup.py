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
    VERSION = re.search(r'VERSION = "(.+?)"', f.read()).group(1)

setup(
    name="mitmproxy",
    version=VERSION,
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
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Security",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: Proxy Servers",
        "Topic :: Software Development :: Testing"
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
        "brotlipy>=0.7.0,<0.8",
        "certifi>=2015.11.20.1",  # no semver here - this should always be on the last release!
        "click>=7.0,<7.1",
        "cryptography>=2.1.4,<2.4",
        "h2>=3.0.1,<4",
        "hyperframe>=5.1.0,<6",
        "kaitaistruct>=0.7,<0.9",
        "ldap3>=2.5,<2.6",
        "passlib>=1.6.5, <1.8",
        "protobuf>=3.6.0, <3.7",
        "pyasn1>=0.3.1,<0.5",
        "pyOpenSSL>=17.5,<18.1",
        "pyparsing>=2.3,<2.4",
        "pyperclip>=1.7,<1.8",
        "ruamel.yaml>=0.15,<0.16",
        "sortedcontainers>=1.5.4,<2.1",
        "tornado>=4.3,<5.2",
        "urwid>=2.0.1,<2.1",
        "wsproto>=0.12.0,<0.13.0",
    ],
    extras_require={
        ':sys_platform == "win32"': [
            "pydivert>=2.0.3,<2.2",
        ],
        'dev': [
            "asynctest>=0.12.0",
            "flake8>=3.6,<3.7",
            "Flask>=1.0,<1.1",
            "mypy>=0.641,<0.642",
            "parver>=0.1,<2.0",
            "pytest-asyncio>=0.8",
            "pytest-cov>=2.5.1,<3",
            "pytest-faulthandler>=1.3.1,<2",
            "pytest-timeout>=1.2.1,<2",
            "pytest-xdist>=1.22,<2",
            "pytest>=3.3,<4",
            "requests>=2.9.1, <3",
            "tox>=3.5,<3.6",
            "rstcheck>=2.2, <4.0",
        ],
        'examples': [
            "beautifulsoup4>=4.4.1, <4.7"
        ]
    }
)
