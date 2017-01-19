.. _install:

Installation
============

Please follow the steps for your operating system.

Once installation is complete, you can run :ref:`mitmproxy`, :ref:`mitmdump` or
:ref:`mitmweb` from a terminal.


.. _install-macos:

Installation on macOS
---------------------

You can use Homebrew to install everything:

.. code:: bash

    brew install mitmproxy

Or you can download the pre-built binary packages from `mitmproxy.org`_.


.. _install-windows:

Installation on Windows
-----------------------

The recommended way to install mitmproxy on Windows is to use the installer
provided at `mitmproxy.org`_. After installation, you'll find shortcuts for
:ref:`mitmweb` (the web-based interface) and :ref:`mitmdump` in the start menu.
Both executables are  added to your PATH and can be invoked from the command
line.

.. note::
    Mitmproxy's console interface is not supported on Windows, but you can use
    mitmweb (the web-based interface) and mitmdump.

.. _install-linux:

Installation on Linux
---------------------

The recommended way to run mitmproxy on Linux is to use the pre-built binaries
provided at `mitmproxy.org`_.

Our pre-built binaries provide you with the latest version of mitmproxy, a
self-contained Python 3.5 environment and a recent version of OpenSSL that
supports HTTP/2. Of course, you can also install mitmproxy from source if you
prefer that (see :ref:`install-advanced`).

.. _install-advanced:

Advanced Installation
---------------------

.. _install-docker:

Docker Images
^^^^^^^^^^^^^

You can also use the official mitmproxy images from `DockerHub`_. That being
said, our portable binaries are just as easy to install and even easier to use. 😊


.. _install-arch:

Installation on Arch Linux
^^^^^^^^^^^^^^^^^^^^^^^^^^

mitmproxy has been added into the [community] repository. Use pacman to install it:

>>> sudo pacman -S mitmproxy


.. _install-source-ubuntu:

Installation from Source on Ubuntu
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ubuntu comes with Python but we need to install pip3, python3-dev and several
libraries. This was tested on a fully patched installation of Ubuntu 16.04.

.. code:: bash

   sudo apt-get install python3-pip python3-dev libffi-dev libssl-dev libtiff5-dev libjpeg8-dev zlib1g-dev libwebp-dev
   sudo pip3 install mitmproxy  # or pip3 install --user mitmproxy

On older Ubuntu versions, e.g., **12.04** and **14.04**, you may need to install
a newer version of Python. mitmproxy requires Python 3.5 or higher. Please take
a look at pyenv_. Make sure to have an up-to-date version of pip by running
``pip3 install -U pip``.


.. _install-source-fedora:

Installation from Source on Fedora
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Fedora comes with Python but we need to install pip3, python3-dev and several
libraries. This was tested on a fully patched installation of Fedora 24.

.. code:: bash

   sudo dnf install make gcc redhat-rpm-config python3-pip python3-devel libffi-devel openssl-devel libtiff-devel libjpeg-devel zlib-devel libwebp-devel openjpeg2-devel
   sudo pip3 install mitmproxy  # or pip3 install --user mitmproxy

Make sure to have an up-to-date version of pip by running ``pip3 install -U pip``.



.. _install-source-windows:

🐱💻 Installation from Source on Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
    Mitmproxy's console interface is not supported on Windows, but you can use
    mitmweb (the web-based interface) and mitmdump.

First, install the latest version of Python 3.5 or later from the `Python
website`_. During installation, make sure to select `Add Python to PATH`.

Mitmproxy has no other dependencies on Windows. You can now install mitmproxy by running

.. code:: powershell

    pip3 install mitmproxy



.. _install-dev-version:

Latest Development Version
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you would like to install mitmproxy directly from the master branch on GitHub
or would like to get set up to contribute to the project, install the
dependencies as you would for a regular installation from source. Then see the
Hacking_ section of the README on GitHub. You can check your system information
by running: ``mitmproxy --version``


.. _Hacking: https://github.com/mitmproxy/mitmproxy/blob/master/README.rst#hacking
.. _mitmproxy.org: https://mitmproxy.org/
.. _`Python website`: https://www.python.org/downloads/windows/
.. _pip: https://pip.pypa.io/en/latest/installing.html
.. _pyenv: https://github.com/yyuu/pyenv
.. _DockerHub: https://hub.docker.com/r/mitmproxy/mitmproxy/
