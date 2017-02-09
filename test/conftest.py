import os
import pytest
import OpenSSL
import functools
from contextlib import contextmanager

import mitmproxy.net.tcp


requires_alpn = pytest.mark.skipif(
    not mitmproxy.net.tcp.HAS_ALPN,
    reason='requires OpenSSL with ALPN support')

skip_windows = pytest.mark.skipif(
    os.name == "nt",
    reason='Skipping due to Windows'
)

skip_not_windows = pytest.mark.skipif(
    os.name != "nt",
    reason='Skipping due to not Windows'
)

skip_appveyor = pytest.mark.skipif(
    "APPVEYOR" in os.environ,
    reason='Skipping due to Appveyor'
)


original_pytest_raises = pytest.raises


# TODO: remove this wrapper when pytest 3.1.0 is released
@contextmanager
@functools.wraps(original_pytest_raises)
def raises(exc, *args, **kwargs):
    with original_pytest_raises(exc, *args, **kwargs) as exc_info:
        yield
    if 'match' in kwargs:
        assert exc_info.match(kwargs['match'])


pytest.raises = raises


@pytest.fixture()
def disable_alpn(monkeypatch):
    monkeypatch.setattr(mitmproxy.net.tcp, 'HAS_ALPN', False)
    monkeypatch.setattr(OpenSSL.SSL._lib, 'Cryptography_HAS_ALPN', False)


enable_coverage = False
coverage_values = []
coverage_passed = False


def pytest_addoption(parser):
    parser.addoption('--full-cov',
                     action='append',
                     dest='full_cov',
                     default=[],
                     help="Require full test coverage of 100%% for this module/path/filename (multi-allowed). Default: none")

    parser.addoption('--no-full-cov',
                     action='append',
                     dest='no_full_cov',
                     default=[],
                     help="Exclude file from a parent 100%% coverage requirement (multi-allowed). Default: none")


def pytest_configure(config):
    global enable_coverage
    enable_coverage = (
        len(config.getoption('file_or_dir')) == 0 and
        len(config.getoption('full_cov')) > 0 and
        config.pluginmanager.getplugin("_cov") is not None and
        config.pluginmanager.getplugin("_cov").cov_controller is not None and
        config.pluginmanager.getplugin("_cov").cov_controller.cov is not None
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtestloop(session):
    global enable_coverage
    global coverage_values
    global coverage_passed

    if not enable_coverage:
        yield
        return

    cov = pytest.config.pluginmanager.getplugin("_cov").cov_controller.cov

    if os.name == 'nt':
        cov.exclude('pragma: windows no cover')

    yield

    coverage_values = dict([(name, 0) for name in pytest.config.option.full_cov])

    prefix = os.getcwd()
    excluded_files = [os.path.normpath(f) for f in pytest.config.option.no_full_cov]
    measured_files = [os.path.normpath(os.path.relpath(f, prefix)) for f in cov.get_data().measured_files()]
    measured_files = [f for f in measured_files if not any(f.startswith(excluded_f) for excluded_f in excluded_files)]

    for name in coverage_values.keys():
        files = [f for f in measured_files if f.startswith(os.path.normpath(name))]
        try:
            with open(os.devnull, 'w') as null:
                overall = cov.report(files, ignore_errors=True, file=null)
                singles = [(s, cov.report(s, ignore_errors=True, file=null)) for s in files]
                coverage_values[name] = (overall, singles)
        except:
            pass

    if any(v < 100 for v, _ in coverage_values.values()):
        # make sure we get the EXIT_TESTSFAILED exit code
        session.testsfailed += 1
    else:
        coverage_passed = True


def pytest_terminal_summary(terminalreporter, exitstatus):
    global enable_coverage
    global coverage_values
    global coverage_passed

    if not enable_coverage:
        return

    terminalreporter.write('\n')
    if not coverage_passed:
        markup = {'red': True, 'bold': True}
        msg = "FAIL: Full test coverage not reached!\n"
        terminalreporter.write(msg, **markup)

        for name in sorted(coverage_values.keys()):
            msg = 'Coverage for {}: {:.2f}%\n'.format(name, coverage_values[name][0])
            if coverage_values[name][0] < 100:
                markup = {'red': True, 'bold': True}
                for s, v in sorted(coverage_values[name][1]):
                    if v < 100:
                        msg += '  {}: {:.2f}%\n'.format(s, v)
            else:
                markup = {'green': True}
            terminalreporter.write(msg, **markup)
    else:
        markup = {'green': True}
        msg = 'SUCCESS: Full test coverage reached in modules and files:\n'
        msg += '{}\n\n'.format('\n'.join(pytest.config.option.full_cov))
        terminalreporter.write(msg, **markup)

    msg = '\nExcluded files:\n'
    for s in sorted(pytest.config.option.no_full_cov):
        msg += "  {}\n".format(s)
    terminalreporter.write(msg)
