# Quick Start

- Install mitmproxy as described in [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
- Run `node --version` to make sure that you have at least Node.js 14 or above. If you are on **Ubuntu <= 20.04**, you
  need to
  [upgrade](https://github.com/nodesource/distributions/blob/master/README.md#installation-instructions).
- Run `cd mitmproxy/web` to change to the directory with package.json
- Run `npm install` to install dependencies
- Run `npm start` to start live-compilation
- Run `mitmweb` after activating your Python virtualenv (see [`../CONTRIBUTING.md`](../CONTRIBUTING.md)).

## Testing

- Run `npm test` to run the test suite.

## Architecture

There are two components:

- Server: [`mitmproxy/tools/web`](../mitmproxy/tools/web)

- Client: `web`

## Contributing

We very much appreciate any (small) improvements to mitmweb. Please do *not* include the compiled assets in
[`mitmproxy/tools/web/static`](https://github.com/mitmproxy/mitmproxy/tree/main/mitmproxy/tools/web/static)
in your pull request. Refreshing them on every commit would massively increase repository size. We will update these
files before every release.

## Developer Tools

- `npm start` supports live-reloading if you install a matching
  [browser extension](http://livereload.com/extensions/).
- You can debug application state using the
  [React DevTools](https://reactjs.org/blog/2019/08/15/new-react-devtools.html) and
  [Redux DevTools](https://github.com/reduxjs/redux-devtools) browser extensions.
