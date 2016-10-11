.. _overview:

Overview
=========

Mitmproxy has a powerful scripting API that allows you to control almost any
aspect of traffic being proxied. In fact, much of mitmproxy's own core
functionality is implemented using the exact same API exposed to scripters (see
:src:`mitmproxy/builtins`).

Scripting is event driven, with named handlers on the script object called at
appropriate points of mitmproxy's operation. Here's a complete mitmproxy script
that adds a new header to every HTTP response before it is returned to the
client:

.. literalinclude:: ../../examples/add_header.py
   :caption: :src:`examples/add_header.py`
   :language: python

All events that deal with an HTTP request get an instance of
:py:class:`~mitmproxy.models.HTTPFlow`, which we can use to manipulate the
response itself. We can now run this script using mitmdump or mitmproxy as
follows:

>>> mitmdump -s add_header.py

The new header will be added to all responses passing through the proxy.


mitmproxy comes with a variety of example inline scripts, which demonstrate
many basic tasks.


Running scripts in parallel
---------------------------

We have a single flow primitive, so when a script is blocking, other requests are not processed.
While that's usually a very desirable behaviour, blocking scripts can be run threaded by using the
:py:obj:`mitmproxy.script.concurrent` decorator.
**If your script does not block, you should avoid the overhead of the decorator.**

.. literalinclude:: ../../examples/nonblocking.py
   :caption: examples/nonblocking.py
   :language: python

Make scripts configurable with arguments
----------------------------------------

Sometimes, you want to pass runtime arguments to the inline script. This can be simply done by
surrounding the script call with quotes, e.g. ```mitmdump -s 'script.py --foo 42'``.
The arguments are then exposed in the start event:

.. literalinclude:: ../../examples/modify_response_body.py
   :caption: examples/modify_response_body.py
   :language: python


Running scripts on saved flows
------------------------------

Sometimes, we want to run a script on :py:class:`~mitmproxy.models.Flow` objects that are already
complete.  This happens when you start a script, and then load a saved set of flows from a file
(see the "scripted data transformation" example :ref:`here <mitmdump>`).
It also happens when you run a one-shot script on a single flow through the ``|`` (pipe) shortcut
in mitmproxy.

In this case, there are no client connections, and the events are run in the following order:
**start**, **request**, **responseheaders**, **response**, **error**, **done**.
If the flow doesn't have a **response** or **error** associated with it, the matching events will
be skipped.

Spaces in the script path
-------------------------

By default, spaces are interpreted as a separator between the inline script and its arguments
(e.g. ``-s 'foo.py 42'``). Consequently, the script path needs to be wrapped in a separate pair of
quotes if it contains spaces: ``-s '\'./foo bar/baz.py\' 42'``.

.. _GitHub: https://github.com/mitmproxy/mitmproxy
