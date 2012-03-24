#
# Unpacker for eval() based packers, a part of javascript beautifier
# by Einar Lielmanis <einar@jsbeautifier.org>
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# usage:
#
# if detect(some_string):
#     unpacked = unpack(some_string)
#

"""Unpacker for eval() based packers: runs JS code and returns result.
Works only if a JS interpreter (e.g. Mozilla's Rhino) is installed and
properly set up on host."""

from subprocess import PIPE, Popen

PRIORITY = 3

def detect(source):
    """Detects if source is likely to be eval() packed."""
    return source.strip().lower().startswith('eval(function(')

def unpack(source):
    """Runs source and return resulting code."""
    return jseval('print %s;' % source[4:]) if detect(source) else source

# In case of failure, we'll just return the original, without crashing on user.
def jseval(script):
    """Run code in the JS interpreter and return output."""
    try:
        interpreter = Popen(['js'], stdin=PIPE, stdout=PIPE)
    except OSError:
        return script
    result, errors = interpreter.communicate(script)
    if interpreter.poll() or errors:
        return script
    return result
