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
import controller
import utils
import proxy
import recorder

class PlaybackMaster(controller.Master):
    """
        A simple master that plays back recorded responses.
    """
    def __init__(self, server, options):
        self.verbosity = options.verbose
        self.store = recorder.Recorder(options)
        controller.Master.__init__(self, server)

    def run(self):
        try:
            return controller.Master.run(self)
        except KeyboardInterrupt:
            self.shutdown()

    def process_missing_response(self, request):
        response = None
        print >> sys.stderr, self.store.normalize_request(request).assemble_proxy()
        print >> sys.stderr, "Actions:"
        print >> sys.stderr, "  q  Quit"
        print >> sys.stderr, "  a(dd)        Add pattern rule"
        print >> sys.stderr, "  A(dd)        Add pattern rule (forced)"
        print >> sys.stderr, "  e(rror)      respond with a 404 error"
        print >> sys.stderr, "  k(ill)       kill the request, empty response"
        print >> sys.stderr, "  f(orward)    forward the request to the requested server and cache response"
        command = raw_input("Action: ")
        command = command[:1]
        if command == 'q':
            self.shutdown()
            return None
        elif command == 'a' or command == 'A':
            filt = raw_input("Filter: ")
            search = raw_input("Search pattern: ")
            replace = raw_input("Replacement string: ")
            self.store.add_rule(filt, search, replace)
            if command == 'A':
                self.store.save_rule(filt, search, replace)
        elif command == 'e':
            return proxy.Response(request, "404", "Not found", utils.Headers(), "Not found")
        elif command == 'k':
            return None
        elif command == 'f':
            return request
        else:
            print >> sys.stderr, "ERROR: Unknown command"
            return self.process_missing_response(request)
        try:
            response = self.store.get_response(request)
            if command == 'a':
                self.store.save_rule(filt, search, replace)
        except proxy.ProxyError:
            print >> sys.stderr, "ERROR: Malformed substitution rule"
            self.store.forget_last_rule()
            response = self.process_missing_response(request)
        except IOError:
            print >> sys.stderr, "NOTICE: Response still not found"
            if command == 'a':
                self.store.forget_last_rule()
            response = self.process_missing_response(request)
        return response

    def handle_request(self, msg):
        request = msg
        try:
            response = self.store.get_response(request)
        except IOError:
            if self.verbosity > 0:
                print >> sys.stderr, ">>",
                print >> sys.stderr, request.short()
                print >> sys.stderr, "<<",
            print >> sys.stderr, "ERROR: No matching response.",
            print >> sys.stderr, ",".join(self.store.cookies)
            response = self.process_missing_response(msg)
        msg.ack(response)

    def handle_response(self, msg):
        request = msg.request
        response = msg
        if self.verbosity > 0:
            print >> sys.stderr, ">>",
            print >> sys.stderr, request.short()
            print >> sys.stderr, "<<",
            print >> sys.stderr, response.short()
        if not response.is_cached():
            self.store.save_response(response)
        msg.ack(self.store.filter_response(msg))
