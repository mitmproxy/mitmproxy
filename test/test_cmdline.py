import argparse
from libmproxy import cmdline
import tutils
import os.path


class MockParser(argparse.ArgumentParser):
    """
    argparse.ArgumentParser sys.exits() by default.
    Make it more testable by throwing an exception instead.
    """
    def error(self, message):
        raise Exception(message)


def test_parse_replace_hook():
    x = cmdline.parse_replace_hook("/foo/bar/voing")
    assert x == ("foo", "bar", "voing")

    x = cmdline.parse_replace_hook("/foo/bar/vo/ing/")
    assert x == ("foo", "bar", "vo/ing/")

    x = cmdline.parse_replace_hook("/bar/voing")
    assert x == (".*", "bar", "voing")

    tutils.raises(
        "replacement regex",
        cmdline.parse_replace_hook,
        "patt/[/rep"
    )
    tutils.raises(
        "filter pattern",
        cmdline.parse_replace_hook,
        "/~/foo/rep"
    )
    tutils.raises(
        "empty clause",
        cmdline.parse_replace_hook,
        "//"
    )


def test_parse_setheaders():
    x = cmdline.parse_setheader("/foo/bar/voing")
    assert x == ("foo", "bar", "voing")

def test_shlex():
    """
    shlex.split assumes posix=True by default, we do manual detection for windows.
    Test whether script paths are parsed correctly
    """
    absfilepath = os.path.normcase(os.path.abspath(__file__))

    parser = MockParser()
    cmdline.add_common_arguments(parser)
    opts = parser.parse_args(args=["-s",absfilepath])
    
    assert os.path.isfile(opts.scripts[0][0])

def test_common():
    parser = MockParser()
    cmdline.add_common_arguments(parser)
    opts = parser.parse_args(args=[])

    opts = parser.parse_args(args=["-t","foo","-u","foo"])

    assert opts.stickycookie == "foo"
    assert opts.stickyauth == "foo"

    opts = parser.parse_args(args=["--setheader","/foo/bar/voing"])
    assert opts.setheaders == [("foo", "bar", "voing")]

    tutils.raises(
        "empty clause",
        parser.parse_args,
        ["--setheader","//"]
    )

    opts = parser.parse_args(args=["--replace","/foo/bar/voing"])
    assert opts.replacements == [("foo", "bar", "voing")]

    tutils.raises(
        "empty clause",
        parser.parse_args,
        ["--replace","//"]
    )

    tutils.raises(
        "could not read replace file",
        parser.parse_args,
        ["--replace-from-file","/foo/bar/nonexistent"]
    )

    tutils.raises(
        "filter pattern",
        parser.parse_args,
        ["--replace-from-file","/~/bar/nonexistent"]
    )

    p = tutils.test_data.path("data/replace")
    opts = parser.parse_args(args=["--replace-from-file",("/foo/bar/%s"%p)])
    assert len(opts.replacements) == 1
    assert opts.replacements[0][2].strip() == "replacecontents"

