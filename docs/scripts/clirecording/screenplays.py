#!/usr/bin/env python3

import os
import requests
import threading
from urllib3.exceptions import InsecureRequestWarning
from clidirector import CliDirector

os.environ['HTTP_PROXY'] = os.environ['http_proxy'] = 'http://127.0.0.1:8080/'
os.environ['HTTPS_PROXY'] = os.environ['https_proxy'] = 'http://127.0.0.1:8080/'
os.environ['NO_PROXY'] = os.environ['no_proxy'] = '127.0.0.1,localhost,.local'
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


def generate_sample_requests():
    requests.get('https://mitmproxy.org', verify=False)
    requests.get('https://mitmproxy.org/vote/', verify=False)


def record_simple(d: CliDirector):
    tmux = d.start_session(width=120, height=24)
    window = tmux.attached_window

    window.set_window_option("window-status-current-format", "mitmproxy Tutorial: Intercept Requests")

    d.exec("mitmproxy")
    d.pause(5)
    generate_sample_requests()
    d.pause(1)

    d.start_recording("recordings/recording_simple.cast")
    d.popup("    mitmproxy Tutorial: Intercept Requests    ")
    d.pause(2)

    d.message("Step 1: Press 'i'.")
    d.type("i")
    d.pause(0.5)

    d.message("Step 2: Enter '~u /vote/' and then press 'Enter'.")
    d.exec("~u /vote/")
    d.pause(2)

    d.message("Step 3: Generate a sample flow to mitmproxy.org/vote")
    threading.Thread(target=lambda: requests.get('https://mitmproxy.org/vote/', verify=False)).start()
    d.pause(2)

    d.message("Step 4: Put the focus (>>) on the intercepted flow.")
    d.press_key("Down", count=2)
    d.pause(1)

    d.message("Press 'a' to resume this flow without making any changes.")
    d.type("a")

    d.pause(2)
    d.popup("    THE END    ")
    d.end()



if __name__ == '__main__':
    director = CliDirector()
    record_simple(director)
