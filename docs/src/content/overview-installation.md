---
title: "Installation"
menu: "overview"
menu:
    overview:
        weight: 2
---

# Installation

Please follow the steps for your operating system.

## macOS

The recommended way to install mitmproxy on macOS is to use
[Homebrew](https://brew.sh/):

{{< highlight bash  >}}
brew install mitmproxy
{{< / highlight >}}

Alternatively you can download the binary-packages from our
[releases](https://github.com/mitmproxy/mitmproxy/releases/latest) page.

## Linux

The recommended way to install mitmproxy on Linux is to download the
binary-packages from our
[releases](https://github.com/mitmproxy/mitmproxy/releases/latest) page.

Some Linux distributions provide community-supported mitmproxy packages through
their native package repositories (e.g., Arch Linux, Debian, Ubuntu, Kali
Linux, OpenSUSE, etc...). We are not involved in the maintenance of
downstream packaging efforts, and they often lag behind the current
mitmproxy release. Please contact the repository maintainers directly for
issues with native packages.

## Windows


All the mitmproxy tools are fully supported under [WSL (Windows Subsystem
for Linux)](https://docs.microsoft.com/en-us/windows/wsl/about). We
recommend to  [install
WSL](https://docs.microsoft.com/en-us/windows/wsl/install-win10), and then
follow the mitmproxy installation instructions for Linux.

We also distribute native Windows packages for all tools other than the
mitmproxy console app, which only works under WSL. To install mitmproxy on Windows,
download the binary packages from our
[releases](https://github.com/mitmproxy/mitmproxy/releases/latest) page. 

After installation, you'll find shortcuts for mitmweb and mitmdump in the start
menu. Both executables are added to your PATH and can be invoked from the
command line.


# Advanced Installation

## Self-contained Pre-built Binary Packages

For some platforms we provide pre-built binary packages containing ready-to-run
executables. This includes a self-contained Python 3 environment, a recent
OpenSSL that support ALPN and HTTP/2, and other dependencies that would
otherwise be cumbersome to compile and install.

Dependencies in the binary packages are frozen on release, and can't be updated
in situ. This means that we necessarily capture any bugs or security issues that
may be present. We don't generally release new binary packages simply to update
dependencies (though we may do so if we become aware of a really serious issue).
If you use our binary packages, please make sure you update regularly to ensure
that everything remains current.


## Docker Images

You can use the official mitmproxy images from
[DockerHub](https://hub.docker.com/r/mitmproxy/mitmproxy/). The same
security considerations apply as for our binary packages.

## Installation on Linux within a virtual environment

Please make sure to install Python 3.6 (or higher) for your distribution.
If your distribution does not provide a suitable Python version, you can
also use [pyenv](https://github.com/yyuu/pyenv) to get a recent Python
environment.

{{< highlight bash  >}}
sudo apt install python3 # Debian 10 or higher, Ubuntu 17.10 or higher
sudo dnf install python3 # Fedora 26 or higher
sudo pacman -S python # Arch Linux
{{< / highlight >}}

Create a virtual environment and activate it:

{{< highlight bash >}}
python3 -m venv mitm_env
source mitm_env/bin/activate
pip install mitmproxy
{{</ highlight >}}

You can now run the mitmproxy tools with the relevant commands as your
`PATH` environment will be updated upon virtual environment activation.

Whenever you want to run mitmproxy, either:
- activate the environment again (`source mitm_env/bin/activate`).
- add `mitm_env/bin` folder to your `$PATH` environment variable.
- run mitmproxy with its full path.

The transparent mode requires to be run with root privileges, the
recommended way to do that is to run with the full path:

{{< highlight bash >}}
# regular virtual environment
sudo mitm_env/bin/mitmproxy [options]

# with pyenv
sudo $HOME/.pyenv/versions/mitmproxy/bin/mitmproxy
{{</ highlight >}}

Don't run `pip` with sudo or in root as it might break stuff in your
system (overwriting distribution-maintained files, and such)

## Installation on Windows via pip3

First, install the latest version of Python 3.6 or higher from the
[Python website](https://www.python.org/downloads/windows/). During
installation, make sure to select Add Python to PATH. There are no other
dependencies on Windows.

Now you can install mitmproxy via pip3:

{{< highlight bash  >}}
pip3 install mitmproxy
{{< / highlight >}}

## Installation from Source

Download the [release
package](https://github.com/mitmproxy/mitmproxy/releases).

{{< highlight bash  >}}
tar xvzf mitmproxy-[VERSION].tar.gz
cd mitmproxy-[VERSION]
pip install .
{{< / highlight >}}

