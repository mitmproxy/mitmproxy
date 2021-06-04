# Mitmproxy Documentation

This directory houses the mitmproxy documentation available at <https://docs.mitmproxy.org/>.

## Prerequisites

 1. Install [hugo "extended"](https://gohugo.io/getting-started/installing/). 
 2. Windows users: Depending on your git settings, you may need to manually create a symlink from `/docs/src/examples` to `/examples`.

## Editing docs locally

 1. Make sure the mitmproxy Python package is installed and the virtual python environment was activated. See [CONTRIBUTING.md](../CONTRIBUTING.md#development-setup) for details.
 2. Run `./build.py` to generate additional documentation source files.
 3. Now you can change your working directory to `./src` and run `hugo server -D`.
