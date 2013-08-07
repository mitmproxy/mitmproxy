#!/usr/bin/env python
#
# Helper tool to enable/disable OS X proxy and wrap mitmproxy
#
# Get usage information with:
#
# mitmproxywrapper.py -h
#

import subprocess
import re
import argparse

class Wrapper(object):
    
    def __init__(self, port):
        self.port = port
        self.primary_service_name = self.find_primary_service_name()

    def run_networksetup_command(self, *arguments):
        return subprocess.check_output(['sudo', 'networksetup'] + list(arguments))

    def proxy_state_for_service(self, service):
        state = self.run_networksetup_command('-getwebproxy', service).splitlines()
        return dict([re.findall(r'([^:]+): (.*)', line)[0] for line in state])

    def enable_proxy_for_service(self, service):
        print 'Enabling proxy on {}...'.format(service)
        for subcommand in ['-setwebproxy', '-setsecurewebproxy']:
            self.run_networksetup_command(subcommand, service, '127.0.0.1', str(self.port))

    def disable_proxy_for_service(self, service):
        print 'Disabling proxy on {}...'.format(service)
        for subcommand in ['-setwebproxystate', '-setsecurewebproxystate']:
            self.run_networksetup_command(subcommand, service, 'Off')

    def interface_name_to_service_name_map(self):
        order = self.run_networksetup_command('-listnetworkserviceorder')
        mapping = re.findall(r'\(\d+\)\s(.*)$\n\(.*Device: (.+)\)$', order, re.MULTILINE)
        return dict([(b, a) for (a, b) in mapping])

    def run_command_with_input(self, command, input):
        popen = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        (stdout, stderr) = popen.communicate(input)
        return stdout
    
    def primary_interace_name(self):
        scutil_script = 'get State:/Network/Global/IPv4\nd.show\n'
        stdout = self.run_command_with_input('/usr/sbin/scutil', scutil_script)
        interface, = re.findall(r'PrimaryInterface\s*:\s*(.+)', stdout)
        return interface

    def find_primary_service_name(self):
        return self.interface_name_to_service_name_map()[self.primary_interace_name()]

    def proxy_enabled_for_service(self, service):
        return self.proxy_state_for_service(service)['Enabled'] == 'Yes'

    def toggle_proxy(self):
        if self.proxy_enabled_for_service(self.primary_service_name):
            self.disable_proxy_for_service(self.primary_service_name)
        else:
            self.enable_proxy_for_service(self.primary_service_name)

    def wrap_mitmproxy(self):
        if not self.proxy_enabled_for_service(self.primary_service_name):
            self.enable_proxy_for_service(self.primary_service_name)

        subprocess.check_call(['mitmproxy', '-p', str(self.port), '--palette', 'light'])

        if self.proxy_enabled_for_service(self.primary_service_name):
            self.disable_proxy_for_service(self.primary_service_name)

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(description='Helper tool for OS X proxy configuration and mitmproxy')
        parser.add_argument('-t', '--toggle', action='store_true', help='just toggle the proxy configuration')
        parser.add_argument('-p', '--port', type=int, help='override the default port of 8080', default=8080)
        args = parser.parse_args()

        wrapper = cls(port=args.port)
        if args.toggle:
            wrapper.toggle_proxy()
        else:
            wrapper.wrap_mitmproxy()

if __name__ == '__main__':
    Wrapper.main()

