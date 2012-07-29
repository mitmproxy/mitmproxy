**pathod** is a collection of pathological tools for testing and torturing HTTP
clients and servers. The project has three components:

- **pathod**, an pathological HTTP daemon.
- **pathoc**, a perverse HTTP client. 
- **libpathod.test**, an API for easily using pathod and pathoc in unit tests.


Documentation
-------------

The pathod documentation is self-hosted. Just fire up pathod, like so:
    
    ./pathod 

And then browse to:

    http://localhost:9999

You can aways view the documentation for the latest release at the pathod
website:
    
    http://pathod.net


Installing
----------

If you already have **pip** on your system, installing **pathod** and its
dependencies is dead simple:
    
    pip install pathod

The project has the following dependencies:

* netlib_
* requests_

The project's test suite uses the nose_ unit testing framework.

.. _netlib: http://github.com/cortesi/netlib
.. _requests: http://docs.python-requests.org/en/latest/index.html 
.. _nose: http://nose.readthedocs.org/en/latest/ 
