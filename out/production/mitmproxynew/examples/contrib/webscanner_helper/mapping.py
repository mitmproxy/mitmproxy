import copy
import logging
import typing
from typing import Dict

from bs4 import BeautifulSoup

from mitmproxy.http import HTTPFlow
from examples.contrib.webscanner_helper.urldict import URLDict

NO_CONTENT = object()


class MappingAddonConfig:
    HTML_PARSER = "html.parser"


class MappingAddon:
    """ The mapping add-on can be used in combination with web application scanners to reduce their false positives.

    Many web application scanners produce false positives caused by dynamically changing content of web applications
    such as the current time or current measurements. When testing for injection vulnerabilities, web application
    scanners are tricked into thinking they changed the content with the injected payload. In realty, the content of
    the web application changed notwithstanding the scanner's input. When the mapping add-on is used to map the content
    to a fixed value, these false positives can be avoided.
    """

    OPT_MAPPING_FILE = "mapping_file"
    """File where urls and css selector to mapped content is stored.

    Elements will be replaced with the content given in this file. If the content is none it will be set to the first
    seen value.

    Example:

        {
            "http://10.10.10.10": {
                "body": "My Text"
            },
            "URL": {
                "css selector": "Replace with this"
            }
        }
    """

    OPT_MAP_PERSISTENT = "map_persistent"
    """Whether to store all new content in the configuration file."""

    def __init__(self, filename: str, persistent: bool = False) -> None:
        """ Initializes the mapping add-on

        Args:
            filename: str that provides the name of the file in which the urls and css selectors to mapped content is
                stored.
            persistent: bool that indicates whether to store all new content in the configuration file.

        Example:
            The file in which the mapping config is given should be in the following format:
            {
                "http://10.10.10.10": {
                    "body": "My Text"
                },
                "<URL>": {
                    "<css selector>": "Replace with this"
                }
            }
        """
        self.filename = filename
        self.persistent = persistent
        self.logger = logging.getLogger(self.__class__.__name__)
        with open(filename) as f:
            self.mapping_templates = URLDict.load(f)

    def load(self, loader):
        loader.add_option(
            self.OPT_MAPPING_FILE, str, "",
            "File where replacement configuration is stored."
        )
        loader.add_option(
            self.OPT_MAP_PERSISTENT, bool, False,
            "Whether to store all new content in the configuration file."
        )

    def configure(self, updated):
        if self.OPT_MAPPING_FILE in updated:
            self.filename = updated[self.OPT_MAPPING_FILE]
            with open(self.filename) as f:
                self.mapping_templates = URLDict.load(f)

        if self.OPT_MAP_PERSISTENT in updated:
            self.persistent = updated[self.OPT_MAP_PERSISTENT]

    def replace(self, soup: BeautifulSoup, css_sel: str, replace: BeautifulSoup) -> None:
        """Replaces the content of soup that matches the css selector with the given replace content."""
        for content in soup.select(css_sel):
            self.logger.debug(f"replace \"{content}\" with \"{replace}\"")
            content.replace_with(copy.copy(replace))

    def apply_template(self, soup: BeautifulSoup, template: Dict[str, typing.Union[BeautifulSoup]]) -> None:
        """Applies the given mapping template to the given soup."""
        for css_sel, replace in template.items():
            mapped = soup.select(css_sel)
            if not mapped:
                self.logger.warning(f"Could not find \"{css_sel}\", can not freeze anything.")
            else:
                self.replace(soup, css_sel, BeautifulSoup(replace, features=MappingAddonConfig.HTML_PARSER))

    def response(self, flow: HTTPFlow) -> None:
        """If a response is received, check if we should replace some content. """
        try:
            templates = self.mapping_templates[flow]
            res = flow.response
            if res is not None:
                encoding = res.headers.get("content-encoding", "utf-8")
                content_type = res.headers.get("content-type", "text/html")

                if "text/html" in content_type and encoding == "utf-8":
                    content = BeautifulSoup(res.content, MappingAddonConfig.HTML_PARSER)
                    for template in templates:
                        self.apply_template(content, template)
                    res.content = content.encode(encoding)
                else:
                    self.logger.warning(f"Unsupported content type '{content_type}' or content encoding '{encoding}'")
        except KeyError:
            pass

    def done(self) -> None:
        """Dumps all new content into the configuration file if self.persistent is set."""
        if self.persistent:

            # make sure that all items are strings and not soups.
            def value_dumper(value):
                store = {}
                if value is None:
                    return "None"
                try:
                    for css_sel, soup in value.items():
                        store[css_sel] = str(soup)
                except:
                    raise RuntimeError(value)
                return store

            with open(self.filename, "w") as f:
                self.mapping_templates.dump(f, value_dumper)
