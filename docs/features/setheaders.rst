.. _setheaders:

Set Headers
===========

This feature lets you specify a set of headers to be added to requests or
responses, based on a filter pattern. You can specify these either on the
command-line, or through an interactive editor in mitmproxy.

Example: Set the **Host** header to "example.com" for all requests.

.. code-block:: none

    mitmdump -R http://example.com --setheader :~q:Host:example.com

================== =============================
command-line       :option:`--setheader PATTERN`
mitmproxy shortcut :kbd:`o` then :kbd:`H`
================== =============================
