from distutils.command.build import build
from setuptools.command.install import install
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


def get_ext_modules():
    from netlib import certffi
    return [certffi.xffi.verifier.get_extension()]


class CFFIBuild(build):

    def finalize_options(self):
        self.distribution.ext_modules = get_ext_modules()
        build.finalize_options(self)


class CFFIInstall(install):

    def finalize_options(self):
        self.distribution.ext_modules = get_ext_modules()
        install.finalize_options(self)

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
        "cffi",
        "pyasn1>=0.1.7",
        "pyOpenSSL>=0.15.1",
        "cryptography>=0.9",
        "passlib>=1.6.2",
        "hpack>=1.0.1"],
    setup_requires=[
        "cffi",
        "pyOpenSSL>=0.15.1",
    ],
    extras_require={
        'dev': [
            "mock>=1.0.1",
            "nose>=1.3.0",
            "nose-cov>=1.6",
            "coveralls>=0.4.1",
            "autopep8>=1.0.3",
            "autoflake>=0.6.6",
            "pathod>=%s, <%s" %
            (version.MINORVERSION,
             version.NEXT_MINORVERSION)]},
    cmdclass={
        "build": CFFIBuild,
        "install": CFFIInstall,
    },
)
