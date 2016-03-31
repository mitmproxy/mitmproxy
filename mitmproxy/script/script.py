"""
The script object representing mitmproxy inline scripts.
Script objects know nothing about mitmproxy or mitmproxy's API - this knowledge is provided
by the mitmproxy-specific ScriptContext.
"""
# Do not import __future__ here, this would apply transitively to the inline scripts.
import os
import shlex
import traceback
import sys

import six

from ..exceptions import ScriptException


class Script(object):

    """
    Script object representing an inline script.
    """

    def __init__(self, command, context):
        self.command = command
        self.args = self.parse_command(command)
        self.ctx = context
        self.ns = None

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            return False  # reraise the exception
        self.unload()

    @property
    def filename(self):
        return self.args[0]

    @staticmethod
    def parse_command(command):
        if not command or not command.strip():
            raise ScriptException("Empty script command.")
        # Windows: escape all backslashes in the path.
        if os.name == "nt":  # pragma: no cover
            backslashes = shlex.split(command, posix=False)[0].count("\\")
            command = command.replace("\\", "\\\\", backslashes)
        args = shlex.split(command)  # pragma: no cover
        args[0] = os.path.expanduser(args[0])
        if not os.path.exists(args[0]):
            raise ScriptException(
                ("Script file not found: %s.\r\n"
                 "If your script path contains spaces, "
                 "make sure to wrap it in additional quotes, e.g. -s \"'./foo bar/baz.py' --args\".") %
                args[0])
        elif os.path.isdir(args[0]):
            raise ScriptException("Not a file: %s" % args[0])
        return args

    def load(self):
        """
            Loads an inline script.

            Returns:
                The return value of self.run("start", ...)

            Raises:
                ScriptException on failure
        """
        if self.ns is not None:
            raise ScriptException("Script is already loaded")
        script_dir = os.path.dirname(os.path.abspath(self.args[0]))
        self.ns = {'__file__': os.path.abspath(self.args[0])}
        sys.path.append(script_dir)
        try:
            with open(self.filename) as f:
                code = compile(f.read(), self.filename, 'exec')
                exec (code, self.ns, self.ns)
        except Exception as e:
            six.reraise(
                ScriptException,
                ScriptException(str(e)),
                sys.exc_info()[2]
            )
        finally:
            sys.path.pop()
        return self.run("start", self.args)

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
            raise ScriptException("Script not loaded.")
        f = self.ns.get(name)
        if f:
            try:
                return f(self.ctx, *args, **kwargs)
            except Exception as e:
                six.reraise(
                    ScriptException,
                    ScriptException(str(e)),
                    sys.exc_info()[2]
                )
        else:
            return None
