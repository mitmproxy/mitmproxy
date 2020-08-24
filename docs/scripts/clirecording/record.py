#!/usr/bin/env python3

import os
import requests
from urllib3.exceptions import InsecureRequestWarning

from clidirector import MitmCliDirector
import screenplays

os.environ['HTTP_PROXY'] = os.environ['http_proxy'] = 'http://127.0.0.1:8080/'
os.environ['HTTPS_PROXY'] = os.environ['https_proxy'] = 'http://127.0.0.1:8080/'
os.environ['NO_PROXY'] = os.environ['no_proxy'] = '127.0.0.1,localhost,.local'
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


if __name__ == '__main__':
    director = MitmCliDirector()
    screenplays.record_user_interface(director)
    screenplays.record_user_interface2(director)
