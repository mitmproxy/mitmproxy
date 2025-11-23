---
title: "Installation"
weight: 2
aliases:
  - /overview-installation/
---

# Installation

Please follow the steps for your operating system.

## macOS

The recommended way to install mitmproxy on macOS is to use
[Homebrew](https://brew.sh/):

```bash
brew install --cask mitmproxy
```

Alternatively, you can download standalone binaries on [mitmproxy.org](https://mitmproxy.org/).

## Linux

The recommended way to install mitmproxy on Linux is to download the
standalone binaries on [mitmproxy.org](https://mitmproxy.org/).

Some Linux distributions provide community-supported mitmproxy packages through
their native package repositories (e.g., Arch Linux, Debian, Ubuntu, Kali Linux,
OpenSUSE, etc.). We are not involved in the maintenance of downstream packaging
efforts, and they often lag behind the current mitmproxy release. Please contact
the repository maintainers directly for issues with native packages.

## Windows

To install mitmproxy on Windows, download the installer from [mitmproxy.org](https://mitmproxy.org/). 
We also provide standalone binaries, they take significantly longer to start
as some files need to be extracted to temporary directories first.
After installation, mitmproxy, mitmdump and mitmweb are also added to your PATH and can be invoked from the command line.

We highly recommend to [install Windows Terminal](https://aka.ms/terminal) to improve the rendering of the console interface.

All the mitmproxy tools are also supported under
[WSL (Windows Subsystem for Linux)](https://docs.microsoft.com/en-us/windows/wsl/about). After
[installing WSL](https://docs.microsoft.com/en-us/windows/wsl/install-win10), follow the mitmproxy installation
instructions for Linux.

## Advanced Installation

### Development Setup

If you would like to install mitmproxy directly from source code or the
GitHub main branch, please see the our
[CONTRIBUTING.md](https://github.com/mitmproxy/mitmproxy/blob/main/CONTRIBUTING.md)
on GitHub.

### Installation from the Python Package Index (PyPI)

If your mitmproxy addons require the installation of additional Python packages,
you can install mitmproxy from [PyPI](https://pypi.org/project/mitmproxy/).

While there are plenty of options around[^1], we recommend the installation using uv:

[^1]: If you are familiar with the Python ecosystem, you may know that there are a million ways to install Python
    packages. Most of them (pip, virtualenv, pipenv, etc.) should just work, but we don't have the capacity to
    provide support for it.

1. Install [uv](https://docs.astral.sh/uv/).
2. `uv tool install mitmproxy`.

To install additional Python packages, run `uv tool install --with <your-package-name> mitmproxy`.

### Docker Images

You can use the official mitmproxy images from
[DockerHub](https://hub.docker.com/r/mitmproxy/mitmproxy/).

### Security Considerations for Binary Packages

Our pre-compiled binary packages and Docker images include a self-contained
Python 3 environment, a recent version of OpenSSL, and other dependencies
that would otherwise be cumbersome to compile and install.

Dependencies in the binary packages are frozen on release, and can't be updated
in situ. This means that we necessarily capture any bugs or security issues that
may be present. We don't generally release new binary packages simply to update
dependencies (though we may do so if we become aware of a really serious issue).
If you use our binary packages, please make sure you update regularly to ensure
that everything remains current.

As a general principle, mitmproxy does not "phone home" and consequently will not do any update checks.
