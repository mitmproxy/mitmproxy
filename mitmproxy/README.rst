|travis| |coveralls| |downloads| |latest_release| |python_versions|

``mitmproxy`` is an interactive, SSL/TLS-capable man-in-the-middle proxy for HTTP
with a console interface.

``mitmdump`` is the command-line version of mitmproxy. Think tcpdump for HTTP.


Features
--------

- Intercept HTTP requests and responses and modify them on the fly.
- Save complete HTTP conversations for later replay and analysis.
- Replay the client-side of an HTTP conversations.
- Replay HTTP responses of a previously recorded server.
- Reverse proxy mode to forward traffic to a specified server.
- Transparent proxy mode on OSX and Linux.
- Make scripted changes to HTTP traffic using Python.
- SSL/TLS certificates for interception are generated on the fly.
- And much, much more.

``mitmproxy`` is tested and developed on Mac OSX and Linux.
On Windows, only mitmdump is supported, which does not have a graphical user interface.


Documentation & Help
--------------------

Documentation, tutorials and distribution packages can be found on the
mitmproxy website.

|mitmproxy_site|

Installation Instructions are available in the documentation.

|mitmproxy_docs|

You can join our developer chat on Slack.

|slack|


.. |mitmproxy_site| image:: https://shields.mitmproxy.org/api/https%3A%2F%2F-mitmproxy.org-blue.svg
    :target: https://mitmproxy.org/
    :alt: mitmproxy.org

.. |mitmproxy_docs| image:: https://readthedocs.org/projects/mitmproxy/badge/
    :target: http://docs.mitmproxy.org/en/latest/
    :alt: mitmproxy documentation

.. |slack| image:: http://slack.mitmproxy.org/badge.svg
    :target: http://slack.mitmproxy.org/
    :alt: Slack Developer Chat

.. |travis| image:: https://shields.mitmproxy.org/travis/mitmproxy/mitmproxy/master.svg
    :target: https://travis-ci.org/mitmproxy/mitmproxy
    :alt: Build Status

.. |coveralls| image:: https://shields.mitmproxy.org/coveralls/mitmproxy/mitmproxy/master.svg
    :target: https://coveralls.io/r/mitmproxy/mitmproxy
    :alt: Coverage Status

.. |downloads| image:: https://shields.mitmproxy.org/pypi/dm/mitmproxy.svg?color=orange
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Downloads

.. |latest_release| image:: https://shields.mitmproxy.org/pypi/v/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Latest Version

.. |python_versions| image:: https://shields.mitmproxy.org/pypi/pyversions/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Supported Python versions
