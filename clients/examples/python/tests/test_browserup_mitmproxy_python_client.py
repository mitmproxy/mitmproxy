#!/usr/bin/env python

"""Tests for `browserup_mitmproxy_python_client_usage_example` package."""

import unittest

import BrowserUpMitmProxyClient
from BrowserUpMitmProxyClient.api import browser_up_proxy_api
from BrowserUpMitmProxyClient.model.counter import Counter


class TestBrowserupMitmProxyPythonClient(unittest.TestCase):
    def setUp(self):
        """Configure client"""
        self.configuration = BrowserUpMitmProxyClient.Configuration(
            host="http://localhost:8088"
        )
        self.api_client = BrowserUpMitmProxyClient.ApiClient(self.configuration)
        self.api_instance = browser_up_proxy_api.BrowserUpProxyApi(self.api_client)
        self.api_instance.reset_har_log()

    def tearDown(self):
        """Tear down test fixtures, if any."""

    def test_health_check(self):
        """Test adding counter using client."""
        try:
            self.api_instance.healthcheck()
        except BrowserUpMitmProxyClient.ApiException as e:
            print("Exception when calling BrowserUpProxyApi->healthcheck: %s\n" % e)
            raise e

    def test_get_har(self):
        """Test adding counter using client."""
        try:
            har = self.api_instance.get_har_log()
        except BrowserUpMitmProxyClient.ApiException as e:
            print("Exception when calling BrowserUpProxyApi->healthcheck: %s\n" % e)
            raise e

        self.assertIsNotNone(har)
        self.assertIsNotNone(har.log.entries)

    def test_adding_counter_using_client(self):
        """Test adding counter using client."""
        counter = Counter(
            value=3.14,
            name="some counter",
        )
        try:
            self.api_instance.add_counter(counter)
        except BrowserUpMitmProxyClient.ApiException as e:
            print("Exception when calling BrowserUpProxyApi->add_counter: %s\n" % e)
            raise e

        har = self.api_instance.get_har_log()

        self.assertTrue(
            any(
                item.name == counter.name and item.value == counter.value
                for item in har.log.pages[0].counters
            )
        )
