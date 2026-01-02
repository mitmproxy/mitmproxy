# Quick Start

- Install mitmproxy as described in [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
- Run `node --version` to make sure that you have at least Node.js 24 or above.
- Run `cd ./web` to change to the directory with package.json.
- Run `npm install` to install dependencies.
- Run `uv run mitmweb`
- Run `npm start` in a separate window to start the Vite development server for the web interface.

## Testing

- Run `npm test` to run the test suite.

## Code formatting

- Run `npm run prettier` to format your code. You can also integrate prettier into your editor, see https://prettier.io/docs/en/editors.html

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

- You can debug application state using the
  [React DevTools](https://reactjs.org/blog/2019/08/15/new-react-devtools.html) and
  [Redux DevTools](https://github.com/reduxjs/redux-devtools) browser extensions.
