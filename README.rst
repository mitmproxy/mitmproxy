mitmproxy
^^^^^^^^^

|travis| |appveyor| |coverage| |latest_release| |python_versions|

This repository contains the **mitmproxy** and **pathod** projects.

``mitmproxy`` is an interactive, SSL-capable intercepting proxy with a console
interface.

``mitmdump`` is the command-line version of mitmproxy. Think tcpdump for HTTP.

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


Join our developer chat on Slack if you would like to hack on mitmproxy itself.

|slack|


Installation
------------

The installation instructions are `here <http://docs.mitmproxy.org/en/stable/install.html>`__.
If you want to contribute changes, keep on reading.


Hacking
-------

To get started hacking on mitmproxy, make sure you have Python_ 3.5.x or above with
virtualenv_ installed (you can find installation instructions for virtualenv
`here <http://virtualenv.readthedocs.org/en/latest/>`__). Then do the following:

.. code-block:: text

    git clone https://github.com/mitmproxy/mitmproxy.git
    cd mitmproxy
    ./dev.sh  # powershell .\dev.ps1 on Windows


The *dev* script will create a virtualenv environment in a directory called
"venv", and install all mandatory and optional dependencies into it. The
primary mitmproxy components - mitmproxy and pathod - are installed as
"editable", so any changes to the source in the repository will be reflected
live in the virtualenv.

To confirm that you're up and running, activate the virtualenv, and run the
mitmproxy test suite:

.. code-block:: text

    . venv/bin/activate  # venv\Scripts\activate on Windows
    py.test

Note that the main executables for the project - ``mitmdump``, ``mitmproxy``,
``mitmweb``, ``pathod``, and ``pathoc`` - are all created within the
virtualenv. After activating the virtualenv, they will be on your $PATH, and
you can run them like any other command:

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

You can also use `tox` to run the full suite of tests, including a quick test
to check documentation and code linting.

The following tox environments are relevant for local testing:

.. code-block:: text

    tox -e py35  # runs all tests with Python 3.5
    tox -e docs  # runs a does-it-compile check on the documentation
    tox -e lint  # runs the linter for coding style checks


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

Style
-----

Keeping to a consistent code style throughout the project makes it easier to
contribute and collaborate. Please stick to the guidelines in
`PEP8`_ and the `Google Style Guide`_ unless there's a very
good reason not to.

This is automatically enforced on every PR. If we detect a linting error, the
PR checks will fail and block merging. We are using this command to check for style compliance:

.. code-block:: text

    flake8 --jobs 8 --count mitmproxy pathod examples test


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

.. _Python: https://www.python.org/
.. _virtualenv: http://virtualenv.readthedocs.org/en/latest/
.. _autoenv: https://github.com/kennethreitz/autoenv
.. _.env: https://github.com/mitmproxy/mitmproxy/blob/master/.env
.. _Sphinx: http://sphinx-doc.org/
.. _sphinx-autobuild: https://pypi.python.org/pypi/sphinx-autobuild
.. _PEP8: https://www.python.org/dev/peps/pep-0008
.. _Google Style Guide: https://google.github.io/styleguide/pyguide.html
