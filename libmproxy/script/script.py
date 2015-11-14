"""
The script object representing mitmproxy inline scripts.
Script objects know nothing about mitmproxy or mitmproxy's API - this knowledge is provided
by the mitmproxy-specific ScriptContext.
"""
from __future__ import absolute_import, print_function, division
import os
import shlex
import traceback
import sys
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
        self.load()

    @property
    def filename(self):
        return self.args[0]

    @staticmethod
    def parse_command(command):
        if not command or not command.strip():
            raise ScriptException("Empty script command.")
        if os.name == "nt":  # Windows: escape all backslashes in the path.
            backslashes = shlex.split(command, posix=False)[0].count("\\")
            command = command.replace("\\", "\\\\", backslashes)
        args = shlex.split(command)
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
            self.unload()
        script_dir = os.path.dirname(os.path.abspath(self.args[0]))
        self.ns = {'__file__': os.path.abspath(self.args[0])}
        sys.path.append(script_dir)
        try:
            execfile(self.args[0], self.ns, self.ns)
        except Exception as e:
            # Python 3: use exception chaining, https://www.python.org/dev/peps/pep-3134/
            raise ScriptException(traceback.format_exc(e))
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
        f = self.ns.get(name)
        if f:
            try:
                return f(self.ctx, *args, **kwargs)
            except Exception as e:
                raise ScriptException(traceback.format_exc(e))
        else:
            return None