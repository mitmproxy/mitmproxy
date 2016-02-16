pathod
^^^^^^

|travis| |coveralls| |downloads| |latest_release| |python_versions|

**pathod** is a collection of pathological tools for testing and torturing HTTP
clients and servers. The project has three components:

- ``pathod``, an pathological HTTP daemon.
- ``pathoc``, a perverse HTTP client.
- ``pathod.test``, an API for easily using pathod and pathoc in unit tests.

Installing
----------

If you already have **pip** on your system, installing **pathod** and its
dependencies is dead simple:

.. code-block:: text

    pip install pathod

Documentation
-------------

The pathod documentation is self-hosted. Just fire up pathod, like so:

.. code-block:: text

    ./pathod

And then browse to:

`<http://localhost:9999>`_

You can always view the documentation for the latest release at the pathod
website:

`<http://pathod.net>`_


.. |travis| image:: https://shields.mitmproxy.org/travis/mitmproxy/pathod/master.svg
    :target: https://travis-ci.org/mitmproxy/pathod
    :alt: Build Status

.. |coveralls| image:: https://shields.mitmproxy.org/coveralls/mitmproxy/pathod/master.svg
    :target: https://coveralls.io/r/mitmproxy/pathod
    :alt: Coverage Status

.. |downloads| image:: https://shields.mitmproxy.org/pypi/dm/pathod.svg?color=orange
    :target: https://pypi.python.org/pypi/pathod
    :alt: Downloads

.. |latest_release| image:: https://shields.mitmproxy.org/pypi/v/pathod.svg
    :target: https://pypi.python.org/pypi/pathod
    :alt: Latest Version

.. |python_versions| image:: https://shields.mitmproxy.org/pypi/pyversions/pathod.svg
    :target: https://pypi.python.org/pypi/pathod
    :alt: Supported Python versions