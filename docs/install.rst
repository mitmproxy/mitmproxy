.. _install:

Installation
============

.. _install-ubuntu:

Installation On Ubuntu
----------------------

Ubuntu comes with Python but we need to install pip, python-dev and several libraries.
This was tested on a fully patched installation of Ubuntu 16.04.

.. code:: bash

   sudo apt-get install python3-pip python3-dev libffi-dev libssl-dev libtiff5-dev libjpeg8-dev zlib1g-dev libwebp-dev
   sudo pip3 install mitmproxy  # or pip install --user mitmproxy

On older Ubuntu versions, e.g., **12.04** and **14.04**, you may need to install a newer version of Python.
mitmproxy requires Python 3.5 or higher. Please take a look at pyenv_.
Make sure to have an up-to-date version of pip by running ``pip3 install -U pip``.

Once installation is complete you can run :ref:`mitmproxy` or :ref:`mitmdump` from a terminal.


.. _install-fedora:

Installation On Fedora
----------------------

Fedora comes with Python but we need to install pip, python-dev and several libraries.
This was tested on a fully patched installation of Fedora 24.

.. code:: bash

   sudo dnf install make gcc redhat-rpm-config python3-pip python3-devel libffi-devel openssl-devel libtiff-devel libjpeg-devel zlib-devel libwebp-devel openjpeg2-devel
   sudo pip3 install mitmproxy  # or pip install --user mitmproxy

Make sure to have an up-to-date version of pip by running ``pip3 install -U pip``.

Once installation is complete you can run :ref:`mitmproxy` or :ref:`mitmdump` from a terminal.



.. _install-arch:

Installation On Arch Linux
--------------------------

mitmproxy has been added into the [community] repository. Use pacman to install it:

>>> sudo pacman -S mitmproxy

Once installation is complete you can run :ref:`mitmproxy` or :ref:`mitmdump` from a terminal.


.. _install-macos:

Installation On macOS
------------------------

You can use Homebrew to install everything:
.. code:: bash
    brew install mitmproxy

Or you can download the pre-built binary packages from `mitmproxy.org`_.

Once installation is complete you can run :ref:`mitmproxy` or :ref:`mitmdump` from a terminal.



.. _install-windows:

Installation On Windows
-----------------------

.. note::
    Please note that mitmdump is the only component of mitmproxy that is supported on Windows at
    the moment.

    **There is no interactive user interface on Windows.**


First, install the latest version of Python 3.5 from the `Python website`_.
If you already have an older version of Python 3.5 installed, make sure to install pip_
(pip is included in Python by default). If pip aborts with an error, make sure you are using the current version of pip.

.. code:: powershell
    python -m pip install --upgrade pip

Next, add Python and the Python Scripts directory to your **PATH** variable.
You can do this easily by running the following in powershell:

.. code:: powershell
    [Environment]::SetEnvironmentVariable("Path", "$env:Path;C:\Python27;C:\Python27\Scripts", "User")

Now, you can install mitmproxy by running

.. code:: powershell
    pip install mitmproxy

Once the installation is complete, you can run :ref:`mitmdump` from a command prompt.


.. _install-source:

Installation From Source
------------------------

If you would like to install mitmproxy directly from the master branch on GitHub or would like to
get set up to contribute to the project, install the dependencies as you would for a regular
mitmproxy installation. Then see the Hacking_ section of the README on GitHub.
You can check your system information by running: ``mitmproxy --sysinfo``


.. _Hacking: https://github.com/mitmproxy/mitmproxy/blob/master/README.rst#hacking
.. _mitmproxy.org: https://mitmproxy.org/
.. _`Python website`: https://www.python.org/downloads/windows/
.. _pip: https://pip.pypa.io/en/latest/installing.html
.. _pyenv: https://github.com/yyuu/pyenv
