.. _overview:

Introduction
============

Mitmproxy has a powerful scripting API that allows you to control almost any
aspect of traffic being proxied. In fact, much of mitmproxy's own core
functionality is implemented using the exact same API exposed to scripters (see
:src:`mitmproxy/builtins`).


A simple example
----------------

Scripting is event driven, with named handlers on the script object called at
appropriate points of mitmproxy's operation. Here's a complete mitmproxy script
that adds a new header to every HTTP response before it is returned to the
client:

.. literalinclude:: ../../examples/add_header.py
   :caption: :src:`examples/add_header.py`
   :language: python

All events that deal with an HTTP request get an instance of `HTTPFlow
<api.html#mitmproxy.models.http.HTTPFlow>`_, which we can use to manipulate the
response itself. We can now run this script using mitmdump, and the new header
will be added to all responses passing through the proxy:

>>> mitmdump -s add_header.py


Using classes
-------------

In the example above, the script object is the ``add_header`` module itself.
That is, the handlers are declared at the global level of the script. This is
great for quick hacks, but soon becomes limiting as scripts become more
sophisticated.

When a script first starts up, the `start <events.html#start>`_, event is
called before anything else happens. You can replace the current script object
by returning it from this handler. Here's how this looks when applied to the
example above:

.. literalinclude:: ../../examples/classes.py
   :caption: :src:`examples/classes.py`
   :language: python

So here, we're using a module-level script to "boot up" into a class instance.
From this point on, the module-level script is removed from the handler chain,
and is replaced by the class instance.


Handling arguments
------------------

Scripts can handle their own command-line arguments, just like any other Python
program. Let's build on the example above to do something slightly more
sophisticated - replace one value with another in all responses. Mitmproxy's
`HTTPRequest <api.html#mitmproxy.models.http.HTTPRequest>`_ and `HTTPResponse
<api.html#mitmproxy.models.http.HTTPResponse>`_ objects have a handy `replace
<api.html#mitmproxy.models.http.HTTPResponse.replace>`_ method that takes care
of all the details for us.

.. literalinclude:: ../../examples/arguments.py
   :caption: :src:`examples/arguments.py`
   :language: python

We can now call this script on the command-line like this:

>>> mitmdump -dd -s "./arguments.py html faketml"

Whenever a handler is called, mitpmroxy rewrites the script environment so that
it sees its own arguments as if it was invoked from the command-line.


Running scripts in parallel
---------------------------

We have a single flow primitive, so when a script is blocking, other requests are not processed.
While that's usually a very desirable behaviour, blocking scripts can be run threaded by using the
:py:obj:`mitmproxy.script.concurrent` decorator.
**If your script does not block, you should avoid the overhead of the decorator.**

.. literalinclude:: ../../examples/nonblocking.py
   :caption: examples/nonblocking.py
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
