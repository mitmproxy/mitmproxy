.. _mitmweb:
.. program:: mitmweb

mitmweb
=======

**mitmweb** is mitmproxy's web-based user interface that allows interactive
examination and modification of HTTP traffic. Like mitmproxy, it differs from
mitmdump in that all flows are kept in memory, which means that **it's intended
for taking and manipulating small-ish samples.**

If you need to handle large amounts of data and want the web interface available after-the-fact, you can run your proxy with ``mitmdump`` and then use ``mitmweb -n --read-flows /path/to/mitmdump/output/file`` to read the flows from your mitmdump capture.

If you need mitmweb to work in real time during the capture, but do not want to store the flows in RAM, you can simply specify an output file with ``mitmweb -w /path/to/output/file``.

.. warning::

  Mitmweb is currently in beta. We consider it stable for all features currently
  exposed in the UI, but it still misses a lot of mitmproxy's features.


.. image:: screenshots/mitmweb.png
