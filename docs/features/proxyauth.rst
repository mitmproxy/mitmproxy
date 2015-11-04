.. _proxyauth:

Proxy Authentication
====================


Asks the user for authentication before they are permitted to use the proxy.
Authentication headers are stripped from the flows, so they are not passed to
upstream servers. For now, only HTTP Basic authentication is supported. The
proxy auth options are not compatible with the transparent, socks or reverse proxy
mode.

================== =============================
command-line       :option:`--nonanonymous`,
                   :option:`--singleuser USER`,
                   :option:`--htpasswd PATH`
================== =============================
