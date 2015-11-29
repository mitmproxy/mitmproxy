|travis| |coveralls| |downloads| |latest-release| |python-versions|

Netlib is a collection of network utility classes, used by the pathod and
mitmproxy projects. It differs from other projects in some fundamental
respects, because both pathod and mitmproxy often need to violate standards.
This means that protocols are implemented as small, well-contained and flexible
functions, and are designed to allow misbehaviour when needed.


Hacking
-------

If you'd like to work on netlib, check out the instructions in mitmproxy's README_.

.. |travis| image:: https://img.shields.io/travis/mitmproxy/netlib/master.svg
    :target: https://travis-ci.org/mitmproxy/netlib
    :alt: Build Status

.. |coveralls| image:: https://img.shields.io/coveralls/mitmproxy/netlib/master.svg
    :target: https://coveralls.io/r/mitmproxy/netlib
    :alt: Coverage Status

.. |downloads| image:: https://img.shields.io/pypi/dm/netlib.svg?color=orange
    :target: https://pypi.python.org/pypi/netlib
    :alt: Downloads

.. |latest-release| image:: https://img.shields.io/pypi/v/netlib.svg
    :target: https://pypi.python.org/pypi/netlib
    :alt: Latest Version

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/netlib.svg
    :target: https://pypi.python.org/pypi/netlib
    :alt: Supported Python versions

.. _README: https://github.com/mitmproxy/mitmproxy#hacking