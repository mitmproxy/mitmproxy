from setuptools import setup, find_packages
from codecs import open
import os

from netlib import version

# Based on https://github.com/pypa/sampleproject/blob/master/setup.py
# and https://python-packaging-user-guide.readthedocs.org/
# and https://caremad.io/2014/11/distributing-a-cffi-project/

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.mkd'), encoding='utf-8') as f:
    long_description = f.read()

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
    install_requires=[
        "pyasn1>=0.1.7",
        "pyOpenSSL>=0.15.1",
        "cryptography>=1.0",
        "passlib>=1.6.2",
        "hpack>=1.0.1",
        "six>=1.9.0",
        "certifi"
    ],
    extras_require={
        'dev': [
            "mock>=1.0.1",
            "nose>=1.3.0",
            "nose-cov>=1.6",
            "coveralls>=0.4.1",
            "autopep8>=1.0.3",
            "autoflake>=0.6.6",
            "wheel>=0.24.0",
            "pathod>=%s, <%s" %
            (version.MINORVERSION,
             version.NEXT_MINORVERSION)
        ]
    },
)
