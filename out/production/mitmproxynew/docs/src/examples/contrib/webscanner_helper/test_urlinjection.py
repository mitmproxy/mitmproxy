import json
from unittest import mock

from mitmproxy import flowfilter
from mitmproxy.test import tflow
from mitmproxy.test import tutils

from examples.contrib.webscanner_helper.urlinjection import InjectionGenerator, HTMLInjection, RobotsInjection, \
    SitemapInjection, \
    UrlInjectionAddon, logger

index = json.loads(
    "{\"http://example.com:80\": {\"/\": {\"GET\": [301]}}, \"http://www.example.com:80\": {\"/test\": {\"POST\": [302]}}}")


class TestInjectionGenerator:

    def test_inject(self):
        f = tflow.tflow(resp=tutils.tresp())
        injection_generator = InjectionGenerator()
        injection_generator.inject(index=index, flow=f)
        assert True


class TestHTMLInjection:

    def test_inject_not404(self):
        html_injection = HTMLInjection()
        f = tflow.tflow(resp=tutils.tresp())

        with mock.patch.object(logger, 'warning') as mock_warning:
            html_injection.inject(index, f)
        assert mock_warning.called

    def test_inject_insert(self):
        html_injection = HTMLInjection(insert=True)
        f = tflow.tflow(resp=tutils.tresp())
        assert "example.com" not in str(f.response.content)
        html_injection.inject(index, f)
        assert "example.com" in str(f.response.content)

    def test_inject_insert_body(self):
        html_injection = HTMLInjection(insert=True)
        f = tflow.tflow(resp=tutils.tresp())
        f.response.text = "<body></body>"
        assert "example.com" not in str(f.response.content)
        html_injection.inject(index, f)
        assert "example.com" in str(f.response.content)

    def test_inject_404(self):
        html_injection = HTMLInjection()
        f = tflow.tflow(resp=tutils.tresp())
        f.response.status_code = 404
        assert "example.com" not in str(f.response.content)
        html_injection.inject(index, f)
        assert "example.com" in str(f.response.content)


class TestRobotsInjection:

    def test_inject_not404(self):
        robots_injection = RobotsInjection()
        f = tflow.tflow(resp=tutils.tresp())

        with mock.patch.object(logger, 'warning') as mock_warning:
            robots_injection.inject(index, f)
        assert mock_warning.called

    def test_inject_404(self):
        robots_injection = RobotsInjection()
        f = tflow.tflow(resp=tutils.tresp())
        f.response.status_code = 404
        assert "Allow: /test" not in str(f.response.content)
        robots_injection.inject(index, f)
        assert "Allow: /test" in str(f.response.content)


class TestSitemapInjection:

    def test_inject_not404(self):
        sitemap_injection = SitemapInjection()
        f = tflow.tflow(resp=tutils.tresp())

        with mock.patch.object(logger, 'warning') as mock_warning:
            sitemap_injection.inject(index, f)
        assert mock_warning.called

    def test_inject_404(self):
        sitemap_injection = SitemapInjection()
        f = tflow.tflow(resp=tutils.tresp())
        f.response.status_code = 404
        assert "<url><loc>http://example.com:80/</loc></url>" not in str(f.response.content)
        sitemap_injection.inject(index, f)
        assert "<url><loc>http://example.com:80/</loc></url>" in str(f.response.content)


class TestUrlInjectionAddon:

    def test_init(self, tmpdir):
        tmpfile = tmpdir.join("tmpfile")
        with open(tmpfile, "w") as tfile:
            json.dump(index, tfile)
        flt = f"~u .*/site.html$"
        url_injection = UrlInjectionAddon(f"~u .*/site.html$", tmpfile, HTMLInjection(insert=True))
        assert "http://example.com:80" in url_injection.url_store
        fltr = flowfilter.parse(flt)
        f = tflow.tflow(resp=tutils.tresp())
        f.request.url = "http://example.com/site.html"
        assert fltr(f)
        assert "http://example.com:80" not in str(f.response.content)
        url_injection.response(f)
        assert "http://example.com:80" in str(f.response.content)
