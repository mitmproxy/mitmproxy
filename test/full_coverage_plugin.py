import os
import configparser
import pytest
import sys

here = os.path.abspath(os.path.dirname(__file__))


enable_coverage = False
coverage_values = []
coverage_passed = True
no_full_cov = []


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
    global no_full_cov

    enable_coverage = (
        config.getoption('file_or_dir') and len(config.getoption('file_or_dir')) == 0 and
        config.getoption('full_cov') and len(config.getoption('full_cov')) > 0 and
        config.pluginmanager.getplugin("_cov") is not None and
        config.pluginmanager.getplugin("_cov").cov_controller is not None and
        config.pluginmanager.getplugin("_cov").cov_controller.cov is not None
    )

    c = configparser.ConfigParser()
    c.read(os.path.join(here, "..", "setup.cfg"))
    fs = c['tool:full_coverage']['exclude'].split('\n')
    no_full_cov = config.option.no_full_cov + [f.strip() for f in fs]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtestloop(session):
    global enable_coverage
    global coverage_values
    global coverage_passed
    global no_full_cov

    if not enable_coverage:
        yield
        return

    cov = session.config.pluginmanager.getplugin("_cov").cov_controller.cov

    if os.name == 'nt':
        cov.exclude('pragma: windows no cover')

    if sys.platform == 'darwin':
        cov.exclude('pragma: osx no cover')

    if os.environ.get("OPENSSL") == "old":
        cov.exclude('pragma: openssl-old no cover')

    yield

    coverage_values = {name: 0 for name in session.config.option.full_cov}

    prefix = os.getcwd()

    excluded_files = [os.path.normpath(f) for f in no_full_cov]
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
        coverage_passed = False


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    global enable_coverage
    global coverage_values
    global coverage_passed
    global no_full_cov

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
                        msg += f'  {s}: {v:.2f}%\n'
            else:
                markup = {'green': True}
            terminalreporter.write(msg, **markup)
    else:
        msg = 'SUCCESS: Full test coverage reached in modules and files:\n'
        msg += '{}\n\n'.format('\n'.join(config.option.full_cov))
        terminalreporter.write(msg, green=True)

    msg = '\nExcluded files:\n'
    for s in sorted(no_full_cov):
        msg += f"  {s}\n"
    terminalreporter.write(msg)
