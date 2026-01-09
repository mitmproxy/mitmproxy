"""
Oximy OISP Addon for mitmproxy

Captures AI API traffic based on OISP bundle whitelists,
normalizes events, and writes to JSONL files.
"""

from mitmproxy.addons.oximy.addon import OximyAddon

__all__ = ["OximyAddon"]

# For use with `mitmdump -s .../oximy/__init__.py`
addons = [OximyAddon()]
