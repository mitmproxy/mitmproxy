# Mitmproxy Documentation

This directory houses the mitmproxy documentation available at <https://docs.mitmproxy.org/>.

## Quick Start

 1. Install [hugo](https://gohugo.io/).
 2. Windows users: Depending on your git settings, you may need to manually create a symlink from 
 /docs/src/examples to /examples.

Make sure mitmproxy python package is installed.

Run `./build-current` script in docs folder. If you skip this step, hugo will fail because files in ./src/generated are missing

Now you can run `hugo server -D` in ./src.


## Extended Install

This is required to modify CSS files.

 1. Install node, yarn, and [modd](https://github.com/cortesi/modd).
 2. Run `yarn` in this directory to get node-sass.

You can now run `modd` in this directory instead of running hugo directly.
