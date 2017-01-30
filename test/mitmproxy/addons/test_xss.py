import unittest
from unittest import mock
from mitmproxy.addons import xss


class MockResponseOrRequest:
    def __init__(self, cookies):
        self.cookies = MockLoCT(cookies)
        self.content = "<html></html>"
        self.url = "https://example.com/index.html?q=1"


class MockLoCT:
    def __init__(self, cookies):
        self.fields = cookies


class MockCookieValue:
    def __init__(self, value):
        self.value = value


class MockFlow:
    def __init__(self):
        self.response = MockResponseOrRequest([("cookieName1", MockCookieValue("cookieValue1"))])
        self.request = MockResponseOrRequest([("cookieName2", "cookieValue2")])


class test_mitmXSS(unittest.TestCase):
    def test_getXSSInfo(self):
        # First type of exploit: <script>PAYLOAD</script>
        # Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><script>%s</script><html>" %
                                        xss.fullPayload,
                                        "https://example.com",
                                        "End of URL"),
                         {'Line': xss.fullPayload.decode('utf-8'),
                          'Exploit': '</script><script>alert(0)</script><script>',
                          'URL': 'https://example.com',
                          'Injection Point': "End of URL"})
        self.assertEqual(xss.getXSSInfo(b"<html><script>%s</script><html>" %
                                        xss.fullPayload.replace(b"'", b"%27").replace(b'"', b"%22"),
                                        "https://example.com",
                                        "End of URL"),
                         {'Line': xss.fullPayload.replace(b"'", b"%27").replace(b'"', b"%22").decode('utf-8'),
                          'Exploit': '</script><script>alert(0)</script><script>',
                          'URL': 'https://example.com',
                          'Injection Point': "End of URL"})
        # Non-Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><script>%s</script><html>" %
                                        xss.fullPayload.replace(b"'", b"%27").replace(b'"', b"%22").replace(b"/", b"%2F"),
                                        "https://example.com",
                                        "End of URL"),
                         None)
        # Second type of exploit: <script>t='PAYLOAD'</script>
        # Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><script>t='%s';</script></html>" %
                                        xss.fullPayload.replace(b"<", b"%3C").replace(b">", b"%3E").replace(b"\"", b"%22"),
                                        "https://example.com",
                                        "End of URL"),
                         {'Line': xss.fullPayload.replace(b"<", b"%3C").replace(b">", b"%3E").replace(b"\"", b"%22").decode('utf-8'),
                          'Exploit': "';alert(0);g='",
                          'URL': 'https://example.com',
                          'Injection Point': "End of URL"})
        # Non-Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><script>t='%s';</script></html>" %
                                        xss.fullPayload.replace(b"<", b"%3C").replace(b"\"", b"%22").replace(b"'", b"%22"),
                                        "https://example.com",
                                        "End of URL"),
                         None)
        # Third type of exploit: <script>t="PAYLOAD"</script>
        # Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><script>t=\"%s\";</script></html>" %
                                        xss.fullPayload.replace(b"<", b"%3C").replace(b">", b"%3E").replace(b"'", b"%27"),
                                        "https://example.com",
                                        "End of URL"),
                         {'Line': xss.fullPayload.replace(b"<", b"%3C").replace(b">", b"%3E").replace(b"'", b"%27").decode('utf-8'),
                          'Exploit': '";alert(0);g="',
                          'URL': 'https://example.com',
                          'Injection Point': "End of URL"})
        # Non-Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><script>t=\"%s\";</script></html>" %
                                        xss.fullPayload.replace(b"<", b"%3C").replace(b"'", b"%27").replace(b"\"", b"%22"),
                                        "https://example.com",
                                        "End of URL"),
                         None)
        # Fourth type of exploit: <a href='PAYLOAD'>Test</a>
        # Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><a href='%s'>Test</a></html>" %
                                        xss.fullPayload,
                                        "https://example.com",
                                        "End of URL"),
                         {'Line': xss.fullPayload.decode('utf-8'),
                          'Exploit': "'><script>alert(0)</script>",
                          'URL': 'https://example.com',
                          'Injection Point': "End of URL"})
        # Non-Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><a href='OtherStuff%s'>Test</a></html>" %
                                        xss.fullPayload.replace(b"'", b"%27"),
                                        "https://example.com",
                                        "End of URL"),
                         None)
        # Fifth type of exploit: <a href="PAYLOAD">Test</a>
        # Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><a href=\"%s\">Test</a></html>" %
                                        xss.fullPayload.replace(b"'", b"%27"),
                                        "https://example.com",
                                        "End of URL"),
                         {'Line': xss.fullPayload.replace(b"'", b"%27").decode('utf-8'),
                          'Exploit': "\"><script>alert(0)</script>",
                          'URL': 'https://example.com',
                          'Injection Point': "End of URL"})
        # Non-Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><a href=\"OtherStuff%s\">Test</a></html>" %
                                        xss.fullPayload.replace(b"'", b"%27").replace(b"\"", b"%22"),
                                        "https://example.com",
                                        "End of URL"),
                         None)
        # Sixth type of exploit: <a href=PAYLOAD>Test</a>
        # Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><a href=%s>Test</a></html>" %
                                        xss.fullPayload,
                                        "https://example.com",
                                        "End of URL"),
                         {'Line': xss.fullPayload.decode('utf-8'),
                          'Exploit': "><script>alert(0)</script>",
                          'URL': 'https://example.com',
                          'Injection Point': "End of URL"})
        # Non-Exploitable
        self.assertEqual(xss.getXSSInfo(b"<html><a href=OtherStuff%s>Test</a></html>" %
                                        xss.fullPayload.replace(b"<", b"%3C").replace(b">", b"%3E"),
                                        "https://example.com",
                                        "End of URL"),
                         None)
        # Seventh type of exploit: <html>PAYLOAD</html>
        # Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><b>%s</b></html>" %
                                        xss.fullPayload,
                                        "https://example.com",
                                        "End of URL"),
                         {'Line': xss.fullPayload.decode('utf-8'),
                          'Exploit': "<script>alert(0)</script>",
                          'URL': 'https://example.com',
                          'Injection Point': "End of URL"})
        # Non-Exploitable
        self.assertEqual(xss.getXSSInfo(b"<html><b>%s</b></html>" %
                                        xss.fullPayload.replace(b"<", b"%3C").replace(b">", b"%3E").replace(b"/", b"%2F"),
                                        "https://example.com",
                                        "End of URL"),
                         None)
        # Eighth type of exploit: <a href=PAYLOAD>Test</a>
        # Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><a href=%s>Test</a></html>" %
                                        xss.fullPayload.replace(b"<", b"%3C").replace(b">", b"%3E"),
                                        "https://example.com",
                                        "End of URL"),
                         {'Line': xss.fullPayload.replace(b"<", b"%3C").replace(b">", b"%3E").decode('utf-8'),
                          'Exploit': "Javascript:alert(0)",
                          'URL': 'https://example.com',
                          'Injection Point': "End of URL"})
        # Non-Exploitable:
        self.assertEqual(xss.getXSSInfo(b"<html><a href=OtherStuff%s>Test</a></html>" %
                                        xss.fullPayload.replace(b"<", b"%3C").replace(b">", b"%3E"),
                                        "https://example.com",
                                        "End of URL"),
                         None)

    def testInsideQuote(self):
        self.assertEqual(xss.insideQuote("'", b"no", 0, b"no"), False)
        self.assertEqual(xss.insideQuote("'", b"yes", 0, b"'yes'"), True)
        self.assertEqual(xss.insideQuote("'", b"yes", 1, b"'yes'otherJunk'yes'more"), True)
        self.assertEqual(xss.insideQuote("'", b"longStringNotInIt", 1, b"short"), False)

    def testPathsToText(self):
        self.assertEqual(xss.pathsToText("""<html><head><h1>STRING</h1></head>
                                            <script>STRING</script>
                                            <a href=STRING></a></html>""", "STRING"),
                         ["/html/head/h1", "/html/script"])
        self.assertEqual(xss.pathsToText("""<html></html>""", "STRING"), [])

    def mocked_requests(*args, headers=None, cookies=None):
        class MockResponse:
            def __init__(self, html, headers=None, cookies=None):
                self.text = html
        return MockResponse("<html>%s</html>" % xss.fullPayload)

    @mock.patch('requests.get', side_effect=mocked_requests)
    def testTestEndOfURLInjection(self, mocked_requests):
        self.assertEqual(xss.testEndOfURLInjection("<html></html>", "https://example.com/", {})[0],
                         {'Exploit': '<script>alert(0)</script>',
                          'Injection Point': 'End of URL',
                          'Line': '1029zxcs\\\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\\\3847asd',
                          'URL': 'https://example.com/1029zxcs\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\3847asd'})

    @mock.patch('requests.get', side_effect=mocked_requests)
    def testTestRefererInjection(self, mocked_requests):
        self.assertEqual(xss.testRefererInjection("<html></html>", "https://example.com/", {})[0],
                         {'Exploit': '<script>alert(0)</script>',
                          'Injection Point': 'Referer',
                          'Line': '1029zxcs\\\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\\\3847asd',
                          'URL': 'https://example.com/'})

    @mock.patch('requests.get', side_effect=mocked_requests)
    def testTestUserAgentInjection(self, mocked_requests):
        self.assertEqual(xss.testUserAgentInjection("<html></html>", "https://example.com/", {})[0],
                         {'Exploit': '<script>alert(0)</script>',
                          'Injection Point': 'User Agent',
                          'Line': '1029zxcs\\\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\\\3847asd',
                          'URL': 'https://example.com/'})

    @mock.patch('requests.get', side_effect=mocked_requests)
    def testTestQueryInjection(self, mocked_requests):
        self.assertEqual(xss.testQueryInjection("<html></html>", "https://example.com/vuln.php?cmd=ls", {})[0],
                         {'Exploit': '<script>alert(0)</script>',
                          'Injection Point': 'Query',
                          'URL': 'https://example.com/vuln.php?cmd=1029zxcs\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\3847asd',
                          'Line': '1029zxcs\\\'d"ao<ac>so[sb]po(pc)se;sl/bsl\\\\3847asd'})

    @mock.patch('mitmproxy.ctx.log')
    def testFindUnclaimedURLs(self, mocked_log):
        xss.findUnclaimedURLs("<html><script src=\"http://google.com\"></script></html>", "https://example.com")
        self.assertFalse(mocked_log.error.called)
        xss.findUnclaimedURLs("<html><script src=\"http://unclaimedDomainName.com\"></script></html>", "https://example.com")
        self.assertTrue(mocked_log.error.called)

    @mock.patch('mitmproxy.ctx.log')
    def testlogXSS(self, mocked_log):
        xss.logXSS(None)
        self.assertFalse(mocked_log.error.called)
        xss.logXSS({'Exploit': 'String',
                    'Injection Point': 'Location',
                    'URL': 'https://example.com',
                    'Line': 'Line of HTML'})
        mocked_log.error.assert_has_calls([mock.call('===== XSS Found ===='),
                                           mock.call('XSS URL: https://example.com'),
                                           mock.call('Injection Point: Location'),
                                           mock.call('Suggested Exploit: String'),
                                           mock.call('Line: Line of HTML')])

    def testGetCookies(self):
        mocked_flow = MockFlow()
        self.assertEqual(xss.getCookies(mocked_flow), {'cookieName1': 'cookieValue1', 'cookieName2': 'cookieValue2'})

    @mock.patch('mitmproxy.ctx.log')
    def testResponse(self, mocked_log):
        mocked_flow = MockFlow()
        xss.response(mocked_flow)
        self.assertFalse(mocked_log.error.called)

    @mock.patch('mitmproxy.ctx.log')
    def testlogSQLi(self, mocked_log):
        xss.logSQLiDict(None)
        self.assertFalse(mocked_log.error.called)
        xss.logSQLiDict({'URL': "https://example.com",
                         'Injection Point': "Location",
                         'Regex': "Oracle.*Driver",
                         'DBMS': "Oracle"})
        mocked_log.error.assert_has_calls([mock.call('===== SQLi Found ====='),
                                           mock.call('SQLi URL: https://example.com'),
                                           mock.call('Injection Point: Location'),
                                           mock.call('Regex used: Oracle.*Driver')])

    def testGetSQLiInfo(self):
        self.assertEqual(xss.getSQLiInfo("<html>SQL syntax MySQL</html>",
                                         "<html></html>",
                                         "https://example.com",
                                         "End of URL"),
                         {'URL': "https://example.com",
                          'Injection Point': "End of URL",
                          'Regex': "SQL syntax.*MySQL",
                          'DBMS': "MySQL"})
        self.assertEqual(xss.getSQLiInfo("<html>SQL syntax MySQL</html>",
                                         "<html>SQL syntax MySQL</html>",
                                         "https://example.com",
                                         "End of URL"),
                         None)


if __name__ == '__main__':
    unittest.main()
