#
# deobfuscator for scripts messed up with myobfuscate.com
# by Einar Lielmanis <einar@jsbeautifier.org>
#
#     written by Stefano Sanfilippo <a.little.coder@gmail.com>
#
# usage:
#
# if detect(some_string):
#     unpacked = unpack(some_string)
#

# CAVEAT by Einar Lielmanis

#
# You really don't want to obfuscate your scripts there: they're tracking
# your unpackings, your script gets turned into something like this,
# as of 2011-08-26:
#
#   var _escape = 'your_script_escaped';
#   var _111 = document.createElement('script');
#   _111.src = 'http://api.www.myobfuscate.com/?getsrc=ok' +
#              '&ref=' + encodeURIComponent(document.referrer) +
#              '&url=' + encodeURIComponent(document.URL);
#   var 000 = document.getElementsByTagName('head')[0];
#   000.appendChild(_111);
#   document.write(unescape(_escape));
#

"""Deobfuscator for scripts messed up with MyObfuscate.com"""

import re
import base64

# Python 2 retrocompatibility
# pylint: disable=F0401
# pylint: disable=E0611
try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote

from . import UnpackingError

PRIORITY = 1

CAVEAT = """//
// Unpacker warning: be careful when using myobfuscate.com for your projects:
// scripts obfuscated by the free online version call back home.
//

"""

SIGNATURE = (r'["\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4A\x4B\x4C\x4D\x4E\x4F'
             r'\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5A\x61\x62\x63\x64\x65'
             r'\x66\x67\x68\x69\x6A\x6B\x6C\x6D\x6E\x6F\x70\x71\x72\x73\x74\x75'
             r'\x76\x77\x78\x79\x7A\x30\x31\x32\x33\x34\x35\x36\x37\x38\x39\x2B'
             r'\x2F\x3D","","\x63\x68\x61\x72\x41\x74","\x69\x6E\x64\x65\x78'
             r'\x4F\x66","\x66\x72\x6F\x6D\x43\x68\x61\x72\x43\x6F\x64\x65","'
             r'\x6C\x65\x6E\x67\x74\x68"]')

def detect(source):
    """Detects MyObfuscate.com packer."""
    return SIGNATURE in source

def unpack(source):
    """Unpacks js code packed with MyObfuscate.com"""
    if not detect(source):
        return source
    payload = unquote(_filter(source))
    match = re.search(r"^var _escape\='<script>(.*)<\/script>'",
                      payload, re.DOTALL)
    polished = match.group(1) if match else source
    return CAVEAT + polished

def _filter(source):
    """Extracts and decode payload (original file) from `source`"""
    try:
        varname = re.search(r'eval\(\w+\(\w+\((\w+)\)\)\);', source).group(1)
        reverse = re.search(r"var +%s *\= *'(.*)';" % varname, source).group(1)
    except AttributeError:
        raise UnpackingError('Malformed MyObfuscate data.')
    try:
        return base64.b64decode(reverse[::-1].encode('utf8')).decode('utf8')
    except TypeError:
        raise UnpackingError('MyObfuscate payload is not base64-encoded.')
