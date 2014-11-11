from setuptools import setup, find_packages
from codecs import open
import os
from netlib import version

# Based on https://github.com/pypa/sampleproject/blob/master/setup.py
# and https://python-packaging-user-guide.readthedocs.org/

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
        "Topic :: Internet",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Testing :: Traffic Generation",
    ],

    packages=find_packages(),
    include_package_data=True,

    install_requires=[
        "pyasn1>=0.1.7",
        "pyOpenSSL>=0.14",
        "passlib>=1.6.2"
    ],
    extras_require={
        'dev': [
            "mock>=1.0.1",
            "nose>=1.3.0",
            "nose-cov>=1.6",
            "coveralls>=0.4.1",
            "pathod>=%s, <%s" % (version.MINORVERSION, version.NEXT_MINORVERSION)
        ]
    }
)