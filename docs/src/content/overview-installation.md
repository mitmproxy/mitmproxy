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
their native package repositories (e.g., Arch Linux, Debian, Ubuntu, Kali Linux,
OpenSUSE, etc.). We are not involved in the maintenance of downstream packaging
efforts, and they often lag behind the current mitmproxy release. Please contact
the repository maintainers directly for issues with native packages.

## Windows

The recommended way to install mitmproxy on Windows is to download our
binary-packages from our
[releases](https://github.com/mitmproxy/mitmproxy/releases/latest) page.

FIXME: WSL

After installation, you'll find shortcuts for mitmweb and mitmdump in the start
menu. Both executables are added to your PATH and can be invoked from the
command line. The console interface is not supported on native Windows.


# Advanced Installation

## Self-contained Pre-built Binary Packages

For some platforms we provide pre-built binary packages containing
ready-to-run executables. This includes a self-contained Python 3
environment, a recent OpenSSL that support ALPN and HTTP/2, and other
dependencies that would otherwise we cumbersome to compile and install.

Please be advised that we do not update these binaries after the initial
release. This means we do not include security-related updates of our
dependencies in already released mitmproxy versions. If there is a
severe issue, we might consider releasing a bugfix release of mitmproxy
and corresponding binary packages.

We only support the latest version of mitmproxy with bugfix and security
updates through regular minor releases.

## Docker Images

You can use the official mitmproxy images from
[DockerHub](https://hub.docker.com/r/mitmproxy/mitmproxy/). The same
security considerations apply as for our binary packages.

## Installation on Linux via pip3

Please make sure to install Python 3.5 (or higher) and pip3 for your
distribution. If your distribution does not provide a suitable Python
version, you can use [pyenv](https://github.com/yyuu/pyenv) to get a
recent Python environment.

{{< highlight bash  >}}
sudo apt install python3-pip # Debian 8 or higher, Ubuntu 16.04 or higher
sudo dnf install python3-pip # Fedora 24 or higher
sudo pacman -S python-pip # Arch Linux
{{< / highlight >}}

Please make sure to upgrade pip3 itself:

{{< highlight bash  >}}
sudo pip3 install -U pip
{{< / highlight >}}

Now you can install mitmproxy via pip3:

{{< highlight bash  >}}
sudo pip3 install mitmproxy
{{< / highlight >}}

## Installation on Windows via pip3

First, install the latest version of Python 3.5 or higher from the
[Python website](https://www.python.org/downloads/windows/). During
installation, make sure to select Add Python to PATH. There are no other
dependencies on Windows.

Now you can install mitmproxy via pip3:

{{< highlight bash  >}}
pip3 install mitmproxy
{{< / highlight >}}

## Installation from Source

If you would like to install mitmproxy directly from source code or the
GitHub master branch, please see the our
[README](https://github.com/mitmproxy/mitmproxy/blob/master/README.rst)
on GitHub.
