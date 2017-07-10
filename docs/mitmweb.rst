.. _mitmweb:
.. program:: mitmweb

mitmweb
=======

**mitmweb** is mitmproxy's web-based user interface that allows interactive
examination and modification of HTTP traffic. Like mitmproxy, it differs from
mitmdump in that all flows are kept in memory, which means that **it's intended
for taking and manipulating small-ish samples.** If you need to handle larger amounts of data with mitmweb, you should run your proxy with mitmdump and write the output to a file, then run ``mitmweb --read-flows /path/to/mitmdump/output/file``.

.. warning::

  Mitmweb is currently in beta. We consider it stable for all features currently
  exposed in the UI, but it still misses a lot of mitmproxy's features.


.. image:: screenshots/mitmweb.png
