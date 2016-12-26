#!/usr/bin/env python3

# example command:
#   > py.test smoke_test_moz_top500.py -s n 4

"""
Install on Ubuntu 16.04:
sudo apt-get install python3-pip python3-dev python3-venv libffi-dev libssl-dev libtiff5-dev libjpeg8-dev zlib1g-dev libwebp-dev

sudo apt-get build-dep nghttp2
wget https://github.com/nghttp2/nghttp2/releases/download/v1.17.0/nghttp2-1.17.0.tar.bz2
tar xvjf nghttp2-1.17.0.tar.bz2
cd nghttp2-1.17.0
autoreconf -i
automake
autoreconf
./configure --disable-app
make
sudo make install
sudo ldconfig

sudo apt-get build-dep curl
wget https://curl.haxx.se/download/curl-7.52.1.tar.bz2
tar xvjf curl-7.52.1.tar.bz2
cd curl-7.52.1
./configure
make



export PATH=/home/ubuntu/chromedriver_linux64:$PATH
"""

import tempfile
import sys
import os
import csv
import subprocess
import queue
import threading
import glob
import time

import pytest
import selenium
from flaky import flaky
from selenium import webdriver
from pyvirtualdisplay import Display

from mitmproxy import controller, flow, proxy, options
from mitmproxy.proxy.server import ProxyServer
from mitmproxy.proxy.config import ProxyConfig
from mitmproxy.addons.disable_h2c_upgrade import DisableH2CleartextUpgrade
from test.mitmproxy import tservers


def generate_combinations():
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
            # (True, domain, "http://{}".format(domain)),
            # (True, domain, "http://www.{}".format(domain)),
            # (True, domain, "https://{}".format(domain)),
            # (True, domain, "https://www.{}".format(domain)),
        ] for domain in domains]
    return [item for sublist in l for item in sublist]


def write_protocol(offer_h2, domain, url, message=None, stdout=None, stderr=None, fs=None, tlog=None):
    u = 'h2_' if offer_h2 else ''
    u += 'http' if url.startswith('http://') else 'https'
    u += '_www.' if '://www.' in url else '_'
    u += domain
    with open("tmp/{}/{}.txt".format(os.environ['SMOKE_TEST_TIMESTAMP'], u), mode='a') as file:
        file.write("################################################################################\n".format(domain))
        file.write("domain: {}\n".format(domain))
        file.write("url: {}\n".format(url))

        if message:
            file.write("{}\n".format(message))

        file.write("\n\n")
        if fs:
            file.write("flows in mitmproxy:\n")
            for fl in fs.keys():
                file.write("{}\n".format(fl))
        else:
            file.write("<no flows in mitmproxy>\n")

        if stdout:
            file.write("\n\n")
            file.write("stdout:\n{}\n".format(stdout.decode()))
        if stderr:
            file.write("\n\n")
            file.write("stderr:\n{}\n".format(stderr.decode()))

        if tlog:
            file.write("\n\n")
            for msg in tlog:
                file.write(msg)
                file.write("\n")

        file.write("\n\n")


class TestSmokeCurl(object):
    @classmethod
    def setup_class(cls):
        opts = options.Options(
            listen_port=0,
            no_upstream_cert=False,
            ssl_insecure=True,
            verbosity=99,
            flow_detail=99,
        )
        opts.cadir = os.path.join(tempfile.gettempdir(), "mitmproxy")
        config = ProxyConfig(opts)

        tmaster = tservers.TestMaster(opts, config)
        tmaster.clear_log()
        cls.proxy = proxy = tservers.ProxyThread(tmaster)
        cls.proxy.start()

        cls.display = Display(visible=0, size=(800, 600))
        cls.display.start()

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--proxy-server={}:{}'.format('127.0.0.1', cls.proxy.port))
        cls.driver = webdriver.Chrome(chrome_options=chrome_options)


    @classmethod
    def teardown_class(cls):
        cls.proxy.shutdown()
        cls.driver.close()
        cls.display.stop()

    @flaky(max_runs=3)
    @pytest.mark.parametrize('offer_h2, domain, url', generate_combinations())
    def test_smoke_curl(self, offer_h2, domain, url):
        self.proxy.tmaster.clear_log()
        self.proxy.tmaster.reset([DisableH2CleartextUpgrade()])

        cmd = [
            # '/usr/local/opt/curl/bin/curl',
            '/home/ubuntu/curl-7.51.0/src/curl',
            '--location',
            '--insecure',
            '--silent',
            '--verbose',
            '--fail',
            '--http2' if offer_h2 else '--http1.1',
            '--alpn' if offer_h2 else '--no-alpn',
            '--npn' if offer_h2 else '--no-npn',
            '--cookie', 'tmp/cookie_jar',
            '--cookie-jar', 'tmp/cookie_jar',
            '--header', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            '--header', 'Accept-Encoding: gzip, deflate',
            '--header', 'Accept-Language: en,en-US;q=0.8,de;q=0.6',
            '--user-agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0',
        ]

        for i in range(3):
            try:
                subprocess.run(cmd + [url], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=True)
            except:
                if i == 2:
                    pytest.skip('{}: curl failed, so skip testing through mitmproxy'.format(url))

        output = b''
        negotiated_http2 = False
        c = cmd + [
            '--proxy', 'http://127.0.0.1:{}'.format(self.proxy.port),
            url
        ]
        try:
            self.driver.get(url)
            # assert self.driver.title

            # c = subprocess.run(c, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=True)
            # output += c.stderr
            # if b'ALPN, server accepted to use h2' in c.stderr:
            #     negotiated_http2 = True
        except subprocess.CalledProcessError as e:
            write_protocol(offer_h2,
                           domain,
                           url,
                           'curl failed: returncode={}'.format(e.returncode),
                           stdout=e.stdout,
                           stderr=e.stderr,
                           tlog=self.proxy.tmaster.tlog)
            pytest.fail("curl failed: {}, returncode: {}".format(url, e.returncode))
        except subprocess.TimeoutExpired as e:
            write_protocol(offer_h2,
                           domain,
                           url,
                           'timeout',
                           stdout=e.stdout,
                           stderr=e.stderr,
                           tlog=self.proxy.tmaster.tlog)
            pytest.fail("timeout: {}".format(url))
        except selenium.common.exceptions.TimeoutException:
            write_protocol(offer_h2,
                           domain,
                           url,
                           'selenium timeout',
                           tlog=self.proxy.tmaster.tlog)
            pytest.fail("timeout: {}".format(url))


        fs = {}
        for f in self.proxy.tmaster.state.flows:
            if f.response:
                fs[(f.request.http_version, f.request.scheme, f.request.host, f.response.status_code)] = f

        no_failed_flows = len([k for k in fs.keys() if k[3] >= 500]) == 0
        if not no_failed_flows:
            write_protocol(offer_h2, domain, url, stdout=output, fs=fs, tlog=self.proxy.tmaster.tlog)
        assert no_failed_flows

        successful_flows = len([k for k in fs.keys() if k[3] == 200]) >= 1
        if not successful_flows:
            write_protocol(offer_h2, domain, url, stdout=output, fs=fs, tlog=self.proxy.tmaster.tlog)
        assert successful_flows

        if negotiated_http2:
            successful_flows = len([k for k in fs.keys() if k[0] == 'HTTP/2.0' and k[3] >= 200 and k[3] <= 399]) >= 1
            if not successful_flows:
                write_protocol(offer_h2, domain, url, stdout=output, fs=fs, tlog=self.proxy.tmaster.tlog)
            assert successful_flows

        for k, flow in [(k, f) for k, f in fs.items() if k[3] == 200]:
            success = flow.error is None and flow.request and flow.response
            if not success:
                write_protocol(offer_h2, domain, url, stdout=output, fs=fs, tlog=self.proxy.tmaster.tlog)
            assert success

        for m in self.proxy.tmaster.tlog:
            assert 'Traceback' not in m


if __name__ == '__main__':
    os.environ['SMOKE_TEST_TIMESTAMP'] = time.strftime("%Y%m%d-%H%M")
    print(os.environ['SMOKE_TEST_TIMESTAMP'])
    os.makedirs('tmp/{}'.format(os.environ['SMOKE_TEST_TIMESTAMP']), exist_ok=True)
    if os.path.islink('tmp/latest'):
        os.remove('tmp/latest')
    os.symlink(os.environ['SMOKE_TEST_TIMESTAMP'], 'tmp/latest')
    pytest.main(args=['-s',
                      '-v',
                    #   '-x',
                    #   '-n', '16',
                      '--show-progress',
                      '--no-flaky-report',
                      *sys.argv
                      ])
