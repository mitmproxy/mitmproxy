import os
import re
import glob
import sys


def check_src_files_have_test():
    missing_test_files = []

    excluded = ['mitmproxy/contrib/', 'mitmproxy/test/', 'mitmproxy/tools/', 'mitmproxy/platform/']
    src_files = glob.glob('mitmproxy/**/*.py', recursive=True) + glob.glob('pathod/**/*.py', recursive=True)
    src_files = [f for f in src_files if os.path.basename(f) != '__init__.py']
    src_files = [f for f in src_files if not any(os.path.normpath(p) in f for p in excluded)]
    for f in src_files:
        p = os.path.join("test", os.path.dirname(f), "test_" + os.path.basename(f))
        if not os.path.isfile(p):
            missing_test_files.append((f, p))

    return missing_test_files


def check_test_files_have_src():
    unknown_test_files = []

    excluded = ['test/mitmproxy/data/', 'test/mitmproxy/net/data/', '/tservers.py', '/conftest.py']
    test_files = glob.glob('test/mitmproxy/**/*.py', recursive=True) + glob.glob('test/pathod/**/*.py', recursive=True)
    test_files = [f for f in test_files if os.path.basename(f) != '__init__.py']
    test_files = [f for f in test_files if not any(os.path.normpath(p) in f for p in excluded)]
    for f in test_files:
        p = os.path.join(re.sub('^test/', '', os.path.dirname(f)), re.sub('^test_', '', os.path.basename(f)))
        if not os.path.isfile(p):
            unknown_test_files.append((f, p))

    return unknown_test_files


def main():
    exitcode = 0

    missing_test_files = check_src_files_have_test()
    if missing_test_files:
        exitcode += 1
        for f, p in sorted(missing_test_files):
            print("{} MUST have a matching test file: {}".format(f, p))

    unknown_test_files = check_test_files_have_src()
    if unknown_test_files:
        # TODO: enable this in the future
        # exitcode += 1
        for f, p in sorted(unknown_test_files):
            print("{} DOES NOT MATCH a source file! Expected to find: {}".format(f, p))

    sys.exit(exitcode)


if __name__ == '__main__':
    main()
