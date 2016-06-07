.. _test:

pathod.test
===========

The **pathod.test** module is a light, flexible testing layer for HTTP clients.
It works by firing up a Pathod instance in a separate thread, letting you use
Pathod's full abilities to generate responses, and then query Pathod's internal
logs to establish what happened. All the mechanics of startup, shutdown, finding
free ports and so forth are taken care of for you.

The canonical docs can be accessed using pydoc:

>>> pydoc pathod.test

The remainder of this page demonstrates some common interaction patterns using
<a href="http://nose.readthedocs.org/en/latest/">nose</a>. These examples are
also applicable with only minor modification to most commonly used Python testing
engines.


Context Manager
---------------

.. literalinclude:: ../../examples/pathod/test_context.py
   :caption: examples/pathod/test_context.py
   :language: python


One instance per test
---------------------

.. literalinclude:: ../../examples/pathod/test_setup.py
   :caption: examples/pathod/test_setup.py
   :language: python
