.. _tcpproxy:

TCP Proxy
=========

In case mitmproxy does not handle a specific protocol, you can exempt
hostnames from processing, so that mitmproxy acts as a generic TCP forwarder.
This feature is closely related to the :ref:`passthrough` functionality,
but differs in two important aspects:

- The raw TCP messages are printed to the event log.
- SSL connections will be intercepted.

Please note that message interception or modification are not possible yet.
If you are not interested in the raw TCP messages, you should use the ignore domains feature.

How it works
------------

================== ======================
command-line       ``--tcp HOST``
mitmproxy shortcut :kbd:`O` then :kbd:`T`
================== ======================

For a detailed description how the hostname pattern works, please look at the :ref:`passthrough`
feature.

.. seealso::

    - :ref:`passthrough`
    - :ref:`responsestreaming`
