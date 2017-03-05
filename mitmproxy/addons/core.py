"""
    The core addon is responsible for verifying core settings that are not
    checked by other addons.
"""
from mitmproxy import exceptions
from mitmproxy.utils import human


class Core:
    def configure(self, options, updated):
        if "body_size_limit" in updated and options.body_size_limit:
            try:
                options._processed["body_size_limit"] = human.parse_size(
                    options.body_size_limit
                )
            except ValueError as e:
                raise exceptions.OptionsError(
                    "Invalid body size limit specification: %s" %
                    options.body_size_limit
                )
