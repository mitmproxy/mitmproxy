from __future__ import print_function
import requests
import time

n = 100
url = "http://192.168.1.1/"
proxy = "http://192.168.1.115:8080/"

start = time.time()
for _ in range(n):
    requests.get(url, allow_redirects=False, proxies=dict(http=proxy))
    print(".", end="")
t_mitmproxy = time.time() - start

print("\r\nTotal time with mitmproxy: {}".format(t_mitmproxy))


start = time.time()
for _ in range(n):
    requests.get(url, allow_redirects=False)
    print(".", end="")
t_without = time.time() - start

print("\r\nTotal time without mitmproxy: {}".format(t_without))
