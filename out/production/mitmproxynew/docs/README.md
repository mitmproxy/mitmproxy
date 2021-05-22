# Mitmproxy Documentation

This directory houses the mitmproxy documentation available at <https://docs.mitmproxy.org/>.

## Quick Start

 1. Install [hugo "extended"](https://gohugo.io/getting-started/installing/). 
 2. Windows users: Depending on your git settings, you may need to manually create a symlink from
 /docs/src/examples to /examples.
 3. Make sure the mitmproxy Python package is installed and the virtual python environment was activated. See [CONTRIBUTING.md](../CONTRIBUTING.md#development-setup) for details.
 4. Run `./build.py` to generate additional documentation source files.

Now you can run `hugo server -D` in ./src.

## Extended Install

This is required to modify CSS files.

 1. Install "extended" hugo version.

You can now run `modd` in this directory instead of running hugo directly.
