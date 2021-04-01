import abc
import html
import json
import logging

from mitmproxy import flowfilter
from mitmproxy.http import HTTPFlow

logger = logging.getLogger(__name__)


class InjectionGenerator:
    """Abstract class for an generator of the injection content in order to inject the URL index."""
    ENCODING = "UTF8"

    @abc.abstractmethod
    def inject(self, index, flow: HTTPFlow):
        """Injects the given URL index into the given flow."""
        pass


class HTMLInjection(InjectionGenerator):
    """Injects the URL index either by creating a new HTML page or by appending is to an existing page."""

    def __init__(self, insert: bool = False):
        """Initializes the HTMLInjection.

        Args:
            insert: boolean to decide whether to insert the URL index to an existing page (True) or to create a new
                page containing the URL index.
        """
        self.insert = insert

    @classmethod
    def _form_html(cls, url):
        return f"<form action=\"{url}\" method=\"POST\"></form>"

    @classmethod
    def _link_html(cls, url):
        return f"<a href=\"{url}\">link to {url}</a>"

    @classmethod
    def index_html(cls, index):
        link_htmls = []
        for scheme_netloc, paths in index.items():
            for path, methods in paths.items():
                url = scheme_netloc + path
                if "POST" in methods:
                    link_htmls.append(cls._form_html(url))

                if "GET" in methods:
                    link_htmls.append(cls._link_html(url))
        return "</ br>".join(link_htmls)

    @classmethod
    def landing_page(cls, index):
        return (
                "<head><meta charset=\"UTF-8\"></head><body>"
                + cls.index_html(index)
                + "</body>"
        )

    def inject(self, index, flow: HTTPFlow):
        if flow.response is not None:
            if flow.response.status_code != 404 and not self.insert:
                logger.warning(
                    f"URL '{flow.request.url}' didn't return 404 status, "
                    f"index page would overwrite valid page.")
            elif self.insert:
                content = (flow.response
                           .content
                           .decode(self.ENCODING, "backslashreplace"))
                if "</body>" in content:
                    content = content.replace("</body>", self.index_html(index) + "</body>")
                else:
                    content += self.index_html(index)
                flow.response.content = content.encode(self.ENCODING)
            else:
                flow.response.content = (self.landing_page(index)
                                         .encode(self.ENCODING))


class RobotsInjection(InjectionGenerator):
    """Injects the URL index by creating a new robots.txt including the URLs."""

    def __init__(self, directive="Allow"):
        self.directive = directive

    @classmethod
    def robots_txt(cls, index, directive="Allow"):
        lines = ["User-agent: *"]
        for scheme_netloc, paths in index.items():
            for path, methods in paths.items():
                lines.append(directive + ": " + path)
        return "\n".join(lines)

    def inject(self, index, flow: HTTPFlow):
        if flow.response is not None:
            if flow.response.status_code != 404:
                logger.warning(
                    f"URL '{flow.request.url}' didn't return 404 status, "
                    f"index page would overwrite valid page.")
            else:
                flow.response.content = self.robots_txt(index,
                                                        self.directive).encode(
                    self.ENCODING)


class SitemapInjection(InjectionGenerator):
    """Injects the URL index by creating a new sitemap including the URLs."""

    @classmethod
    def sitemap(cls, index):
        lines = [
            "<?xml version=\"1.0\" encoding=\"UTF-8\"?><urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"]
        for scheme_netloc, paths in index.items():
            for path, methods in paths.items():
                url = scheme_netloc + path
                lines.append(f"<url><loc>{html.escape(url)}</loc></url>")
        lines.append("</urlset>")
        return "\n".join(lines)

    def inject(self, index, flow: HTTPFlow):
        if flow.response is not None:
            if flow.response.status_code != 404:
                logger.warning(
                    f"URL '{flow.request.url}' didn't return 404 status, "
                    f"index page would overwrite valid page.")
            else:
                flow.response.content = self.sitemap(index).encode(self.ENCODING)


class UrlInjectionAddon:
    """ The UrlInjection add-on can be used in combination with web application scanners to improve their crawling
    performance.

    The given URls will be injected into the web application. With this, web application scanners can find pages to
    crawl much easier. Depending on the Injection generator, the URLs will be injected at different places of the
    web application. It is possible to create a landing page which includes the URL (HTMLInjection()), to inject the
    URLs to an existing page (HTMLInjection(insert=True)), to create a robots.txt containing the URLs
    (RobotsInjection()) or to create a sitemap.xml which includes the URLS (SitemapInjection()).
    It is necessary that the web application scanner can find the newly created page containing the URL index. For
    example, the newly created page can be set as starting point for the web application scanner.
    The URL index needed for the injection can be generated by the UrlIndex Add-on.
    """

    def __init__(self, flt: str, url_index_file: str,
                 injection_gen: InjectionGenerator):
        """Initializes the UrlIndex add-on.

        Args:
            flt: mitmproxy filter to decide on which pages the URLs will be injected (str).
            url_index_file: Path to the file which includes the URL index in JSON format (e.g. generated by the UrlIndexAddon), given
                as str.
            injection_gen: InjectionGenerator that should be used to inject the URLs into the web application.
        """
        self.name = f"{self.__class__.__name__}-{injection_gen.__class__.__name__}-{self.__hash__()}"
        self.flt = flowfilter.parse(flt)
        self.injection_gen = injection_gen
        with open(url_index_file) as f:
            self.url_store = json.load(f)

    def response(self, flow: HTTPFlow):
        """Checks if the response matches the filter and such should be injected.
        Injects the URL index if appropriate.
        """
        if flow.response is not None:
            if self.flt is not None and self.flt(flow):
                self.injection_gen.inject(self.url_store, flow)
                flow.response.status_code = 200
                flow.response.headers["content-type"] = "text/html"
                logger.debug(f"Set status code to 200 and set content to logged "
                             f"urls. Method: {self.injection_gen}")
