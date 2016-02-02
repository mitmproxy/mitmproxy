from setuptools import setup, find_packages
from codecs import open
import os
import sys

from netlib import version

# Based on https://github.com/pypa/sampleproject/blob/master/setup.py
# and https://python-packaging-user-guide.readthedocs.org/
# and https://caremad.io/2014/11/distributing-a-cffi-project/

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

deps = {
    "pyasn1>=0.1.9, <0.2",
    "pyOpenSSL>=0.15.1, <0.16",
    "cryptography>=1.2.2, <1.3",
    "passlib>=1.6.5, <1.7",
    "hpack>=2.1.0, <3.0",
    "hyperframe>=3.2.0, <4.0",
    "six>=1.10.0, <1.11",
    "certifi>=2015.11.20.1",  # no semver here - this should always be on the last release!
    "backports.ssl_match_hostname>=3.5.0.1, <3.6",
}
if sys.version_info < (3, 0):
    deps.add("ipaddress>=1.0.15, <1.1")

setup(
    name="netlib",
    version=version.VERSION,
    description="A collection of network utilities used by pathod and mitmproxy.",
    long_description=long_description,
    url="http://github.com/mitmproxy/netlib",
    author="Aldo Cortesi",
    author_email="aldo@corte.si",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 3 - Alpha",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Testing :: Traffic Generation",
    ],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=list(deps),
    extras_require={
        'dev': [
            "mock>=1.0.1",
            "pytest>=2.8.0",
            "pytest-xdist>=1.13.1",
            "pytest-cov>=2.1.0",
            "pytest-timeout>=1.0.0",
            "coveralls>=0.4.1",
            "autopep8>=1.0.3",
            "autoflake>=0.6.6",
            "wheel>=0.24.0",
        ]
    },
)
