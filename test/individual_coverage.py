#!/usr/bin/env python3

import io
import contextlib
import os
import sys
import glob
import multiprocessing
import configparser
import itertools
import pytest


def run_tests(src, test, fail):
    stderr = io.StringIO()
    stdout = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        with contextlib.redirect_stdout(stdout):
            e = pytest.main([
                '-qq',
                '--disable-pytest-warnings',
                '--cov', src.replace('.py', '').replace('/', '.'),
                '--cov-fail-under', '100',
                '--cov-report', 'term-missing:skip-covered',
                '-o', 'faulthandler_timeout=0',
                test
            ])

    if e == 0:
        if fail:
            print("FAIL DUE TO UNEXPECTED SUCCESS:", src, "Please remove this file from setup.cfg tool:individual_coverage/exclude.")
            e = 42
        else:
            print(".")
    else:
        if fail:
            print("Ignoring allowed fail:", src)
            e = 0
        else:
            cov = [l for l in stdout.getvalue().split("\n") if (src in l) or ("was never imported" in l)]
            if len(cov) == 1:
                print("FAIL:", cov[0])
            else:
                print("FAIL:", src, test, stdout.getvalue(), stdout.getvalue())
                print(stderr.getvalue())
                print(stdout.getvalue())

    sys.exit(e)


def start_pytest(src, test, fail):
    # run pytest in a new process, otherwise imports and modules might conflict
    proc = multiprocessing.Process(target=run_tests, args=(src, test, fail))
    proc.start()
    proc.join()
    return (src, test, proc.exitcode)


def main():
    c = configparser.ConfigParser()
    c.read('setup.cfg')
    fs = c['tool:individual_coverage']['exclude'].strip().split('\n')
    no_individual_cov = [f.strip() for f in fs]

    excluded = ['mitmproxy/contrib/', 'mitmproxy/test/', 'mitmproxy/tools/', 'mitmproxy/platform/']
    src_files = glob.glob('mitmproxy/**/*.py', recursive=True)
    src_files = [f for f in src_files if os.path.basename(f) != '__init__.py']
    src_files = [f for f in src_files if not any(os.path.normpath(p) in f for p in excluded)]

    ps = []
    for src in sorted(src_files):
        test = os.path.join("test", os.path.dirname(src), "test_" + os.path.basename(src))
        if os.path.isfile(test):
            ps.append((src, test, src in no_individual_cov))

    result = list(itertools.starmap(start_pytest, ps))

    if any(e != 0 for _, _, e in result):
        sys.exit(1)
        pass


if __name__ == '__main__':
    main()
