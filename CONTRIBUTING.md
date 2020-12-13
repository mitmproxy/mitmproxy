# Contributing

As an open source project, mitmproxy welcomes contributions of all forms. If you would like to bring the project
forward, please consider contributing in the following areas:

- **Maintenance:** We are *incredibly* thankful for individuals who are stepping up and helping with maintenance. This
  includes (but is not limited to) triaging issues, reviewing pull requests and picking up stale ones, helping out other
  users on [StackOverflow](https://stackoverflow.com/questions/tagged/mitmproxy), creating minimal, complete and
  verifiable examples or test cases for existing bug reports, updating documentation, or fixing minor bugs that have
  recently been reported.
- **Code Contributions:** We actively mark issues that we consider are [good first contributions](
  https://github.com/mitmproxy/mitmproxy/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22). If you intend to work
  on a larger contribution to the project, please come talk to us first.

## Development Setup

To get started hacking on mitmproxy, please install a recent version of Python (we require at least Python 3.8). The
following commands should work on your system:

```shell
python3 --version
python3 -m pip --help
python3 -m venv --help
```

If all of this run successfully, do the following:

```shell
git clone https://github.com/mitmproxy/mitmproxy.git
cd mitmproxy
./dev.sh  # "powershell .\dev.ps1" on Windows
```

The *dev* script will create a [virtualenv](https://virtualenv.pypa.io/) environment in a directory called "venv" and
install all mandatory and optional dependencies into it. The primary mitmproxy components are installed as "editable",
so any changes to the source in the repository will be reflected live in the virtualenv.

The main executables for the project - `mitmdump`, `mitmproxy`, and `mitmweb` - are all created within the virtualenv.
After activating the virtualenv, they will be on your $PATH, and you can run them like any other command:

```shell
. venv/bin/activate  # "venv\Scripts\activate" on Windows
mitmdump --version
```

## Testing

If you've followed the procedure above, you already have all the development requirements installed, and you can run the
basic test suite with [tox](https://tox.readthedocs.io/):

```shell
tox -e py      # runs Python tests
```

Our CI system has additional tox environments that are run on every pull request and branch on GitHub.

For speedier testing, we recommend you run [pytest](http://pytest.org/) directly on individual test files or folders:

```shell
cd test/mitmproxy/addons
pytest --cov mitmproxy.addons.anticache --cov-report term-missing --looponfail test_anticache.py
```

Pytest does not check the code style, so you want to run `tox -e flake8` and `tox -e mypy` again before committing.

Please ensure that all patches are accompanied by matching changes in the test suite. The project tries to maintain 100%
test coverage and enforces this strictly for some parts of the codebase.

## Documentation

The following tools are required to build the mitmproxy docs:

- [Hugo](https://gohugo.io/) (the extended version `hugo_extended` is required)
- [modd](https://github.com/cortesi/modd)

```shell
cd docs
modd
```

## Code Style

Keeping to a consistent code style throughout the project makes it easier to contribute and collaborate. Please stick to
the guidelines in [PEP8](https://www.python.org/dev/peps/pep-0008) unless there's a good reason not to.

This is automatically enforced on every PR. If we detect a linting error, the PR checks will fail and block merging. You
can run our lint checks yourself with the following commands:

```shell
tox -e flake8
tox -e mypy    # checks static types
```
