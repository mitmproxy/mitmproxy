.. _passthrough:

Ignore Domains
==============

There are two main reasons why you may want to exempt some traffic from mitmproxy's interception
mechanism:

- **Certificate pinning:** Some traffic is is protected using `Certificate Pinning`_ and
  mitmproxy's interception leads to errors. For example, the Twitter app, Windows Update or
  the Apple App Store fail to work if mitmproxy is active.
- **Convenience:** You really don't care about some parts of the traffic and just want them to go
  away.

If you want to peek into (SSL-protected) non-HTTP connections, check out the :ref:`tcpproxy`
feature.
If you want to ignore traffic from mitmproxy's processing because of large response bodies,
take a look at the :ref:`responsestreaming` feature.

How it works
------------

================== =============================
command-line       :option:`--ignore regex`
mitmproxy shortcut :kbd:`o` then :kbd:`I`
================== =============================


mitmproxy allows you to specify a regex which is matched against a ``host:port`` string
(e.g. "example.com:443") to determine hosts that should be excluded.

There are two important quirks to consider:

- **In transparent mode, the ignore pattern is matched against the IP and ClientHello SNI host.** While we usually infer the
  hostname from the Host header if the :option:`--host` argument is passed to mitmproxy, we do not
  have access to this information before the SSL handshake. If the client uses SNI however, then we treat the SNI host as an ignore target.
- In regular mode, explicit HTTP requests are never ignored. [#explicithttp]_ The ignore pattern is
  applied on CONNECT requests, which initiate HTTPS or clear-text WebSocket connections.

Tutorial
--------

If you just want to ignore one specific domain, there's usually a bulletproof method to do so:

1. Run mitmproxy or mitmdump in verbose mode (:option:`-v`) and observe the ``host:port``
   information in the serverconnect messages. mitmproxy will filter on these.
2. Take the ``host:port`` string, surround it with ^ and $, escape all dots (. becomes \\.)
   and use this as your ignore pattern:

.. code-block:: none
    :emphasize-lines: 6,7,9

    >>> mitmdump -v
    127.0.0.1:50588: clientconnect
    127.0.0.1:50588: request
      -> CONNECT example.com:443 HTTP/1.1
    127.0.0.1:50588: Set new server address: example.com:443
    127.0.0.1:50588: serverconnect
      -> example.com:443
    ^C
    >>> mitmproxy --ignore ^example\.com:443$


Here are some other examples for ignore patterns:

.. code-block:: none

    # Exempt traffic from the iOS App Store (the regex is lax, but usually just works):
    --ignore apple.com:443
    # "Correct" version without false-positives:
    --ignore '^(.+\.)?apple\.com:443$'

    # Ignore example.com, but not its subdomains:
    --ignore '^example.com:'

    # Ignore everything but example.com and mitmproxy.org:
    --ignore '^(?!example\.com)(?!mitmproxy\.org)'

    # Transparent mode:
    --ignore 17\.178\.96\.59:443
    # IP address range:
    --ignore 17\.178\.\d+\.\d+:443


.. seealso::

    - :ref:`tcpproxy`
    - :ref:`responsestreaming`

.. rubric:: Footnotes

.. [#explicithttp] This stems from an limitation of explicit HTTP proxying:
    A single connection can be re-used for multiple target domains - a
    ``GET http://example.com/`` request may be followed by a ``GET http://evil.com/`` request on the
    same connection. If we start to ignore the connection after the first request,
    we would miss the relevant second one.
.. _Certificate Pinning: https://security.stackexchange.com/questions/29988/what-is-certificate-pinning
