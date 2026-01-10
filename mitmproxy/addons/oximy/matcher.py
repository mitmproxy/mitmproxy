"""
Traffic classification against OISP bundle.

Matches HTTP flows against domain lookups, regex patterns,
app signatures, and website definitions.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from typing import TYPE_CHECKING

from mitmproxy.addons.oximy.types import MatchResult

if TYPE_CHECKING:
    from mitmproxy.addons.oximy.bundle import OISPBundle
    from mitmproxy.http import HTTPFlow

logger = logging.getLogger(__name__)


class TrafficMatcher:
    """
    Classifies HTTP traffic against OISP bundle definitions.

    Classification hierarchy:
    1. domain_lookup - exact domain match to known AI API providers
    2. domain_patterns - regex match for dynamic domains (Azure, Bedrock)
    3. websites - known AI websites with endpoint patterns
    4. Unknown - drop silently
    """

    def __init__(self, bundle: OISPBundle):
        self.bundle = bundle
        self._website_domain_index: dict[str, str] = self._build_website_domain_index()

    def _build_website_domain_index(self) -> dict[str, str]:
        """Build reverse index from domain -> website_id."""
        index: dict[str, str] = {}
        for website_id, website in self.bundle.websites.items():
            for domain in website.get("domains", []):
                index[domain] = website_id
        return index

    def match(self, flow: HTTPFlow) -> MatchResult:
        """
        Classify a flow against OISP definitions.

        Args:
            flow: The HTTP flow to classify

        Returns:
            MatchResult with classification and metadata
        """
        host = flow.request.pretty_host
        path = flow.request.path

        # 1. Direct API provider lookup (exact domain match)
        result = self._match_domain_lookup(host)
        if result:
            return result

        # 2. Regex patterns (Azure, Bedrock, etc.)
        result = self._match_domain_patterns(host)
        if result:
            return result

        # 3. Website matching
        result = self._match_website(host, path)
        if result:
            return result

        # 4. Unknown - drop
        return MatchResult(classification="drop")

    def _match_domain_lookup(self, host: str) -> MatchResult | None:
        """Check if host is in the domain_lookup table."""
        provider_id = self.bundle.domain_lookup.get(host)
        if not provider_id:
            return None

        api_format = self.bundle.get_provider_api_format(provider_id)

        return MatchResult(
            classification="full_trace",
            source_type="api",
            source_id=provider_id,
            provider_id=provider_id,
            api_format=api_format,
            endpoint=None,
        )

    def _match_domain_patterns(self, host: str) -> MatchResult | None:
        """Check if host matches any compiled regex patterns."""
        for pattern in self.bundle.domain_patterns:
            if pattern.compiled.match(host):
                api_format = self.bundle.get_provider_api_format(pattern.provider_id)

                return MatchResult(
                    classification="full_trace",
                    source_type="api",
                    source_id=pattern.provider_id,
                    provider_id=pattern.provider_id,
                    api_format=api_format,
                    endpoint=None,
                )
        return None

    def _match_website(self, host: str, path: str) -> MatchResult | None:
        """Check if host/path matches a known website definition."""
        website_id = self._website_domain_index.get(host)
        if not website_id:
            return None

        website = self.bundle.websites.get(website_id)
        if not website:
            return None

        # Check feature endpoints
        features = website.get("features", {})
        for feature_name, feature_def in features.items():
            patterns = feature_def.get("patterns", [])
            for pattern in patterns:
                if self._matches_endpoint_pattern(path, pattern):
                    # Website has parser? -> full_trace, else identifiable
                    # For now, treat all website matches as full_trace
                    # (we'll parse what we can)
                    return MatchResult(
                        classification="full_trace",
                        source_type="website",
                        source_id=website_id,
                        provider_id=None,  # Websites may use multiple providers
                        api_format=None,  # Will need website-specific parsing
                        endpoint=feature_name,
                    )

        # Website matched but no specific endpoint - identifiable only
        return MatchResult(
            classification="identifiable",
            source_type="website",
            source_id=website_id,
            provider_id=None,
            api_format=None,
            endpoint=None,
        )

    def _matches_endpoint_pattern(self, path: str, pattern: dict) -> bool:
        """Check if path matches an endpoint pattern definition."""
        url_pattern = pattern.get("url", "")
        method = pattern.get("method")  # Not used for path matching, but available

        if not url_pattern:
            return False

        # Strip query string from path for matching
        path_without_query = path.split("?")[0]

        # Convert glob-style pattern to regex
        # Pattern like "**/backend-api/conversation" should match:
        # - "/backend-api/conversation"
        # - "/backend-api/f/conversation" (ChatGPT uses /f/ prefix)
        # Handle ** as "any path prefix"
        if url_pattern.startswith("**/"):
            # Match anywhere in path - the suffix can appear anywhere
            suffix = url_pattern[3:]  # Remove **/
            # Check if suffix is contained in path or path ends with it
            if suffix in path_without_query or path_without_query.endswith(suffix):
                return True
            # Also check if the final segment matches (e.g., "conversation" in "/f/conversation")
            suffix_parts = suffix.split("/")
            path_parts = path_without_query.split("/")
            if suffix_parts and path_parts:
                # Check if last part of suffix matches last part of path
                if path_parts[-1] == suffix_parts[-1]:
                    return True

        # Standard glob matching
        return fnmatch.fnmatch(path_without_query, url_pattern)


def matches_glob_pattern(path: str, pattern: str) -> bool:
    """
    Match a path against a glob-style pattern.

    Supports:
    - * matches any single path segment
    - ** matches any number of path segments
    - ? matches any single character
    """
    # Convert glob to regex
    regex_pattern = pattern
    regex_pattern = regex_pattern.replace("**", "<<<DOUBLESTAR>>>")
    regex_pattern = re.escape(regex_pattern)
    regex_pattern = regex_pattern.replace("<<<DOUBLESTAR>>>", ".*")
    regex_pattern = regex_pattern.replace(r"\*", "[^/]*")
    regex_pattern = regex_pattern.replace(r"\?", ".")
    regex_pattern = f"^{regex_pattern}$"

    return bool(re.match(regex_pattern, path))
