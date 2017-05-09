import os
import runpy
from codecs import open

from setuptools import setup, find_packages

# Based on https://github.com/pypa/sampleproject/blob/master/setup.py
# and https://python-packaging-user-guide.readthedocs.org/

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

VERSION = runpy.run_path(os.path.join(here, "mitmproxy", "version.py"))["VERSION"]

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
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
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
        "click>=6.2, <7",
        "certifi>=2015.11.20.1",  # no semver here - this should always be on the last release!
        "construct>=2.8, <2.9",
        "cryptography>=1.4, <1.9",
        "cssutils>=1.0.1, <1.1",
        "h2>=3.0, <4",
        "html2text>=2016.1.8, <=2016.9.19",
        "hyperframe>=5.0, <6",
        "jsbeautifier>=1.6.3, <1.7",
        "kaitaistruct>=0.7, <0.8",
        "ldap3>=2.2.0, <2.3",
        "passlib>=1.6.5, <1.8",
        "pyasn1>=0.1.9, <0.3",
        "pyOpenSSL>=16.0, <17.1",
        "pyparsing>=2.1.3, <2.3",
        "pyperclip>=1.5.22, <1.6",
        "requests>=2.9.1, <3",
        "ruamel.yaml>=0.13.2, <0.15",
        "tornado>=4.3, <4.6",
        "urwid>=1.3.1, <1.4",
        "brotlipy>=0.5.1, <0.7",
        "sortedcontainers>=1.5.4, <1.6",
        # transitive from cryptography, we just blacklist here.
        # https://github.com/pypa/setuptools/issues/861
        "setuptools>=11.3, !=29.0.0",
    ],
    extras_require={
        ':sys_platform == "win32"': [
            "pydivert>=2.0.3, <2.1",
        ],
        ':sys_platform != "win32"': [
        ],
        'dev': [
            "Flask>=0.10.1, <0.13",
            "flake8>=3.2.1, <3.4",
            "mypy>=0.510, <0.511",
            "rstcheck>=2.2, <4.0",
            "tox>=2.3, <3",
            "pytest>=3, <3.1",
            "pytest-cov>=2.2.1, <3",
            "pytest-timeout>=1.0.0, <2",
            "pytest-xdist>=1.14, <2",
            "pytest-faulthandler>=1.3.0, <2",
            "sphinx>=1.3.5, <1.6",
            "sphinx-autobuild>=0.5.2, <0.7",
            "sphinxcontrib-documentedlist>=0.5.0, <0.7",
            "sphinx_rtd_theme>=0.1.9, <0.3",
        ],
        'contentviews': [
        ],
        'examples': [
            "beautifulsoup4>=4.4.1, <4.7",
            "Pillow>=3.2, <4.2",
        ]
    }
)
