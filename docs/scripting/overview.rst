.. _overview:

Overview
========

Mitmproxy has a powerful scripting API that allows you to control almost any
aspect of traffic being proxied. In fact, much of mitmproxy's own core
functionality is implemented using the exact same API exposed to scripters (see
:src:`mitmproxy/addons`).


A simple example
----------------

Scripting is event driven, with named handlers on the script object called at
appropriate points of mitmproxy's operation. Here's a complete mitmproxy script
that adds a new header to every HTTP response before it is returned to the
client:

.. literalinclude:: ../../examples/simple/add_header.py
   :caption: :src:`examples/simple/add_header.py`
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

.. literalinclude:: ../../examples/simple/add_header_class.py
   :caption: :src:`examples/simple/add_header_class.py`
   :language: python

So here, we're using a module-level script to "boot up" into a class instance.
From this point on, the module-level script is removed from the handler chain,
and is replaced by the class instance.


Handling arguments
------------------


FIXME


Logging and the context
-----------------------

Scripts should not output straight to stderr or stdout. Instead, the `log
<api.html#mitmproxy.controller.Log>`_ object on the ``ctx`` context module
should be used, so that the mitmproxy host program can handle output
appropriately. So, mitmdump can print colorised script output to the terminal,
and mitmproxy console can place script output in the event buffer.

Here's how this looks:

.. literalinclude:: ../../examples/simple/log_events.py
   :caption: :src:`examples/simple/log_events.py`
   :language: python

The ``ctx`` module also exposes the mitmproxy master object at ``ctx.master``
for advanced usage.


Running scripts on saved flows
------------------------------

When a flow is loaded from disk, the sequence of events that the flow would
have gone through on the wire is partially replayed. So, for instance, an HTTP
flow loaded from disk will trigger `requestheaders
<events.html#requestheaders>`_,  `request <events.html#request>`_,
`responseheaders <events.html#responseheaders>`_ and  `response
<events.html#response>`_ in order. We can use this behaviour to transform saved
traffic using scripts. For example, we can invoke the replacer script from
above on saved traffic as follows:

>>> mitmdump -dd -s "./arguments.py html fakehtml" -r saved -w changed

This command starts the ``arguments`` script, reads all the flows from
``saved`` transforming them in the process, then writes them all to
``changed``.

The mitmproxy console tool provides interactive ways to run transforming
scripts on flows - for instance, you can run a one-shot script on a single flow
through the ``|`` (pipe) shortcut.


Concurrency
-----------

The mitmproxy script mechanism is single threaded, and the proxy blocks while
script handlers execute. This hugely simplifies the most common case, where
handlers are light-weight and the blocking doesn't have a performance impact.
It's possible to implement a concurrent mechanism on top of the blocking
framework, and mitmproxy includes a handy example of this that is fit for most
purposes. You can use it as follows:

.. literalinclude:: ../../examples/complex/nonblocking.py
   :caption: :src:`examples/complex/nonblocking.py`
   :language: python


Testing
-------

Mitmproxy includes a number of helpers for testing addons. The
``mitmproxy.test.taddons`` module contains a context helper that takes care of
setting up and tearing down the addon event context. The
``mitmproxy.test.tflow`` module contains helpers for quickly creating test
flows. Pydoc is the canonical reference for these modules, and mitmproxy's own
test suite is an excellent source of examples of usage. Here, for instance, is
the mitmproxy unit tests for the `anticache` option, demonstrating a good
cross-section of the test helpers:

.. literalinclude:: ../../test/mitmproxy/addons/test_anticache.py
   :caption: :src:`test/mitmproxy/addons/test_anticache.py`
   :language: python


Developing scripts
------------------

Mitmproxy monitors scripts for modifications, and reloads them on change. When
this happens, the script is shut down (the `done <events.html#done>`_  event is
called), and the new instance is started up as if the script had just been
loaded (the `start <events.html#start>`_ and `configure
<events.html#configure>`_ events are called).
