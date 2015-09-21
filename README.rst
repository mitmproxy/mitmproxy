|travis| |coveralls| |downloads| |latest-release| |python-versions|

``mitmproxy`` is an interactive, SSL-capable man-in-the-middle proxy for HTTP
with a console interface.

``mitmdump`` is the command-line version of mitmproxy. Think tcpdump for HTTP.

``libmproxy`` is the library that mitmproxy and mitmdump are built on.

Documentation & Help
--------------------

Documentation, tutorials and distribution packages can be found on the
mitmproxy website.

|site|

Installation Instructions are available in the docs.

|docs|

You can join our developer chat on Slack.

|slack|

Features
--------

- Intercept HTTP requests and responses and modify them on the fly.
- Save complete HTTP conversations for later replay and analysis.
- Replay the client-side of an HTTP conversations.
- Replay HTTP responses of a previously recorded server.
- Reverse proxy mode to forward traffic to a specified server.
- Transparent proxy mode on OSX and Linux.
- Make scripted changes to HTTP traffic using Python.
- SSL certificates for interception are generated on the fly.
- And much, much more.

``mitmproxy`` is tested and developed on OSX, Linux and OpenBSD.
On Windows, only mitmdump is supported, which does not have a graphical user interface.



Hacking
-------

To get started hacking on mitmproxy, make sure you have Python_ 2.7.x. with
virtualenv_ installed (you can find installation instructions for virtualenv here_).
Then do the following:

.. code-block:: text

    git clone https://github.com/mitmproxy/mitmproxy.git
    git clone https://github.com/mitmproxy/netlib.git
    git clone https://github.com/mitmproxy/pathod.git
    cd mitmproxy
    ./dev


The *dev* script will create a virtualenv environment in a directory called
"venv.mitmproxy", and install all of mitmproxy's development requirements, plus
all optional modules. The primary mitmproxy components - mitmproxy, netlib and
pathod - are all installed "editable", so any changes to the source in the git
checkouts will be reflected live in the virtualenv.

To confirm that you're up and running, activate the virtualenv, and run the
mitmproxy test suite:

.. code-block:: text

    . ../venv.mitmproxy/bin/activate # ..\venv.mitmproxy\Scripts\activate.bat on Windows
    py.test -n 4 --cov libmproxy

Note that the main executables for the project - ``mitmdump``, ``mitmproxy`` and
``mitmweb`` - are all created within the virtualenv. After activating the
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

    py.test -n 4 --cov libmproxy

Please ensure that all patches are accompanied by matching changes in the test
suite. The project maintains 100% test coverage.


Docs
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


.. |site| image:: https://img.shields.io/badge/https%3A%2F%2F-mitmproxy.org-blue.svg
    :target: https://mitmproxy.org/
    :alt: mitmproxy.org

.. |docs| image:: https://readthedocs.org/projects/mitmproxy/badge/
    :target: http://docs.mitmproxy.org/en/latest/
    :alt: Documentation

.. |slack| image:: http://slack.mitmproxy.org/badge.svg
    :target: http://slack.mitmproxy.org/
    :alt: Slack Developer Chat

.. |travis| image:: https://img.shields.io/travis/mitmproxy/mitmproxy/master.svg
    :target: https://travis-ci.org/mitmproxy/mitmproxy
    :alt: Build Status

.. |coveralls| image:: https://img.shields.io/coveralls/mitmproxy/mitmproxy/master.svg
    :target: https://coveralls.io/r/mitmproxy/mitmproxy
    :alt: Coverage Status

.. |downloads| image:: https://img.shields.io/pypi/dm/mitmproxy.svg?color=orange
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Downloads

.. |latest-release| image:: https://img.shields.io/pypi/v/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Latest Version

.. |python-versions| image:: https://img.shields.io/pypi/pyversions/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Supported Python versions

.. _Python: https://www.python.org/
.. _virtualenv: https://virtualenv.pypa.io/en/latest/
.. _here: https://virtualenv.pypa.io/en/latest/installation.html
.. _autoenv: https://github.com/kennethreitz/autoenv
.. _.env: https://github.com/mitmproxy/mitmproxy/blob/master/.env
.. _Sphinx: http://sphinx-doc.org/
.. _sphinx-autobuild: https://pypi.python.org/pypi/sphinx-autobuild
