"""
    The core addon is responsible for verifying core settings that are not
    checked by other addons.
"""
from mitmproxy import exceptions
from mitmproxy import options
from mitmproxy import platform
from mitmproxy.utils import human


class Core:
    def configure(self, opts, updated):
        if "body_size_limit" in updated and opts.body_size_limit:
            try:
                opts._processed["body_size_limit"] = human.parse_size(
                    opts.body_size_limit
                )
            except ValueError as e:
                raise exceptions.OptionsError(
                    "Invalid body size limit specification: %s" %
                    opts.body_size_limit
                )
        if "mode" in updated:
            mode = opts.mode
            if mode.startswith("reverse:") or mode.startswith("upstream:"):
                spec = options.get_mode_spec(mode)
                if not spec:
                    raise exceptions.OptionsError(
                        "Invalid mode specification: %s" % mode
                    )
            elif mode == "transparent":
                if not platform.original_addr:
                    raise exceptions.OptionsError(
                        "Transparent mode not supported on this platform."
                    )
            elif mode not in ["regular", "socks5"]:
                raise exceptions.OptionsError(
                    "Invalid mode specification: %s" % mode
                )
