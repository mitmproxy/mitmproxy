#!/usr/bin/env python

# Copyright (C) 2010  Henrik Nordstrom <henrik@henriknordstrom.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# HENRIK NORDSTROM BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
# OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Alternatively you may use this file under a GPLv3 license as follows:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import sys
import time
import hashlib
import utils
import proxy
import collections
import itertools
import string
import Cookie
import filt
import re
import cStringIO

def constant_factory(value):
    return itertools.repeat(value).next

class PatternRule:
    """
        Request pattern rule
        :_ivar  _match          filt pattern rule
        :_ivar  _search         Regex pattern to search for
        :_ivar  _replace        Replacement string
    """
    def __init__(self, pattern, search, replace):
        self.match = filt.parse(pattern)
        self.search = re.compile(search)
        self.replace = replace
    def execute(self, request, text):
        if self.match and not self.match(request):
            return text
        return re.sub(self.search, self.replace, text)

class RecorderConnection(proxy.ServerConnection):
    """
        Simulated ServerConnection connecting to the cache
    """
    # Note: This may chane in future. Division between Recorder
    # and RecorderConnection is not yet finalized
    def __init__(self, request, fp):
        self.host = request.host
        self.port = request.port
        self.scheme = request.scheme
        self.close = False
        self.server = fp
        self.rfile = fp
        self.wfile = fp

    def send_request(self, request):
        self.request = request

    def read_response(self):
        response = proxy.ServerConnection.read_response(self)
        response.cached = True
        return response

class Recorder:
    """
        A simple record/playback cache
    """
    def __init__(self, options):
        self.sequence = collections.defaultdict(int)
        self.cookies = {}
        try:
            for cookie in options.cookies:
                self.cookies[cookie] = True
        except AttributeError: pass
        try:
            self.verbosity = options.verbose
        except AttributeError:
            self.verbosity = False
        self.storedir = options.cache
        self.patterns = []
        self.indexfp = None
        self.reset_config()

    def reset_config(self):
        self.patterns = []
        self.load_config("default")

    def add_rule(self, match, search, replace):
        self.patterns.append(PatternRule(match, search, replace))

    def forget_last_rule(self):
        self.patterns.pop()

    def save_rule(self, match, search, replace, configfile = "default"):
        fp = self.open(configfile + ".cfg", "a")
        print >> fp, "Condition: " + match
        print >> fp, "Search: " + search
        print >> fp, "Replace: " + replace
        fp.close()

    def load_config(self, name):
        """
            Load configuration settings from name
        """
        try:
            file = name + ".cfg"
            if self.verbosity > 2:
                print >> sys.stderr, "config: " + file
            fp = self.open(file, "r")
        except IOError:
            return False
        for line in fp:
            directive, value = line.split(" ", 1)
            value = value.strip("\r\n")
            if directive == "Cookie:":
                self.cookies[value] = True
            if directive == "Condition:":
                match = value
            if directive == "Search:":
                search = value
            if directive == "Replace:":
                self.add_rule(match, search, value)
        fp.close()
        return True

    def filter_request(self, request):
        """
            Filter forwarded requests to enable better recording
        """
        request = request.copy()
        headers = request.headers
        utils.try_del(headers, 'if-modified-since')
        utils.try_del(headers, 'if-none-match')
        return request

    def normalize_request(self, request):
        """
            Filter request to simplify storage matching
        """
        request.close = False
        req_text = request.assemble_proxy()
        orig_req_text = req_text
        for pattern in self.patterns:
            req_text = pattern.execute(request, req_text)
        if req_text == orig_req_text:
            return request
        fp = cStringIO.StringIO(req_text)
        request_line = fp.readline()
        method, scheme, host, port, path, httpminor = proxy.parse_request_line(request_line)
        headers = utils.Headers()
        headers.read(fp)
        if request.content is None:
            content = None
        else:
            content = fp.read()
        return proxy.Request(request.client_conn, host, port, scheme, method, path, headers, content)

    def open(self, path, mode):
        return open(self.storedir + "/" + path, mode)

    def pathn(self, request):
        """
            Create cache file name and sequence number
        """
        request = self.normalize_request(request)
        request = self.filter_request(request)
        headers = request.headers
        urlkey = (request.host + request.path)[:80].translate(string.maketrans(":/?","__."))
        id = ""
        if headers.has_key("cookie"):
            cookies = Cookie.SimpleCookie("; ".join(headers["cookie"]))
            del headers["cookie"]
            for key, morsel in cookies.iteritems():
                if self.cookies.has_key(key):
                    id = id + key + "=" + morsel.value + "\n"
        if self.verbosity > 1:
            print >> sys.stderr, "ID: " + id
        m = hashlib.sha224(id)
        req_text = request.assemble_proxy()
        if self.verbosity > 2:
            print >> sys.stderr, req_text
        m.update(req_text)
        path = urlkey+"."+m.hexdigest()
        n = str(self.sequence[path])
        if self.verbosity > 1:
            print >> sys.stderr, "PATH: " + path + "." + n
        return path, n

    def filter_response(self, response):
        if response.headers.has_key('set-cookie'):
            for header in response.headers['set-cookie']:
                key = header.split('=',1)[0]
                self.cookies[key] = True
        return response

    def save_response(self, response):
        """
            Save response for later playback
        """

        if self.indexfp is None:
            self.indexfp = self.open("index.txt", "a")
            try:
                cfg = self.open("default.cfg", "r")
            except:
                cfg = self.open("default.cfg", "w")
                for cookie in iter(self.cookies):
                    print >> cfg, "Cookie: " + cookie
            cfg.close()
        request = response.request
        req_text = request.assemble_proxy()
        resp_text = response.assemble()
        path, n = self.pathn(request)
        self.sequence[path] += 1

        f = self.open(path+"."+n+".req", 'w')
        f.write(req_text)
        f.close()
        f = self.open(path+"."+n+".resp", 'w')
        f.write(resp_text)
        f.close()

        print >> self.indexfp , time.time(), request.method, request.path
        if request.headers.has_key('referer'):
            print >> self.indexfp, 'referer:', ','.join(request.headers['referer'])
        if len(self.cookies) > 0:
            print >> self.indexfp, 'cookies:', ','.join(self.cookies)
        print >> self.indexfp , path
        print >> self.indexfp , ""
        self.indexfp.flush()


    def get_response(self, request):
        """
            Retrieve previously saved response saved by save_response
        """
        path, n = self.pathn(request)
        try:
            fp = self.open(path+"."+n+".resp", 'r')
            self.sequence[path]+=1
        except IOError:
            fp = self.open(path+".resp", 'r')
        server = RecorderConnection(request, fp)
        fp = None       # Handed over to RecorderConnection
        server.send_request(request)
        response = server.read_response()
        server.terminate()
        return response
