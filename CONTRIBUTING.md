# Contributing

As an open source project, mitmproxy welcomes contributions of all forms. If you would like to bring the project
forward, please consider contributing in the following areas:

- **Maintenance:** We are *incredibly* thankful for individuals who are stepping up and helping with maintenance. This
  includes (but is not limited to) triaging issues, reviewing pull requests and picking up stale ones, helping out other
  users on [GitHub Discussions](https://github.com/mitmproxy/mitmproxy/discussions), creating minimal, complete and
  verifiable examples or test cases for existing bug reports, updating documentation, or fixing minor bugs that have
  recently been reported.
- **Code Contributions:** We actively mark issues that we consider are [good first contributions](
  https://github.com/mitmproxy/mitmproxy/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22). If you intend to work
  on a larger contribution to the project, please come talk to us first.

## Development Setup

To get started hacking on mitmproxy, please install the latest version of [uv] and do the following:

[uv]: https://docs.astral.sh/uv/

```shell
git clone https://github.com/mitmproxy/mitmproxy.git
cd mitmproxy
uv run mitmproxy --version
```

`uv run` will transparently create a virtual Python environment in `mitmproxy/.venv`, 
and install mitmproxy with all dependencies into it.

To run commands from the Python environment, you can either prefix them with `uv run`, or activate the virtualenv
 and then use the commands directly:

##### Linux / macOS

```shell
source .venv/bin/activate
mitmdump --version
```

##### Windows

```shell
.venv\Scripts\activate
mitmdump --version
```

## Testing

If you've followed the procedure above, you already have all the development requirements installed, and you can run the
basic test suite with [tox](https://tox.readthedocs.io/):

```shell
uv run tox
```

For speedier testing, you can also run [pytest](http://pytest.org/) directly on individual test files or folders:

```shell
cd test/mitmproxy/addons
uv run pytest --cov mitmproxy.addons.anticache --cov-report term-missing --looponfail test_anticache.py
```

Please ensure that all patches are accompanied by matching changes in the test suite. The project tries to maintain 100%
test coverage and enforces this strictly for some parts of the codebase.
Our CI system has additional tox environments that are run on every pull request (see [pyproject.toml](./pyproject.toml)).


### Code Style

Keeping to a consistent code style throughout the project makes it easier to contribute and collaborate.

We enforce the following check for all PRs:

```shell
uv run tox -e lint
```

If a linting error is detected, the automated pull request checks will fail and block merging.

## Documentation

Please check [docs/README.md](./docs/README.md) for instructions.
