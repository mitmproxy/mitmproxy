from setuptools import setup, find_packages
from codecs import open
import os
from libpathod import version

# Based on https://github.com/pypa/sampleproject/blob/master/setup.py
# and https://python-packaging-user-guide.readthedocs.org/

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="pathod",
    version=version.VERSION,
    description="A pathological HTTP/S daemon for testing and stressing clients.",
    long_description=long_description,
    url="http://pathod.net",
    author="Aldo Cortesi",
    author_email="aldo@corte.si",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Development Status :: 5 - Production/Stable",
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
    entry_points={
        'console_scripts': [
            "pathod = libpathod.pathod_cmdline:go_pathod",
            "pathoc = libpathod.pathoc_cmdline:go_pathoc"
        ]
    },
    install_requires=[
        "netlib>=%s, <%s" % (version.MINORVERSION, version.NEXT_MINORVERSION),
        # It's INSANE that we have to do this, but...
        # FIXME: Requirement to be removed at next release
        "pip>=1.5.6",
        "requests>=2.4.1",
        "Flask>=0.10.1",
        "pyparsing>=2.0.3"
    ],
    extras_require={
        'dev': [
            "mock>=1.0.1",
            "nose>=1.3.0",
            "nose-cov>=1.6",
            "coveralls>=0.4.1"
        ]
    }
)
