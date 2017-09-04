.. _install:

Installation
============

Please follow the steps for your operating system.

Once installation is complete, you can run :ref:`mitmproxy`, :ref:`mitmdump` or
:ref:`mitmweb` from a terminal.


.. _install-macos:

Installation on macOS
---------------------

The recommended way to install mitmproxy on macOS is to use `Homebrew`_:

.. code:: bash

    brew install mitmproxy

Alternatively you can download our :ref:`binary-packages` from our `releases`_
page.


.. _install-linux:

Installation on Linux
---------------------

The recommended way to install mitmproxy on Linux is to download our
:ref:`binary-packages` from our `releases`_ page.

Some Linux distributions and their community provide mitmproxy packages via
their native package repositories (e.g., Arch Linux, Debian, Ubuntu, Kali Linux,
OpenSUSE, etc.). While we do encourage seeing mitmproxy in a great variety of
repositories and distributions, we are not maintaining or involved with their
downstream packaging efforts. If you are looking for the latest version or have
other problems, please contact the repository maintainers directly.


.. _install-windows:

Installation on Windows
-----------------------

The recommended way to install mitmproxy on Windows is to download our
:ref:`binary-packages` from our `releases`_ page.

After installation, you'll find shortcuts for :ref:`mitmweb` (the web-based
interface) and :ref:`mitmdump` in the start menu. Both executables are added to
your PATH and can be invoked from the command line.

.. note::
    The console interface is not supported on Windows, but you can
    use `mitmweb` (the web-based interface) and `mitmdump`.


.. _install-advanced:

Advanced Installation
---------------------

.. _binary-packages:

Self-contained Pre-built Binary Packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For some platforms we provide pre-built binary packages containing ready-to-run
executables. This includes a self-contained Python 3 environment, a recent
OpenSSL that support ALPN and HTTP/2, and other dependencies that would
otherwise we cumbersome to compile and install.

Please be advised that we do not updates these binaries after the initial
release. This means we do not include security-related updates of our
dependencies in already released mitmproxy versions. If there is a severe issue,
we might consider releasing a bugfix release of mitmproxy and corresponding
binary packages.

We only support the latest version of mitmproxy with bugfix and security updates
through regular minor releases.


.. _install-docker:

Docker Images
^^^^^^^^^^^^^

You can use the official mitmproxy images from `DockerHub`_. The same security
considerations apply as for our binary packages.


.. _install-linux-pip3:

Installation on Linux via pip3
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Please make sure to install Python 3.5 (or higher) and pip3 for your
distribtion. If your distribution does not provide a suitable Python version,
you can use `pyenv`_ to get a recent Python environment.

.. code:: bash

    sudo apt install python3-pip # Debian 8 or higher, Ubuntu 16.04 or higher
    sudo dnf install python3-pip # Fedora 24 or higher
    sudo pacman -S python-pip # Arch Linux

Please make sure to upgrade pip3 itself:

.. code:: bash

    sudo pip3 install -U pip

Now you can install mitmproxy via pip3:

.. code:: bash

    sudo pip3 install mitmproxy


.. _install-windows-pip3:

Installation on Windows via pip3
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
    The console interface is not supported on Windows, but you can
    use `mitmweb` (the web-based interface) and `mitmdump`.

First, install the latest version of Python 3.5 or higher from the `Python
website`_. During installation, make sure to select `Add Python to PATH`. There
are no other dependencies on Windows.

Now you can install mitmproxy via pip3:

.. code:: powershell

    pip3 install mitmproxy



.. _install-from-source:

Installation from Source Code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you would like to install mitmproxy directly from source code or the GitHub
master branch, please see the our README_ on GitHub.


.. _README: https://github.com/mitmproxy/mitmproxy/blob/master/README.rst
.. _releases: https://github.com/mitmproxy/mitmproxy/releases/latest
.. _mitmproxy.org: https://mitmproxy.org/
.. _`Python website`: https://www.python.org/downloads/windows/
.. _pip: https://pip.pypa.io/en/latest/installing.html
.. _pyenv: https://github.com/yyuu/pyenv
.. _DockerHub: https://hub.docker.com/r/mitmproxy/mitmproxy/
.. _Homebrew: https://brew.sh/
