"""
The script object representing mitmproxy inline scripts.
Script objects know nothing about mitmproxy or mitmproxy's API - this knowledge is provided
by the mitmproxy-specific ScriptContext.
"""
# Do not import __future__ here, this would apply transitively to the inline scripts.
from __future__ import absolute_import, print_function, division

import os
import shlex
import sys
import contextlib

import six
from typing import List  # noqa

from mitmproxy import exceptions


@contextlib.contextmanager
def scriptenv(path, args):
    # type: (str, List[str]) -> None
    oldargs = sys.argv
    script_dir = os.path.dirname(os.path.abspath(path))

    sys.argv = [path] + args
    sys.path.append(script_dir)
    try:
        yield
    finally:
        sys.argv = oldargs
        sys.path.pop()


class Script(object):
    """
    Script object representing an inline script.
    """

    def __init__(self, command):
        self.command = command
        self.path, self.args = self.parse_command(command)
        self.ns = None

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            return False  # re-raise the exception
        self.unload()

    @staticmethod
    def parse_command(command):
        # type: (str) -> Tuple[str,List[str]]
        """
            Returns a (path, args) tuple.
        """
        if not command or not command.strip():
            raise exceptions.ScriptException("Empty script command.")
        # Windows: escape all backslashes in the path.
        if os.name == "nt":  # pragma: no cover
            backslashes = shlex.split(command, posix=False)[0].count("\\")
            command = command.replace("\\", "\\\\", backslashes)
        args = shlex.split(command)  # pragma: no cover
        args[0] = os.path.expanduser(args[0])
        if not os.path.exists(args[0]):
            raise exceptions.ScriptException(
                ("Script file not found: %s.\r\n"
                 "If your script path contains spaces, "
                 "make sure to wrap it in additional quotes, e.g. -s \"'./foo bar/baz.py' --args\".") %
                args[0])
        elif os.path.isdir(args[0]):
            raise exceptions.ScriptException("Not a file: %s" % args[0])
        return args[0], args[1:]

    def load(self):
        """
            Loads an inline script.

            Returns:
                The return value of self.run("start", ...)

            Raises:
                ScriptException on failure
        """
        if self.ns is not None:
            raise exceptions.ScriptException("Script is already loaded")
        self.ns = {'__file__': os.path.abspath(self.path)}

        with scriptenv(self.path, self.args):
            try:
                with open(self.path) as f:
                    code = compile(f.read(), self.path, 'exec')
                    exec(code, self.ns, self.ns)
            except Exception:
                six.reraise(
                    exceptions.ScriptException,
                    exceptions.ScriptException.from_exception_context(),
                    sys.exc_info()[2]
                )
        return self.run("start")

    def unload(self):
        try:
            return self.run("done")
        finally:
            self.ns = None

    def run(self, name, *args, **kwargs):
        """
            Runs an inline script hook.

            Returns:
                The return value of the method.
                None, if the script does not provide the method.

            Raises:
                ScriptException if there was an exception.
        """
        if self.ns is None:
            raise exceptions.ScriptException("Script not loaded.")
        f = self.ns.get(name)
        if f:
            try:
                with scriptenv(self.path, self.args):
                    return f(*args, **kwargs)
            except Exception:
                six.reraise(
                    exceptions.ScriptException,
                    exceptions.ScriptException.from_exception_context(),
                    sys.exc_info()[2]
                )
        else:
            return None
