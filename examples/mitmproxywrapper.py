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
import contextlib
import os
import sys


class Wrapper(object):

    def __init__(self, port, extra_arguments=None):
        self.port = port
        self.extra_arguments = extra_arguments

    def run_networksetup_command(self, *arguments):
        return subprocess.check_output(
            ['sudo', 'networksetup'] + list(arguments))

    def proxy_state_for_service(self, service):
        state = self.run_networksetup_command(
            '-getwebproxy',
            service).splitlines()
        return dict([re.findall(r'([^:]+): (.*)', line)[0] for line in state])

    def enable_proxy_for_service(self, service):
        print('Enabling proxy on {}...'.format(service))
        for subcommand in ['-setwebproxy', '-setsecurewebproxy']:
            self.run_networksetup_command(
                subcommand, service, '127.0.0.1', str(
                    self.port))

    def disable_proxy_for_service(self, service):
        print('Disabling proxy on {}...'.format(service))
        for subcommand in ['-setwebproxystate', '-setsecurewebproxystate']:
            self.run_networksetup_command(subcommand, service, 'Off')

    def interface_name_to_service_name_map(self):
        order = self.run_networksetup_command('-listnetworkserviceorder')
        mapping = re.findall(
            r'\(\d+\)\s(.*)$\n\(.*Device: (.+)\)$',
            order,
            re.MULTILINE)
        return dict([(b, a) for (a, b) in mapping])

    def run_command_with_input(self, command, input):
        popen = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)
        (stdout, stderr) = popen.communicate(input)
        return stdout

    def primary_interace_name(self):
        scutil_script = 'get State:/Network/Global/IPv4\nd.show\n'
        stdout = self.run_command_with_input('/usr/sbin/scutil', scutil_script)
        interface, = re.findall(r'PrimaryInterface\s*:\s*(.+)', stdout)
        return interface

    def primary_service_name(self):
        return self.interface_name_to_service_name_map()[
            self.primary_interace_name()]

    def proxy_enabled_for_service(self, service):
        return self.proxy_state_for_service(service)['Enabled'] == 'Yes'

    def toggle_proxy(self):
        new_state = not self.proxy_enabled_for_service(
            self.primary_service_name())
        for service_name in self.connected_service_names():
            if self.proxy_enabled_for_service(service_name) and not new_state:
                self.disable_proxy_for_service(service_name)
            elif not self.proxy_enabled_for_service(service_name) and new_state:
                self.enable_proxy_for_service(service_name)

    def connected_service_names(self):
        scutil_script = 'list\n'
        stdout = self.run_command_with_input('/usr/sbin/scutil', scutil_script)
        service_ids = re.findall(r'State:/Network/Service/(.+)/IPv4', stdout)

        service_names = []
        for service_id in service_ids:
            scutil_script = 'show Setup:/Network/Service/{}\n'.format(
                service_id)
            stdout = self.run_command_with_input(
                '/usr/sbin/scutil',
                scutil_script)
            service_name, = re.findall(r'UserDefinedName\s*:\s*(.+)', stdout)
            service_names.append(service_name)

        return service_names

    def wrap_mitmproxy(self):
        with self.wrap_proxy():
            cmd = ['mitmproxy', '-p', str(self.port)]
            if self.extra_arguments:
                cmd.extend(self.extra_arguments)
            subprocess.check_call(cmd)

    def wrap_honeyproxy(self):
        with self.wrap_proxy():
            popen = subprocess.Popen('honeyproxy.sh')
            try:
                popen.wait()
            except KeyboardInterrupt:
                popen.terminate()

    @contextlib.contextmanager
    def wrap_proxy(self):
        connected_service_names = self.connected_service_names()
        for service_name in connected_service_names:
            if not self.proxy_enabled_for_service(service_name):
                self.enable_proxy_for_service(service_name)

        yield

        for service_name in connected_service_names:
            if self.proxy_enabled_for_service(service_name):
                self.disable_proxy_for_service(service_name)

    @classmethod
    def ensure_superuser(cls):
        if os.getuid() != 0:
            print('Relaunching with sudo...')
            os.execv('/usr/bin/sudo', ['/usr/bin/sudo'] + sys.argv)

    @classmethod
    def main(cls):
        parser = argparse.ArgumentParser(
            description='Helper tool for OS X proxy configuration and mitmproxy.',
            epilog='Any additional arguments will be passed on unchanged to mitmproxy.')
        parser.add_argument(
            '-t',
            '--toggle',
            action='store_true',
            help='just toggle the proxy configuration')
#         parser.add_argument('--honeyproxy', action='store_true', help='run honeyproxy instead of mitmproxy')
        parser.add_argument(
            '-p',
            '--port',
            type=int,
            help='override the default port of 8080',
            default=8080)
        args, extra_arguments = parser.parse_known_args()

        wrapper = cls(port=args.port, extra_arguments=extra_arguments)

        if args.toggle:
            wrapper.toggle_proxy()
#         elif args.honeyproxy:
#             wrapper.wrap_honeyproxy()
        else:
            wrapper.wrap_mitmproxy()


if __name__ == '__main__':
    Wrapper.ensure_superuser()
    Wrapper.main()
