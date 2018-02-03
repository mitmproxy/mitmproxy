#!/usr/bin/env python3

import tempfile
import sys
import os
import csv
import subprocess
import queue
import threading
import glob
import time
import platform

import pytest
from flaky import flaky

from mitmproxy import controller, flow, proxy, options
from mitmproxy.proxy.server import ProxyServer
from mitmproxy.proxy.config import ProxyConfig
from mitmproxy.addons.disable_h2c import DisableH2C
from test.mitmproxy import tservers

from splinter import Browser
from selenium.webdriver.chrome.options import Options as ChromeOptions

def generate_combinations():
    if not os.path.isdir('tmp'):
        os.makedirs('tmp')
    if not os.path.isfile('tmp/top500.domains.csv'):
        subprocess.run(['wget', 'https://moz.com/top500/domains/csv', '-q', '-O', 'tmp/top500.domains.csv'])

    domains = []
    with open('tmp/top500.domains.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        headers = next(reader)
        domains = [row[1].rstrip('/') for row in reader]

    l = [[
            (False, domain, "http://{}".format(domain)),
            (False, domain, "https://{}".format(domain)),
            (False, domain, "http://www.{}".format(domain)),
            (False, domain, "https://www.{}".format(domain)),
            (True, domain, "http://{}".format(domain)),
            (True, domain, "http://www.{}".format(domain)),
            (True, domain, "https://{}".format(domain)),
            (True, domain, "https://www.{}".format(domain)),
        ] for domain in domains]
    return [item for sublist in l for item in sublist][:10]


def write_protocol(offer_h2, domain, url, fs=None, events=None, logs=None):
    u = 'h2_' if offer_h2 else ''
    u += 'http' if url.startswith('http://') else 'https'
    u += '_www.' if '://www.' in url else '_'
    u += domain
    with open("tmp/{}/{}.txt".format(os.environ['SMOKE_TEST_TIMESTAMP'], u), mode='a') as file:
        file.write("\n################################################################################\n")
        file.write("{}: offer_h2:{} domain:{} url:{}\n".format(os.environ['SMOKE_TEST_TIMESTAMP'], offer_h2, domain, url))

        if fs:
            file.write("\nFlows:\n")
            for fl in fs.keys():
                file.write("{}\n".format(fl))
        else:
            file.write("\n<no flows>\n")

        if events:
            file.write("\nEvents:\n")
            for msg in events:
                file.write("{: <20} {}".format(msg[0].upper() + ':', msg[1]))
                file.write("\n")
        else:
            file.write("\n<no events>\n")

        if logs:
            file.write("\nLog entries:\n")
            for msg in logs:
                file.write("{: <6} {}".format(msg.level.upper() + ':', msg.msg))
                file.write("\n")
        else:
            file.write("\n<no log entries>\n")

        file.write("################################################################################\n")

    with open('/tmp/chromedriver-log.log') as f:
        print(f.read())
    print('-'*80)
    with open("tmp/{}/{}.txt".format(os.environ['SMOKE_TEST_TIMESTAMP'], u)) as f:
        print(f.read())


class TestSmokeCurl(object):
    @classmethod
    def setup_class(cls):
        cls.proxy = {}
        for offer_h2 in [True, False]:
            opts = options.Options(
                listen_port=0,
                upstream_cert=True,
                ssl_insecure=True,
                verbosity='debug',
                flow_detail=99,
                http2=offer_h2,
            )
            opts.cadir = os.path.expanduser("~/.mitmproxy")
            tmaster = tservers.TestMaster(opts)
            cls.proxy[offer_h2] = tservers.ProxyThread(tmaster)
            cls.proxy[offer_h2].start()

        cls.browser = None

    @classmethod
    def teardown_class(cls):
        for proxy in cls.proxy.values():
            proxy.shutdown()

    def teardown_method(self, method):
        if self.browser:
            self.browser.quit()
            self.browser = None

    @flaky(max_runs=3)
    @pytest.mark.parametrize('offer_h2, domain, url', generate_combinations())
    def test_smoke_curl(self, offer_h2, domain, url):
        self.proxy[offer_h2].tmaster.clear()
        self.proxy[offer_h2].tmaster.reset([DisableH2C()])

        chrome_options = ChromeOptions()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--proxy-server=http://127.0.0.1:' + str(self.proxy[offer_h2].port))
        if not offer_h2:
            chrome_options.add_argument('--disable-http2')
        self.browser = Browser('chrome',
                              options=chrome_options,
                              executable_path=os.path.expanduser('~/chromedriver'),
                              headless=True,
                              incognito=True,
                              service_log_path='/tmp/chromedriver-log.log',
                              service_args=["--verbose"])

        self.browser.visit(url)
        assert self.browser.status_code.is_success()

        fs = {}
        for f in self.proxy[offer_h2].tmaster.state.flows:
            if f.response:
                fs[(f.request.http_version, f.request.scheme, f.request.host, f.response.status_code)] = f

        if not offer_h2:
            assert all([k[0].startswith('HTTP/1') for k in fs.keys()])

        no_failed_flows = len([k for k in fs.keys() if k[3] >= 500]) == 0
        if not no_failed_flows:
            write_protocol(offer_h2, domain, url, fs=fs, events=self.proxy[offer_h2].tmaster.events, logs=self.proxy[offer_h2].tmaster.logs)
        assert no_failed_flows

        successful_flows = len([k for k in fs.keys() if k[3] == 200]) >= 1
        if not successful_flows:
            write_protocol(offer_h2, domain, url, fs=fs, events=self.proxy[offer_h2].tmaster.events, logs=self.proxy[offer_h2].tmaster.logs)
        assert successful_flows

        for k, flow in [(k, f) for k, f in fs.items() if k[3] == 200]:
            success = flow.error is None and flow.request and flow.response
            if not success:
                write_protocol(offer_h2, domain, url, fs=fs, events=self.proxy[offer_h2].tmaster.events, logs=self.proxy[offer_h2].tmaster.logs)
            assert success

        for msg in self.proxy[offer_h2].tmaster.logs:
            assert 'Traceback' not in msg.msg


if __name__ == '__main__':
    if platform.platform().startswith('Linux'):
        opts = options.Options(
            listen_port=0,
            upstream_cert=True,
            ssl_insecure=True,
            verbosity='debug',
            flow_detail=99,
            http2=True,
        )
        opts.cadir = os.path.expanduser("~/.mitmproxy")
        tmaster = tservers.TestMaster(opts)
        proxy = tservers.ProxyThread(tmaster)
        proxy.start()
        proxy.shutdown()

        os.makedirs(os.path.expanduser('~/.pki/nssdb'))

        subprocess.run(['certutil',
                        '-d', os.path.expanduser('~/.pki/nssdb'),
                        '-A',
                        '-t', 'TC',
                        '-n', 'mitmproxy-ca',
                        '-i', os.path.expanduser('~/.mitmproxy/mitmproxy-ca-cert.pem'),
        ])
        subprocess.run(['wget',
                        'https://chromedriver.storage.googleapis.com/2.35/chromedriver_linux64.zip',
                        '--directory-prefix', os.path.expanduser('~/'),
        ])
        subprocess.run(['unzip',
                        os.path.expanduser('~/chromedriver_linux64.zip'),
                        '-d', os.path.expanduser('~/'),
        ])
        subprocess.run(['chmod',
                        '+x',
                        os.path.expanduser('~/chromedriver'),
        ])

    os.environ['SMOKE_TEST_TIMESTAMP'] = time.strftime("%Y%m%d-%H%M")
    os.makedirs('tmp/{}'.format(os.environ['SMOKE_TEST_TIMESTAMP']), exist_ok=True)
    if os.path.islink('tmp/latest'):
        os.remove('tmp/latest')
    os.symlink(os.environ['SMOKE_TEST_TIMESTAMP'], 'tmp/latest')
    pytest.main(args=['-s',
                      '-v',
                      '-x',
                      # '-n', '16',
                      '--no-flaky-report',
                      *sys.argv
                      ])
