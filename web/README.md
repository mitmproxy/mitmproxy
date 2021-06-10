# Quick Start

**Be sure to follow the Development Setup instructions found in the README.md,
and activate your virtualenv environment before proceeding.**

- Run `yarn` to install dependencies
- Run `yarn run gulp` to start live-compilation.
- Run `mitmweb` and open http://localhost:8081/

## Testing

- Run `yarn test` to run the test suite.


## Advanced Tools

- `yarn run gulp` supports live-reloading if you install a matching
  [browser extension](http://livereload.com/extensions/).
- You can debug application state using the [Redux DevTools](https://github.com/reduxjs/redux-devtools).

## Architecture

There are two components:

- Server: [`mitmproxy/tools/web`](../mitmproxy/tools/web)

- Client: `web`
