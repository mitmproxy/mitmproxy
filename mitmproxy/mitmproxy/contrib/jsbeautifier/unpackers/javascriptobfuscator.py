#
# simple unpacker/deobfuscator for scripts messed up with
# javascriptobfuscator.com
#
#     written by Einar Lielmanis <einar@jsbeautifier.org>
#     rewritten in Python by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# Will always return valid javascript: if `detect()` is false, `code` is
# returned, unmodified.
#
# usage:
#
# if javascriptobfuscator.detect(some_string):
#     some_string = javascriptobfuscator.unpack(some_string)
#

"""deobfuscator for scripts messed up with JavascriptObfuscator.com"""

import re

PRIORITY = 1

def smartsplit(code):
    """Split `code` at " symbol, only if it is not escaped."""
    strings = []
    pos = 0
    while pos < len(code):
        if code[pos] == '"':
            word = '' # new word
            pos += 1
            while pos < len(code):
                if code[pos] == '"':
                    break
                if code[pos] == '\\':
                    word += '\\'
                    pos += 1
                word += code[pos]
                pos += 1
            strings.append('"%s"' % word)
        pos += 1
    return strings

def detect(code):
    """Detects if `code` is JavascriptObfuscator.com packed."""
    # prefer `is not` idiom, so that a true boolean is returned
    return (re.search(r'^var _0x[a-f0-9]+ ?\= ?\[', code) is not None)

def unpack(code):
    """Unpacks JavascriptObfuscator.com packed code."""
    if detect(code):
        matches = re.search(r'var (_0x[a-f\d]+) ?\= ?\[(.*?)\];', code)
        if matches:
            variable = matches.group(1)
            dictionary = smartsplit(matches.group(2))
            code = code[len(matches.group(0)):]
            for key, value in enumerate(dictionary):
                code = code.replace(r'%s[%s]' % (variable, key), value)
    return code
