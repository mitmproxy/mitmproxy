.. _anticache:

Anticache
=========
When the :option:`--anticache` option is passed to mitmproxy, it removes headers
(``if-none-match`` and ``if-modified-since``) that might elicit a
``304 not modified`` response from the server. This is useful when you want to make
sure you capture an HTTP exchange in its totality. It's also often used during
:ref:`clientreplay`, when you want to make sure the server responds with complete data.


================== ======================
command-line       :option:`--anticache`
mitmproxy shortcut :kbd:`o` then :kbd:`a`
================== ======================
