mitmproxy
^^^^^^^^^

|travis| |appveyor| |coverage| |latest_release| |python_versions|

This repository contains the **mitmproxy** and **pathod** projects.

``mitmproxy`` is an interactive, SSL-capable intercepting proxy with a console
interface.

``mitmdump`` is the command-line version of mitmproxy. Think tcpdump for HTTP.

``mitmweb`` is a web-based interface for mitmproxy.

``pathoc`` and ``pathod`` are perverse HTTP client and server applications
designed to let you craft almost any conceivable HTTP request, including ones
that creatively violate the standards.


Documentation & Help
--------------------


General information, tutorials, and precompiled binaries can be found on the mitmproxy
and pathod websites.

|mitmproxy_site|

The latest documentation for mitmproxy is also available on ReadTheDocs.

|mitmproxy_docs|


Join our discussion forum on Discourse to ask questions, help
each other solve problems, and come up with new ideas for the project.

|mitmproxy_discourse|


Join our developer chat on Slack if you would like to contribute to mitmproxy itself.

|slack|


Installation
------------

The installation instructions are `here <http://docs.mitmproxy.org/en/stable/install.html>`__.
If you want to contribute changes, keep on reading.


Setting Up a Development Environment
------------------------------------

To get started hacking on mitmproxy, please follow the `advanced installation`_ steps to install mitmproxy from source, but stop right before running ``pip3 install mitmproxy``. Instead, do the following:

.. code-block:: text

    git clone https://github.com/mitmproxy/mitmproxy.git
    cd mitmproxy
    ./dev.sh  # "powershell .\dev.ps1" on Windows


The *dev* script will create a `virtualenv`_ environment in a directory called
"venv3.5", and install all mandatory and optional dependencies into it. The
primary mitmproxy components - mitmproxy and pathod - are installed as
"editable", so any changes to the source in the repository will be reflected
live in the virtualenv.

The main executables for the project - ``mitmdump``, ``mitmproxy``,
``mitmweb``, ``pathod``, and ``pathoc`` - are all created within the
virtualenv. After activating the virtualenv, they will be on your $PATH, and
you can run them like any other command:

.. code-block:: text

    . venv3.5/bin/activate  # "venv\Scripts\activate" on Windows
    mitmdump --version

For convenience, the project includes an autoenv_ file (`.env`_) that
auto-activates the virtualenv when you cd into the mitmproxy directory.


Testing
-------

If you've followed the procedure above, you already have all the development
requirements installed, and you can run the full test suite (including tests for code style and documentation) with tox_:

.. code-block:: text

    tox

For speedier testing, we recommend you run `py.test`_ directly on individual test files or folders:

.. code-block:: text

    cd test/mitmproxy/addons
    py.test --cov mitmproxy.addons.anticache --looponfail test_anticache.py

As py.test does not check the code style, you probably want to run ``tox -e lint`` before committing your changes.

Please ensure that all patches are accompanied by matching changes in the test
suite. The project tries to maintain 100% test coverage and enforces this strictly for some parts of the codebase.

Documentation
-------------

The mitmproxy documentation is build using Sphinx_, which is installed
automatically if you set up a development environment as described above. After
installation, you can render the documentation like this:

.. code-block:: text

    cd docs
    make clean
    make html
    make livehtml

The last command invokes `sphinx-autobuild`_, which watches the Sphinx directory and rebuilds
the documentation when a change is detected.

Code Style
----------

Keeping to a consistent code style throughout the project makes it easier to
contribute and collaborate. Please stick to the guidelines in
`PEP8`_ and the `Google Style Guide`_ unless there's a very
good reason not to.

This is automatically enforced on every PR. If we detect a linting error, the
PR checks will fail and block merging. You can run our lint checks yourself
with the following command:

.. code-block:: text

    tox -e lint


.. |mitmproxy_site| image:: https://shields.mitmproxy.org/api/https%3A%2F%2F-mitmproxy.org-blue.svg
    :target: https://mitmproxy.org/
    :alt: mitmproxy.org

.. |mitmproxy_docs| image:: https://readthedocs.org/projects/mitmproxy/badge/
    :target: http://docs.mitmproxy.org/en/latest/
    :alt: mitmproxy documentation

.. |mitmproxy_discourse| image:: https://shields.mitmproxy.org/api/https%3A%2F%2F-discourse.mitmproxy.org-orange.svg
    :target: https://discourse.mitmproxy.org
    :alt: Discourse: mitmproxy

.. |slack| image:: http://slack.mitmproxy.org/badge.svg
    :target: http://slack.mitmproxy.org/
    :alt: Slack Developer Chat

.. |travis| image:: https://shields.mitmproxy.org/travis/mitmproxy/mitmproxy/master.svg?label=Travis%20build
    :target: https://travis-ci.org/mitmproxy/mitmproxy
    :alt: Travis Build Status

.. |appveyor| image:: https://shields.mitmproxy.org/appveyor/ci/mhils/mitmproxy/master.svg?label=Appveyor%20build
    :target: https://ci.appveyor.com/project/mhils/mitmproxy
    :alt: Appveyor Build Status

.. |coverage| image:: https://codecov.io/gh/mitmproxy/mitmproxy/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/mitmproxy/mitmproxy
    :alt: Coverage Status

.. |latest_release| image:: https://shields.mitmproxy.org/pypi/v/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Latest Version

.. |python_versions| image:: https://shields.mitmproxy.org/pypi/pyversions/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Supported Python versions

.. _`advanced installation`: http://docs.mitmproxy.org/en/latest/install.html#advanced-installation
.. _virtualenv: https://virtualenv.pypa.io/
.. _.env: https://github.com/mitmproxy/mitmproxy/blob/master/.env
.. _autoenv: https://github.com/kennethreitz/autoenv
.. _`py.test`: http://pytest.org/
.. _tox: https://tox.readthedocs.io/
.. _Sphinx: http://sphinx-doc.org/
.. _sphinx-autobuild: https://pypi.python.org/pypi/sphinx-autobuild
.. _PEP8: https://www.python.org/dev/peps/pep-0008
.. _`Google Style Guide`: https://google.github.io/styleguide/pyguide.html
