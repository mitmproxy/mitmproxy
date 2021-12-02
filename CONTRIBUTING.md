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

To get started hacking on mitmproxy, please install a recent version of Python (we require at least Python 3.8).
Then, do the following:

### Linux / macOS
#### 1. Verify that these commands work:
```bash
python3 --version
python3 -m pip --help
python3 -m venv --help
```

#### 2) Clone source and install dependencies:

```bash
git clone https://github.com/mitmproxy/mitmproxy.git
cd mitmproxy
python3 -m venv venv
venv/bin/pip install -e ".[dev]"
```

**NOTE**
If you encounter a pyOpenSSL similar looking error on macOS:

> `fatal error: 'openssl/opensslv.h' file not found`

You may need to run the following pip command on its own:

```bash
pip install pyopenssl --global-option=build_ext --global-option="-L/usr/local/opt/openssl/lib" --global-option="-I/usr/local/opt/openssl/include"
```

### Windows

#### 1) Verify that this command works:

```bash
python --version
```

#### 2) Clone source and install dependencies:

```shell
git clone https://github.com/mitmproxy/mitmproxy.git
cd mitmproxy
python -m venv venv
venv\Scripts\pip install -e .[dev]
```

## Editing the source

At this point you'd have a copy of the `mitmproxy` source in a directory with the same name, you should then create an isolated Python environment (a [virtualenv](https://virtualenv.pypa.io/)) into which all dependencies are installed.
Mitmproxy itself is installed as "editable", so any changes to the source in the repository will be reflected live in the virtualenv.

The main executables for the project – `mitmdump`, `mitmproxy`, and `mitmweb` – are all created within the virtualenv.
After activating the virtualenv, they will be on your $PATH, and you can run them like any other command:

### Linux / macOS

```shell
source venv/bin/activate
mitmdump --version
```

### Windows

```shell
venv\Scripts\activate
mitmdump --version
```

## Testing & Code Coverage

If you've followed the procedure above, you already have all the development requirements installed, and you can run the
basic test suite with [tox](https://tox.readthedocs.io/):

```shell
tox -e py      # runs Python tests
```

Our CI system has additional tox environments that are run on every pull request (see [tox.ini](./tox.ini)).

You can check the code coverage by running:

```bash
tox -e individual_coverage
```

For speedier testing, you can also run [pytest](http://pytest.org/) directly on individual test files or folders:

```shell
cd test/mitmproxy/addons
pytest --cov mitmproxy.addons.anticache --cov-report term-missing --looponfail test_anticache.py
```

Please ensure that all patches are accompanied by matching changes in the test suite. The project tries to maintain 100%
test coverage and enforces this strictly for some parts of the codebase.

### Code Style

Keeping to a consistent code style throughout the project makes it easier to contribute and collaborate.

We enforce the following check for all PRs:

```shell
tox -e flake8
```

If a linting error is detected, the automated pull request checks will fail and block merging.

## Documentation

Please check [docs/README.md](./docs/README.md) for instructions.

## Editor or IDE Setups

These are not required steps but rather short pointers and instructions to get started with hacking `mitmproxy` using popular text editors and IDEs. 

### VSCode 

  * [Homepage: Visual Studio Code](https://code.visualstudio.com)

> NOTE: These particular instructions were tested in macOS

  1. Install `debugpy` by running: `pip install debugpy`
  2. Follow the instructions of the `Development Setup` section in this document
  3. Locate where is the `mitmproxy` command installed, you can find this by running `which mitmproxy`. If you're using [pyenv](https://github.com/pyenv/pyenv#simple-python-version-management-pyenv) it will be located at `$HOME/.pyenv/versions/$(pyenv global)/bin/mitmproxy` (full executable path)
  4. Run the `mitmproxy` in debug mode by executing the following:
     
          python -m debugpy --listen 5678 /path/to/mitmproxy

    The mitmproxy TUI should open as regular, you can also use it to debug `mitmdump` or `mitmweb`

  5. Create a VSCode Launch process attach configuration:
      
          {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "connect": {
              "host": "localhost",
              "port": 5678
            },
            "pathMappings": [
              {
                "localRoot": "${workspaceFolder}",
                "remoteRoot": "."
              }
            ]  
          }

  6. Run the attach configuration (F5) after starting mitmproxy in debug mode, after the vscode debugger attaches
     you should be able to set break points and debug away.
