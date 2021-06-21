# Quick Start

**Be sure to follow the Development Setup instructions found in the README.md,
and activate your virtualenv environment before proceeding.**

- Make sure that you have at least Node.js 14 or above: `node --version`
- Run `npm install` to install dependencies
- Run `npm start` to start live-compilation.
- Run `mitmweb` and open http://localhost:8081/

## Testing

- Run `npm test` to run the test suite.


## Advanced Tools

- `npm start` supports live-reloading if you install a matching
  [browser extension](http://livereload.com/extensions/).
- You can debug application state using the
  [React DevTools](https://reactjs.org/blog/2019/08/15/new-react-devtools.html) and
  [Redux DevTools](https://github.com/reduxjs/redux-devtools) browser extensions.

## Architecture

There are two components:

- Server: [`mitmproxy/tools/web`](../mitmproxy/tools/web)

- Client: `web`
