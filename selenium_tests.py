#!/usr/bin/env python3

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from pyvirtualdisplay import Display

# PROXY_HOST = 'http://127.0.0.1'
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 8080

# fp = webdriver.FirefoxProfile()
# fp.set_preference("network.proxy.type", 1)
# fp.set_preference("network.proxy.http", PROXY_HOST)
# fp.set_preference("network.proxy.http_port", PROXY_PORT)
# fp.set_preference("network.proxy.ssl", PROXY_HOST)
# fp.set_preference("network.proxy.ssl_port", PROXY_PORT)
# fp.set_preference("network.proxy.share_proxy_settings", True)
# fp.update_preferences()
# driver = webdriver.Firefox(firefox_profile=fp)

display = Display(visible=0, size=(800, 600))
display.start()

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--proxy-server={}:{}'.format(PROXY_HOST, PROXY_PORT))
driver = webdriver.Chrome(chrome_options=chrome_options)

try:
    driver.get("http://www.python.org")
    print(driver.title)
    assert "Python" in driver.title



finally:
    driver.close()
    display.stop()
