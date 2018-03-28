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

The documentation for mitmproxy is available on our website:

|mitmproxy_docs_stable| |mitmproxy_docs_master| 


Join our discussion forum on Discourse to ask questions, help
each other solve problems, and come up with new ideas for the project.

|mitmproxy_discourse|


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

- **Maintenance:** We are *incredibly* thankful for individuals who are stepping up and helping with maintenance. This includes (but is not limited to) triaging issues, reviewing pull requests and picking up stale ones, helping out other users in our forums_, creating minimal, complete and verifiable examples or test cases for existing bug reports, updating documentation, or fixing minor bugs that have recently been reported.
- **Code Contributions:** We actively mark issues that we consider are `good first contributions`_. If you intend to work on a larger contribution to the project, please come talk to us first.

Development Setup
-----------------

To get started hacking on mitmproxy, please follow the `advanced installation`_ steps to install mitmproxy from source, but stop right before running ``pip3 install mitmproxy``. Instead, do the following:

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
requirements installed, and you can run the full test suite (including tests for code style and documentation) with tox_:

.. code-block:: bash

    tox

To run complete tests with a full coverage report, you can use the following command:

.. code-block:: bash

    tox -- --verbose --cov-report=term

For speedier testing, we recommend you run `pytest`_ directly on individual test files or folders:

.. code-block:: bash

    cd test/mitmproxy/addons
    pytest --cov mitmproxy.addons.anticache --looponfail test_anticache.py

As pytest does not check the code style, you probably want to run ``tox -e lint`` before committing your changes.

Please ensure that all patches are accompanied by matching changes in the test
suite. The project tries to maintain 100% test coverage and enforces this strictly for some parts of the codebase.

Documentation
-------------

The following tools are required to build the mitmproxy docs:

- Hugo_
- modd_
- yarn_

.. code-block:: bash

    cd docs
    yarn
    modd


Code Style
----------

Keeping to a consistent code style throughout the project makes it easier to
contribute and collaborate. Please stick to the guidelines in
`PEP8`_ and the `Google Style Guide`_ unless there's a very
good reason not to.

This is automatically enforced on every PR. If we detect a linting error, the
PR checks will fail and block merging. You can run our lint checks yourself
with the following command:

.. code-block:: bash

    tox -e lint


.. |mitmproxy_site| image:: https://shields.mitmproxy.org/api/https%3A%2F%2F-mitmproxy.org-blue.svg
    :target: https://mitmproxy.org/
    :alt: mitmproxy.org

.. |mitmproxy_docs_stable| image:: https://shields.mitmproxy.org/api/docs-stable-brightgreen.svg
    :target: https://docs.mitmproxy.org/stable/
    :alt: mitmproxy documentation stable
    
.. |mitmproxy_docs_master| image:: https://shields.mitmproxy.org/api/docs-master-brightgreen.svg
    :target: https://docs.mitmproxy.org/master/
    :alt: mitmproxy documentation master

.. |mitmproxy_discourse| image:: https://shields.mitmproxy.org/api/https%3A%2F%2F-discourse.mitmproxy.org-orange.svg
    :target: https://discourse.mitmproxy.org
    :alt: Discourse: mitmproxy

.. |slack| image:: http://slack.mitmproxy.org/badge.svg
    :target: http://slack.mitmproxy.org/
    :alt: Slack Developer Chat

.. |travis| image:: https://shields.mitmproxy.org/travis/mitmproxy/mitmproxy/master.svg?label=travis%20ci
    :target: https://travis-ci.org/mitmproxy/mitmproxy
    :alt: Travis Build Status

.. |appveyor| image:: https://shields.mitmproxy.org/appveyor/ci/mhils/mitmproxy/master.svg?label=appveyor%20ci
    :target: https://ci.appveyor.com/project/mhils/mitmproxy
    :alt: Appveyor Build Status

.. |coverage| image:: https://shields.mitmproxy.org/codecov/c/github/mitmproxy/mitmproxy/master.svg?label=codecov
    :target: https://codecov.io/gh/mitmproxy/mitmproxy
    :alt: Coverage Status

.. |latest_release| image:: https://shields.mitmproxy.org/pypi/v/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Latest Version

.. |python_versions| image:: https://shields.mitmproxy.org/pypi/pyversions/mitmproxy.svg
    :target: https://pypi.python.org/pypi/mitmproxy
    :alt: Supported Python versions

.. _`advanced installation`: https://docs.mitmproxy.org/stable/overview-installation/#advanced-installation
.. _virtualenv: https://virtualenv.pypa.io/
.. _`pytest`: http://pytest.org/
.. _tox: https://tox.readthedocs.io/
.. _Hugo: https://gohugo.io/
.. _modd: https://github.com/cortesi/modd
.. _yarn: https://yarnpkg.com/en/
.. _PEP8: https://www.python.org/dev/peps/pep-0008
.. _`Google Style Guide`: https://google.github.io/styleguide/pyguide.html
.. _forums: https://discourse.mitmproxy.org/
.. _`good first contributions`: https://github.com/mitmproxy/mitmproxy/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22
