from setuptools import setup, find_packages
from codecs import open
import os
import sys

# Based on https://github.com/pypa/sampleproject/blob/master/setup.py
# and https://python-packaging-user-guide.readthedocs.org/

here = os.path.abspath(os.path.dirname(__file__))

sys.path.append(os.path.join(here, "..", "netlib"))
from libmproxy import version

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

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
    packages=find_packages(exclude=["test", "test.*"]),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'mitmproxy = libmproxy.main:mitmproxy',
            'mitmdump = libmproxy.main:mitmdump',
            'mitmweb = libmproxy.main:mitmweb'
        ]
    },
    # https://packaging.python.org/en/latest/requirements/#install-requires
    # It is not considered best practice to use install_requires to pin dependencies to specific versions.
    install_requires=[
        "netlib=={}".format(version.VERSION),
        "h2>=2.1.0, <2.2",
        "tornado>=4.3, <4.4",
        "configargparse>=0.10, <0.11",
        "pyperclip>=1.5.22, <1.6",
        "blinker>=1.4, <1.5",
        "pyparsing>=2.1,<2.2",
        "html2text==2016.1.8",
        "construct>=2.5.2, <2.6",
        "six>=1.10, <1.11",
        "Pillow>=3.1, <3.2",
        "watchdog>=0.8.3, <0.9",
        "click>=6.2, <7.0",
        "urwid>=1.3.1, <1.4",
    ],
    extras_require={
        ':sys_platform == "win32"': [
            "pydivert>=0.0.7, <0.1",
            "lxml==3.4.4",  # there are no Windows wheels for newer versions, so we pin this.
        ],
        ':sys_platform != "win32"': [
            "lxml>=3.5.0, <3.6",
        ],
        # Do not use a range operator here: https://bitbucket.org/pypa/setuptools/issues/380
        # Ubuntu Trusty and other still ship with setuptools < 17.1
        ':python_version == "2.7"': [
            "enum34>=1.0.4, <1.2",
        ],
        'dev': [
            "mock>=1.3.0, <1.4",
            "pytest>=2.8.7, <2.9",
            "pytest-xdist>=1.14, <1.15",
            "pytest-cov>=2.2.1, <2.3",
            "pytest-timeout>=1.0.0, <1.1",
            "coveralls>=1.1, <1.2",
            "pathod=={}".format(version.VERSION),
            "sphinx>=1.3.5, <1.4",
            "sphinx-autobuild>=0.5.2, <0.7",
            "sphinxcontrib-documentedlist>=0.3.0, <0.4"
        ],
        'contentviews': [
            "pyamf>=0.8.0, <0.9",
            "protobuf>=2.6.1, <2.7",
            "cssutils>=1.0.1, <1.1"
        ],
        'examples': [
            "pytz==2015.7.0",
            "harparser>=0.2, <0.3",
            "beautifulsoup4>=4.4.1, <4.5",
        ]
    }
)
