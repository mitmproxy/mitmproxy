|travis| |coveralls| |downloads| |latest_release| |python_versions|

``mitmproxy`` is an interactive, SSL-capable man-in-the-middle proxy for HTTP
with a console interface.

``mitmdump`` is the command-line version of mitmproxy. Think tcpdump for HTTP.

``libmproxy`` is the library that mitmproxy and mitmdump are built on.

Features
--------

- Intercept HTTP requests and responses and modify them on the fly.
- Save complete HTTP conversations for later replay and analysis.
- Replay the client-side of an HTTP conversations.
- Replay HTTP responses of a previously recorded server.
- Reverse proxy mode to forward traffic to a specified server.
- Transparent proxy mode on OSX and Linux.
- Make scripted changes to HTTP traffic using Python.
- SSL certificates for interception are generated on the fly.
- And much, much more.

``mitmproxy`` is tested and developed on OSX, Linux and OpenBSD.
On Windows, only mitmdump is supported, which does not have a graphical user interface.

Documentation & Help
--------------------

Documentation, tutorials and distribution packages can be found on the
mitmproxy website.

|mitmproxy_site|

Installation Instructions are available in the docs.

|mitmproxy_docs|

You can join our developer chat on Slack.

|slack|


.. |mitmproxy_site| image:: https://img.shields.io/badge/https%3A%2F%2F-mitmproxy.org-blue.svg
    :target: https://mitmproxy.org/
    :alt: mitmproxy.org

.. |mitmproxy_docs| image:: https://readthedocs.org/projects/mitmproxy/badge/
    :target: http://docs.mitmproxy.org/en/latest/
    :alt: mitmproxy documentation

.. |slack| image:: http://slack.mitmproxy.org/badge.svg
    :target: http://slack.mitmproxy.org/
    :alt: Slack Developer Chat

.. |travis| image:: https://img.shields.io/travis/mitmproxy/mitmproxy/master.svg
    :target: https://travis-ci.org/mitmproxy/mitmproxy
    :alt: Build Status

.. |coveralls| image:: https://img.shields.io/coveralls/mitmproxy/mitmproxy/master.svg
    :target: https://coveralls.io/r/mitmproxy/mitmproxy
    :alt: Coverage Status

.. |downloads| image:: https://img.shields.io/pypi/dm/mitmproxy.svg?color=orange
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Downloads

.. |latest_release| image:: https://img.shields.io/pypi/v/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Latest Version

.. |python_versions| image:: https://img.shields.io/pypi/pyversions/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Supported Python versions
