import json
from dataclasses import dataclass

from mitmproxy import ctx
from mitmproxy.addonmanager import Loader
from mitmproxy.http import HTTPFlow

"""
This extension implements support for domain fronting.

Usage:

   mitmproxy -s examples/contrib/domain_fronting.py --set domainfrontingfile=./domain_fronting.json

In the following basic example, www.example.com will be used for DNS requests and SNI values
but the secret.example.com value will be used for the HTTP host header:

    {
        "mappings": [
            {
                "patterns": ["secret.example.com"],
                "server": "www.example.com"
            }
        ]
    }

The following example demonstrates the usage of a wildcard (at the beginning of the domain name only):

    {
        "mappings": [
            {
                "patterns": ["*.foo.example.com"],
                "server": "www.example.com"
            }
        ]
    }

In the following example, we override the HTTP host header:

    {
        "mappings": [
            {
                "patterns": ["foo.example"],
                "server": "www.example.com",
                "host": "foo.proxy.example.com"
            }
        ]
    }

"""


@dataclass
class Mapping:
    server: str | None
    host: str | None


class HttpsDomainFronting:
    # configurations for regular ("foo.example.com") mappings:
    star_mappings: dict[str, Mapping]

    # Configurations for star ("*.example.com") mappings:
    strict_mappings: dict[str, Mapping]

    def __init__(self) -> None:
        self.strict_mappings = {}
        self.star_mappings = {}

    def _resolve_addresses(self, host: str) -> Mapping | None:
        mapping = self.strict_mappings.get(host)
        if mapping is not None:
            return mapping

        index = 0
        while True:
            index = host.find(".", index)
            if index == -1:
                break
            super_domain = host[(index + 1) :]
            mapping = self.star_mappings.get(super_domain)
            if mapping is not None:
                return mapping
            index += 1

        return None

    def load(self, loader: Loader) -> None:
        loader.add_option(
            name="domainfrontingfile",
            typespec=str,
            default="./fronting.json",
            help="Domain fronting configuration file",
        )

    def _load_configuration_file(self, filename: str) -> None:
        config = json.load(open(filename))
        strict_mappings: dict[str, Mapping] = {}
        star_mappings: dict[str, Mapping] = {}
        for mapping in config["mappings"]:
            item = Mapping(server=mapping.get("server"), host=mapping.get("host"))
            for pattern in mapping["patterns"]:
                if pattern.startswith("*."):
                    star_mappings[pattern[2:]] = item
                else:
                    strict_mappings[pattern] = item
        self.strict_mappings = strict_mappings
        self.star_mappings = star_mappings

    def configure(self, updated: set[str]) -> None:
        if "domainfrontingfile" in updated:
            domain_fronting_file = ctx.options.domainfrontingfile
            self._load_configuration_file(domain_fronting_file)

    def request(self, flow: HTTPFlow) -> None:
        if not flow.request.scheme == "https":
            return
        # We use the host header to dispatch the request:
        target = flow.request.host_header
        if target is None:
            return
        mapping = self._resolve_addresses(target)
        if mapping is not None:
            flow.request.host = mapping.server or target
            flow.request.headers["host"] = mapping.host or target


addons = [HttpsDomainFronting()]
