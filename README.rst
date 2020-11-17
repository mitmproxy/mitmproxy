mitmproxy
^^^^^^^^^

|ci_status| |coverage| |latest_release| |python_versions|

This repository contains the **mitmproxy** and **pathod** projects.

``mitmproxy`` is an interactive, SSL/TLS-capable intercepting proxy with a console
interface for HTTP/1, HTTP/2, and WebSockets.

``mitmdump`` is the command-line version of mitmproxy. Think tcpdump for HTTP.

``mitmweb`` is a web-based interface for mitmproxy.

``pathoc`` and ``pathod`` are perverse HTTP client and server applications
designed to let you craft almost any conceivable HTTP request, including ones
that creatively violate the standards.


Documentation & Help
--------------------


General information, tutorials, and precompiled binaries can be found on the mitmproxy website.

|mitmproxy_site|

The documentation for mitmproxy is available on our website:

|mitmproxy_docs_stable| |mitmproxy_docs_master|

If you have questions on how to use mitmproxy, please
ask them on StackOverflow!

|mitmproxy_stackoverflow|

Join our developer chat on Slack if you would like to contribute to mitmproxy itself.

|slack|


Installation
------------

The installation instructions are `here <https://docs.mitmproxy.org/stable/overview-installation>`__.
If you want to contribute changes, keep on reading.

Contributing
------------

As an open source project, mitmproxy welcomes contributions of all forms. If you would like to bring the project forward,
please consider contributing in the following areas:

- **Maintenance:** We are *incredibly* thankful for individuals who are stepping up and helping with maintenance. This includes (but is not limited to) triaging issues, reviewing pull requests and picking up stale ones, helping out other users on StackOverflow_, creating minimal, complete and verifiable examples or test cases for existing bug reports, updating documentation, or fixing minor bugs that have recently been reported.
- **Code Contributions:** We actively mark issues that we consider are `good first contributions`_. If you intend to work on a larger contribution to the project, please come talk to us first.

Development Setup
-----------------

To get started hacking on mitmproxy, please install a recent version of Python (we require at least 3.6).
The following commands should work on your system:

.. code-block:: bash

    python3 --version
    python3 -m pip --help
    python3 -m venv --help

If all of this run successfully, do the following:

.. code-block:: bash

    git clone https://github.com/mitmproxy/mitmproxy.git
    cd mitmproxy
    ./dev.sh  # "powershell .\dev.ps1" on Windows


The *dev* script will create a `virtualenv`_ environment in a directory called "venv"
and install all mandatory and optional dependencies into it. The primary
mitmproxy components - mitmproxy and pathod - are installed as
"editable", so any changes to the source in the repository will be reflected
live in the virtualenv.

The main executables for the project - ``mitmdump``, ``mitmproxy``,
``mitmweb``, ``pathod``, and ``pathoc`` - are all created within the
virtualenv. After activating the virtualenv, they will be on your $PATH, and
you can run them like any other command:

.. code-block:: bash

    . venv/bin/activate  # "venv\Scripts\activate" on Windows
    mitmdump --version

Testing
-------

If you've followed the procedure above, you already have all the development
requirements installed, and you can run the basic test suite with tox_:

.. code-block:: bash

    tox -e py      # runs Python tests

Our CI system has additional tox environments that are run on every pull request and branch on GitHub.

For speedier testing, we recommend you run `pytest`_ directly on individual test files or folders:

.. code-block:: bash

    cd test/mitmproxy/addons
    pytest --cov mitmproxy.addons.anticache --cov-report term-missing --looponfail test_anticache.py

Pytest does not check the code style, so you want to run ``tox -e flake8`` again before committing.

Please ensure that all patches are accompanied by matching changes in the test
suite. The project tries to maintain 100% test coverage and enforces this strictly for some parts of the codebase.

Documentation
-------------

The following tools are required to build the mitmproxy docs:

- Hugo_ (the extended version ``hugo_extended`` is required)
- modd_

.. code-block:: bash

    cd docs
    modd


Code Style
----------

Keeping to a consistent code style throughout the project makes it easier to
contribute and collaborate. Please stick to the guidelines in
`PEP8`_ and the `Google Style Guide`_ unless there's a very
good reason not to.

This is automatically enforced on every PR. If we detect a linting error, the
PR checks will fail and block merging. You can run our lint checks yourself
with the following commands:

.. code-block:: bash

    tox -e flake8
    tox -e mypy    # checks static types


.. |mitmproxy_site| image:: https://shields.mitmproxy.org/badge/https%3A%2F%2F-mitmproxy.org-blue.svg
    :target: https://mitmproxy.org/
    :alt: mitmproxy.org

.. |mitmproxy_docs_stable| image:: https://shields.mitmproxy.org/badge/docs-stable-brightgreen.svg
    :target: https://docs.mitmproxy.org/stable/
    :alt: mitmproxy documentation stable

.. |mitmproxy_docs_master| image:: https://shields.mitmproxy.org/badge/docs-master-brightgreen.svg
    :target: https://docs.mitmproxy.org/master/
    :alt: mitmproxy documentation master

.. |mitmproxy_stackoverflow| image:: https://shields.mitmproxy.org/stackexchange/stackoverflow/t/mitmproxy?color=orange&label=stackoverflow%20questions
    :target: https://stackoverflow.com/questions/tagged/mitmproxy
    :alt: StackOverflow: mitmproxy

.. |slack| image:: https://shields.mitmproxy.org/badge/slack-mitmproxy-E01563.svg
    :target: http://slack.mitmproxy.org/
    :alt: Slack Developer Chat

.. |ci_status| image:: https://github.com/mitmproxy/mitmproxy/workflows/CI/badge.svg?branch=master
    :target: https://github.com/mitmproxy/mitmproxy/actions?query=branch%3Amaster
    :alt: Continuous Integration Status

.. |coverage| image:: https://shields.mitmproxy.org/codecov/c/github/mitmproxy/mitmproxy/master.svg?label=codecov
    :target: https://codecov.io/gh/mitmproxy/mitmproxy
    :alt: Coverage Status

.. |latest_release| image:: https://shields.mitmproxy.org/pypi/v/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Latest Version

.. |python_versions| image:: https://shields.mitmproxy.org/pypi/pyversions/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Supported Python versions

.. _virtualenv: https://virtualenv.pypa.io/
.. _`pytest`: http://pytest.org/
.. _tox: https://tox.readthedocs.io/
.. _Hugo: https://gohugo.io/
.. _modd: https://github.com/cortesi/modd
.. _PEP8: https://www.python.org/dev/peps/pep-0008
.. _`Google Style Guide`: https://google.github.io/styleguide/pyguide.html
.. _StackOverflow: https://stackoverflow.com/questions/tagged/mitmproxy
.. _`good first contributions`: https://github.com/mitmproxy/mitmproxy/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22
