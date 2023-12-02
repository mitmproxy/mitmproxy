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

To get started hacking on mitmproxy, please install the latest version of Python and do the following:

##### Linux / macOS

```shell
# 1) Verify that these commands work:
python3 --version
python3 -m pip --help
python3 -m venv --help
# 2) Install:
git clone https://github.com/mitmproxy/mitmproxy.git
cd mitmproxy
python3 -m venv venv
venv/bin/pip install -e ".[dev]"
```

##### Windows

```shell
# 1) Verify that this command works:
python --version
# 2) Install:
git clone https://github.com/mitmproxy/mitmproxy.git
cd mitmproxy
python -m venv venv
venv\Scripts\pip install -e .[dev]
```

This will clone mitmproxy's source code into a directory with the same name,
and then create an isolated Python environment (a [virtualenv](https://virtualenv.pypa.io/)) into which all dependencies are installed.
Mitmproxy itself is installed as "editable", so any changes to the source in the repository will be reflected live in the virtualenv.

The main executables for the project – `mitmdump`, `mitmproxy`, and `mitmweb` – are all created within the virtualenv.
After activating the virtualenv, they will be on your $PATH, and you can run them like any other command:

##### Linux / macOS

```shell
source venv/bin/activate
mitmdump --version
```

##### Windows

```shell
venv\Scripts\activate
mitmdump --version
```

## Testing

If you've followed the procedure above, you already have all the development requirements installed, and you can run the
basic test suite with [tox](https://tox.readthedocs.io/):

```shell
tox -e py      # runs Python tests
```

Our CI system has additional tox environments that are run on every pull request (see [tox.ini](./tox.ini)).

For speedier testing, you can also run [pytest](http://pytest.org/) directly on individual test files or folders:

```shell
cd test/mitmproxy/addons
pytest --looponfail test_anticache.py
```

Please ensure that all patches are accompanied by matching changes in the test suite. The project tries to maintain 100%
test coverage and enforces this strictly for some parts of the codebase.

### Code Style

Keeping to a consistent code style throughout the project makes it easier to contribute and collaborate.

We enforce the following check for all PRs:

```shell
tox -e lint
```

If a linting error is detected, the automated pull request checks will fail and block merging.

## Documentation

Please check [docs/README.md](./docs/README.md) for instructions.
