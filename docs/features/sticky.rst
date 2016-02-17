.. _sticky:

Sticky cookies and auth
=======================

Sticky cookies
--------------

When the sticky cookie option is set, __mitmproxy__ will add the cookie most
recently set by the server to any cookie-less request. Consider a service that
sets a cookie to track the session after authentication. Using sticky cookies,
you can fire up mitmproxy, and authenticate to a service as you usually would
using a browser. After authentication, you can request authenticated resources
through mitmproxy as if they were unauthenticated, because mitmproxy will
automatically add the session tracking cookie to requests. Among other things,
this lets you script interactions with authenticated resources (using tools
like wget or curl) without having to worry about authentication.

Sticky cookies are especially powerful when used in conjunction with :ref:`clientreplay` - you can
record the authentication process once, and simply replay it on startup every time you need
to interact with the secured resources.

================== ======================
command-line       :option:`-t FILTER`
mitmproxy shortcut :kbd:`o` then :kbd:`t`
================== ======================


Sticky auth
-----------

The sticky auth option is analogous to the sticky cookie option, in that HTTP
**Authorization** headers are simply replayed to the server once they have been
seen. This is enough to allow you to access a server resource using HTTP Basic
authentication through the proxy. Note that :program:`mitmproxy` doesn't (yet) support
replay of HTTP Digest authentication.

================== ======================
command-line       :option:`-u FILTER`
mitmproxy shortcut :kbd:`o` then :kbd:`A`
================== ======================
