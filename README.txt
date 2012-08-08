**mitmproxy** is an SSL-capable man-in-the-middle proxy for HTTP. It provides a
console interface that allows traffic flows to be inspected and edited on the
fly.

**mitmdump** is the command-line version of mitmproxy, with the same
functionality but without the user interface. Think tcpdump for HTTP.

Complete documentation and a set of practical tutorials is included in the
distribution package, and is also available at mitmproxy.org_.


Features
--------

- Intercept HTTP requests and responses and modify them on the fly.
- Save complete HTTP conversations for later replay and analysis.
- Replay the client-side of an HTTP conversations.
- Replay HTTP responses of a previously recorded server.
- Reverse proxy mode to forward traffic to a specified server.
- Make scripted changes to HTTP traffic using Python. 
- SSL certificates for interception are generated on the fly.


Download
--------

Releases and rendered documentation can be found on the mitmproxy website:

mitmproxy.org_

Source is hosted on github: 

`github.com/cortesi/mitmproxy`_


Community
---------

Come join us in the #mitmproxy channel on the OFTC IRC network
(irc.oftc.net, port 6667).

We also have a mailing list, hosted here:

http://groups.google.com/group/mitmproxy


Requirements
------------

* Python_ 2.6.x or 2.7.x.
* PyOpenSSL_ 0.13 or newer.
* pyasn1_ 0.1.2 or newer.
* urwid_  version 0.9.8 or newer.
* PIL_  version 1.1 or newer.
* lxml_ version 2.3 or newer.

The following auxiliary components may be needed if you plan to hack on
mitmproxy:

* The test suite uses the nose_ unit testing
  framework.
* Rendering the documentation requires countershape_.

**mitmproxy** is tested and developed on OSX, Linux and OpenBSD. Windows is not
supported at the moment.

You should also make sure that your console environment is set up with the
following: 
    
* EDITOR environment variable to determine the external editor.
* PAGER environment variable to determine the external pager.
* Appropriate entries in your mailcap files to determine external
  viewers for request and response contents.

.. _mitmproxy.org: http://mitmproxy.org
.. _github.com/cortesi/mitmproxy: http://github.com/cortesi/mitmproxy
.. _python: http://www.python.org
.. _PyOpenSSL: http://pypi.python.org/pypi/pyOpenSSL
.. _pyasn1: http://pypi.python.org/pypi/pyasn1
.. _PIL: http://www.pythonware.com/products/pil/
.. _lxml: http://lxml.de/
.. _urwid: http://excess.org/urwid/
.. _nose: http://readthedocs.org/docs/nose/en/latest/
.. _countershape: http://github.com/cortesi/countershape
