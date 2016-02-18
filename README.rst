mitmproxy
^^^^^^^^^

|travis| |coveralls| |downloads| |latest_release| |python_versions|

This repository contains the **mitmproxy** and **pathod** projects, as well as their shared networking library, **netlib**.

``mitmproxy`` is an interactive, SSL-capable intercepting proxy with a console interface.

``mitmdump`` is the command-line version of mitmproxy. Think tcpdump for HTTP.

``pathoc`` and ``pathod`` are perverse HTTP client and server applications designed to let you craft almost any conceivable HTTP request, including ones that creatively violate the standards.


Documentation & Help
--------------------

Documentation, tutorials and precompiled binaries can be found on the mitmproxy and pathod websites.

|mitmproxy_site| |pathod_site|

The latest documentation for mitmproxy is also available on ReadTheDocs.

|mitmproxy_docs|

You can join our developer chat on Slack.

|slack|


Hacking
-------

To get started hacking on mitmproxy, make sure you have Python_ 2.7.x. with
virtualenv_ installed (you can find installation instructions for virtualenv here_).
Then do the following:

.. code-block:: text

    git clone https://github.com/mitmproxy/mitmproxy.git
    cd mitmproxy
    ./dev


The *dev* script will create a virtualenv environment in a directory called "venv",
and install all mandatory and optional dependencies into it.
The primary mitmproxy components - mitmproxy, netlib and pathod - are installed as "editable",
so any changes to the source in the repository will be reflected live in the virtualenv.

To confirm that you're up and running, activate the virtualenv, and run the
mitmproxy test suite:

.. code-block:: text

    . venv/bin/activate # venv\Scripts\activate.bat on Windows
    py.test

Note that the main executables for the project - ``mitmdump``, ``mitmproxy``,
``mitmweb``, ``pathod``, and ``pathoc`` - are all created within the virtualenv. After activating the
virtualenv, they will be on your $PATH, and you can run them like any other
command:

.. code-block:: text

    mitmdump --version

For convenience, the project includes an autoenv_ file (`.env`_) that
auto-activates the virtualenv when you cd into the mitmproxy directory.


Testing
-------

If you've followed the procedure above, you already have all the development
requirements installed, and you can simply run the test suite:

.. code-block:: text

    py.test

Please ensure that all patches are accompanied by matching changes in the test
suite. The project tries to maintain 100% test coverage.


Documentation
----

The mitmproxy documentation is build using Sphinx_, which is installed automatically if you set up a development
environment as described above.
After installation, you can render the documentation like this:

.. code-block:: text

    cd docs
    make clean
    make html
    make livehtml

The last command invokes `sphinx-autobuild`_, which watches the Sphinx directory and rebuilds
the documentation when a change is detected.



.. |mitmproxy_site| image:: https://shields.mitmproxy.org/api/https%3A%2F%2F-mitmproxy.org-blue.svg
    :target: https://mitmproxy.org/
    :alt: mitmproxy.org

.. |pathod_site| image:: https://shields.mitmproxy.org/api/https%3A%2F%2F-pathod.net-blue.svg
    :target: https://pathod.net/
    :alt: pathod.net

.. |mitmproxy_docs| image:: https://readthedocs.org/projects/mitmproxy/badge/
    :target: http://docs.mitmproxy.org/en/latest/
    :alt: mitmproxy documentation

.. |slack| image:: http://slack.mitmproxy.org/badge.svg
    :target: http://slack.mitmproxy.org/
    :alt: Slack Developer Chat

.. |travis| image:: https://shields.mitmproxy.org/travis/mitmproxy/mitmproxy/master.svg
    :target: https://travis-ci.org/mitmproxy/mitmproxy
    :alt: Build Status

.. |coveralls| image:: https://shields.mitmproxy.org/coveralls/mitmproxy/mitmproxy/master.svg
    :target: https://coveralls.io/r/mitmproxy/mitmproxy
    :alt: Coverage Status

.. |downloads| image:: https://shields.mitmproxy.org/pypi/dm/mitmproxy.svg?color=orange
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Downloads

.. |latest_release| image:: https://shields.mitmproxy.org/pypi/v/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Latest Version

.. |python_versions| image:: https://shields.mitmproxy.org/pypi/pyversions/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Supported Python versions

.. _Python: https://www.python.org/
.. _virtualenv: http://virtualenv.readthedocs.org/en/latest/
.. _here: http://virtualenv.readthedocs.org/en/latest/installation.html
.. _autoenv: https://github.com/kennethreitz/autoenv
.. _.env: https://github.com/mitmproxy/mitmproxy/blob/master/.env
.. _Sphinx: http://sphinx-doc.org/
.. _sphinx-autobuild: https://pypi.python.org/pypi/sphinx-autobuild
.. _issue_tracker: https://github.com/mitmproxy/mitmproxy/issues
