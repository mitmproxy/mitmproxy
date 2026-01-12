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

from models import MatchResult
from process import ClientProcess

if TYPE_CHECKING:
    from bundle import OISPBundle
    from mitmproxy.http import HTTPFlow

logger = logging.getLogger(__name__)


class TrafficMatcher:
    """
    Classifies HTTP traffic against OISP bundle definitions.

    Classification hierarchy:
    1. apps - desktop apps identified by process signature + API patterns
    2. domain_lookup - exact domain match to known AI API providers
    3. domain_patterns - regex match for dynamic domains (Azure, Bedrock)
    4. websites - known AI websites with endpoint patterns
    5. Unknown - drop silently
    """

    def __init__(self, bundle: OISPBundle):
        self.bundle = bundle
        self._website_domain_index: dict[str, str] = self._build_website_domain_index()
        self._app_signature_index: dict[str, str] = self._build_app_signature_index()
        self._app_domain_index: dict[str, set[str]] = self._build_app_domain_index()

    def _build_website_domain_index(self) -> dict[str, str]:
        """Build reverse index from domain -> website_id."""
        index: dict[str, str] = {}
        for website_id, website in self.bundle.websites.items():
            for domain in website.get("api_domains", []):
                index[domain] = website_id
        return index

    def _build_app_signature_index(self) -> dict[str, str]:
        """Build reverse index from bundle_id/exe/app_name -> app_id."""
        index: dict[str, str] = {}
        for app_id, app in self.bundle.apps.items():
            # Index by app name for macOS path matching (e.g., "Granola.app" in path)
            app_name = app.get("name", "")
            if app_name:
                # Store "AppName.app" pattern for macOS path matching
                index[f"{app_name}.app"] = app_id
                # Also store lowercase variant
                index[f"{app_name.lower()}.app"] = app_id

            signatures = app.get("signatures", {})
            for platform, sig in signatures.items():
                if "bundle_id" in sig:
                    index[sig["bundle_id"]] = app_id
                if "exe" in sig:
                    # Store both original case and lowercase for Windows matching
                    index[sig["exe"]] = app_id
                    index[sig["exe"].lower()] = app_id
        return index

    def _build_app_domain_index(self) -> dict[str, set[str]]:
        """Build index of which API domains each app uses."""
        index: dict[str, set[str]] = {}
        for app_id, app in self.bundle.apps.items():
            domains = app.get("api_domains", [])
            if domains:
                index[app_id] = set(domains)
        return index

    def match(
        self, flow: HTTPFlow, client_process: ClientProcess | None = None
    ) -> MatchResult:
        """
        Classify a flow against OISP definitions.

        Args:
            flow: The HTTP flow to classify
            client_process: Optional process info for app matching

        Returns:
            MatchResult with classification and metadata
        """
        host = flow.request.pretty_host
        path = flow.request.path
        method = flow.request.method

        # 1. App matching (highest priority - requires process info)
        result = self._match_app(host, path, method, client_process)
        if result:
            return result

        # 2. Direct API provider lookup (exact domain match)
        result = self._match_domain_lookup(host)
        if result:
            return result

        # 3. Regex patterns (Azure, Bedrock, etc.)
        result = self._match_domain_patterns(host)
        if result:
            return result

        # 4. Website matching
        result = self._match_website(host, path)
        if result:
            return result

        # 5. Unknown - drop
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

    def _match_app(
        self,
        host: str,
        path: str,
        method: str,
        client_process: ClientProcess | None,
    ) -> MatchResult | None:
        """
        Match traffic from known desktop apps.

        Apps are matched by:
        1. Process signature (bundle_id on macOS, exe on Windows)
        2. API domain restrictions (if specified)
        3. Endpoint URL patterns (like website features)
        """
        if not client_process:
            return None

        # Find app by process signature
        app_id = self._find_app_by_process(client_process)
        if not app_id:
            return None

        app = self.bundle.apps.get(app_id)
        if not app:
            return None

        # Check if app has features with parser configs
        features = app.get("features", {})
        if not features:
            return None

        # Check domain restriction if present
        allowed_domains = self._app_domain_index.get(app_id)
        if allowed_domains and not self._domain_matches_pattern(host, allowed_domains):
            return None

        # Check feature patterns
        for feature_name, feature_def in features.items():
            patterns = feature_def.get("patterns", [])
            for pattern in patterns:
                # Check method if specified
                pattern_method = pattern.get("method")
                if pattern_method and pattern_method.upper() != method.upper():
                    continue

                if self._matches_endpoint_pattern(path, pattern):
                    logger.debug(
                        f"App match: {app_id}/{feature_name} for {client_process.name}"
                    )
                    return MatchResult(
                        classification="full_trace",
                        source_type="app",
                        source_id=app_id,
                        provider_id=None,
                        api_format=f"{app_id}_app",
                        endpoint=feature_name,
                    )

        return None

    def _find_app_by_process(self, client_process: ClientProcess) -> str | None:
        """
        Find app_id by matching process info against signatures.

        Matches against:
        - Process path containing app name or bundle_id (macOS apps)
        - Process name matching exe name (Windows apps)
        - Parent process name (for helper processes)
        """
        # Check by path (contains app name like "Granola.app" on macOS)
        if client_process.path:
            for signature, app_id in self._app_signature_index.items():
                if signature in client_process.path:
                    logger.debug(
                        f"Matched app {app_id} by signature '{signature}' in path"
                    )
                    return app_id

        # Check by process name (Windows exe)
        if client_process.name:
            name_lower = client_process.name.lower()
            if name_lower in self._app_signature_index:
                return self._app_signature_index[name_lower]

        # Check by parent process name (for helper processes)
        if client_process.parent_name:
            parent_lower = client_process.parent_name.lower()
            if parent_lower in self._app_signature_index:
                return self._app_signature_index[parent_lower]

        return None

    def _domain_matches_pattern(self, host: str, allowed: set[str]) -> bool:
        """Check if host matches any of the allowed domain patterns."""
        for domain in allowed:
            if domain.startswith("*."):
                # Wildcard pattern - match suffix
                suffix = domain[2:]
                if host.endswith(suffix) or host == suffix:
                    return True
            elif host == domain:
                return True
        return False

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
                    # Use website-specific api_format for parsing
                    api_format = website.get("api_format", f"{website_id}_web")
                    return MatchResult(
                        classification="full_trace",
                        source_type="website",
                        source_id=website_id,
                        provider_id=None,  # Websites may use multiple providers
                        api_format=api_format,
                        endpoint=feature_name,
                    )

        # Website matched but no specific endpoint - drop it
        # We only care about actual AI conversation endpoints, not gizmos/settings/etc.
        return MatchResult(classification="drop")

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
