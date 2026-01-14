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
from urllib.parse import urlparse

from mitmproxy.addons.oximy.models import MatchResult
from mitmproxy.addons.oximy.process import ClientProcess

if TYPE_CHECKING:
    from mitmproxy.addons.oximy.bundle import OISPBundle
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
            # Support both "api_domains" (current spec) and "domains" (legacy)
            domains = website.get("api_domains") or website.get("domains", [])
            for domain in domains:
                index[domain] = website_id
        logger.debug(f"Website domain index: {list(index.keys())}")
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

        # Extract referer/origin headers for website matching
        referer = flow.request.headers.get("referer") or flow.request.headers.get(
            "referrer"
        )
        origin = flow.request.headers.get("origin")

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

        # 4. Website matching (uses referer/origin to identify website)
        result = self._match_website(host, path, referer, origin)
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
            classification="full_extraction",
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
                    classification="full_extraction",
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
            logger.debug(f"_match_app: no client_process")
            return None

        # Find app by process signature
        app_id = self._find_app_by_process(client_process)
        logger.debug(f"_match_app: client={client_process.name}, path={client_process.path}, found app_id={app_id}")
        if not app_id:
            return None

        app = self.bundle.apps.get(app_id)
        if not app:
            logger.debug(f"_match_app: app_id {app_id} not in bundle")
            return None

        # Check if app has features with parser configs
        features = app.get("features", {})
        if not features:
            logger.debug(f"_match_app: app {app_id} has no features")
            return None

        # Check domain restriction if present
        allowed_domains = self._app_domain_index.get(app_id)
        logger.debug(f"_match_app: app {app_id} allowed_domains={allowed_domains}, checking host={host}")
        if allowed_domains and not self._domain_matches_pattern(host, allowed_domains):
            logger.debug(f"_match_app: host {host} not in allowed domains")
            return None

        # Check feature patterns
        for feature_name, feature_def in features.items():
            patterns = feature_def.get("patterns", [])
            for pattern in patterns:
                # Check method if specified
                pattern_method = pattern.get("method")
                logger.debug(
                    f"App {app_id} checking pattern: method={pattern_method} vs request={method}, "
                    f"url_pattern={pattern.get('url')}, path={path}"
                )
                if pattern_method and pattern_method.upper() != method.upper():
                    logger.debug(f"  -> method mismatch, skipping")
                    continue

                matches = self._matches_endpoint_pattern(path, pattern)
                logger.debug(f"  -> endpoint pattern match: {matches}")
                if matches:
                    # Determine classification based on parser presence
                    has_parser = "parser" in feature_def
                    classification = "full_extraction" if has_parser else "feature_extraction"
                    feature_type = feature_def.get("type")

                    logger.debug(
                        f"App match: {app_id}/{feature_name} for {client_process.name} "
                        f"(classification={classification})"
                    )
                    return MatchResult(
                        classification=classification,
                        source_type="app",
                        source_id=app_id,
                        provider_id=None,
                        api_format=f"{app_id}_app",
                        endpoint=feature_name,
                        feature_type=feature_type,
                    )

        # App matched but no specific feature endpoint - metadata_only
        return MatchResult(
            classification="metadata_only",
            source_type="app",
            source_id=app_id,
        )

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

    def _matches_query_params(self, query_string: str, required_params: list[str]) -> bool:
        """
        Check if query string contains all required parameters.

        Args:
            query_string: The query string portion of URL (without leading ?)
            required_params: List of required params, e.g., ["tree=True", "format=json"]

        Returns:
            True if all required params are present in query string
        """
        if not required_params:
            return True

        # Parse query string into key=value pairs
        # Handle both "key=value" and just "key" formats
        query_pairs = set()
        if query_string:
            for part in query_string.split("&"):
                # Store the full key=value pair for exact matching
                query_pairs.add(part)
                # Also store lowercase version for case-insensitive matching
                query_pairs.add(part.lower())

        # Check each required param
        for required in required_params:
            # Check exact match or case-insensitive match
            if required not in query_pairs and required.lower() not in query_pairs:
                return False

        return True

    def _extract_host_from_url(self, url: str | None) -> str | None:
        """
        Extract hostname from a URL.

        Examples:
            "https://chat.openai.com/c/123" -> "chat.openai.com"
            "https://gemini.google.com" -> "gemini.google.com"
            None -> None
        """
        if not url:
            return None
        try:
            parsed = urlparse(url)
            # netloc contains the host (and port if present)
            # For "https://chat.openai.com:443/path", netloc = "chat.openai.com:443"
            host = parsed.netloc
            if host:
                # Strip port if present
                if ":" in host:
                    host = host.split(":")[0]
                return host
            return None
        except Exception:
            return None

    def _match_website(
        self, host: str, path: str, referer: str | None, origin: str | None
    ) -> MatchResult | None:
        """
        Check if traffic is from a known AI website.

        L1: Check if referer/origin host matches a website's api_domains
            - If NO match -> return None (not from a known AI website)
            - If YES -> website_id found, continue

        L2: Check if destination host + path matches any feature patterns
            - If NO match -> return metadata_only (we know the website, not the feature)
            - If YES -> feature found, continue

        L3: Check if feature has a parser
            - If NO -> return feature_extraction
            - If YES -> return full_extraction
        """
        # L1: Extract host from referer/origin and check against website domains
        referer_host = self._extract_host_from_url(referer)
        origin_host = self._extract_host_from_url(origin)

        # Try referer first, then origin
        website_id = None
        if referer_host:
            website_id = self._website_domain_index.get(referer_host)
        if not website_id and origin_host:
            website_id = self._website_domain_index.get(origin_host)

        if not website_id:
            # Not from a known AI website
            return None

        website = self.bundle.websites.get(website_id)
        if not website:
            return None

        logger.debug(
            f"Website L1 match: {website_id} (referer={referer_host}, origin={origin_host})"
        )

        # L2: Check if destination host + path matches any feature patterns
        features = website.get("features", {})
        for feature_name, feature_def in features.items():
            patterns = feature_def.get("patterns", [])
            for pattern in patterns:
                if self._matches_endpoint_pattern(path, pattern):
                    # L3: Determine classification based on parser presence
                    # full_extraction: feature matched AND has parser config
                    # feature_extraction: feature matched BUT no parser (we know the feature type)
                    has_parser = "parser" in feature_def
                    classification = "full_extraction" if has_parser else "feature_extraction"

                    # Use website-specific api_format for parsing
                    api_format = website.get("api_format", f"{website_id}_web")
                    feature_type = feature_def.get("type")  # e.g., "chat", "asset_creation"

                    logger.debug(
                        f"Website L2+L3 match: {website_id}/{feature_name} "
                        f"(classification={classification}, feature_type={feature_type})"
                    )

                    return MatchResult(
                        classification=classification,
                        source_type="website",
                        source_id=website_id,
                        provider_id=None,  # Websites may use multiple providers
                        api_format=api_format,
                        endpoint=feature_name,
                        feature_type=feature_type,
                    )

        # L1 passed but L2 failed: Website matched but no specific feature endpoint
        # We know it's traffic from an AI website but don't know which specific feature
        logger.debug(
            f"Website metadata_only: {website_id} (no feature pattern matched for path={path})"
        )
        return MatchResult(
            classification="metadata_only",
            source_type="website",
            source_id=website_id,
        )

    def _matches_endpoint_pattern(self, path: str, pattern: dict) -> bool:
        """Check if path matches an endpoint pattern definition."""
        url_pattern = pattern.get("url", "")
        required_query_params = pattern.get("query_params", [])

        if not url_pattern:
            return False

        # Split path and query string
        if "?" in path:
            path_without_query, query_string = path.split("?", 1)
        else:
            path_without_query = path
            query_string = ""

        logger.debug(
            f"    _matches_endpoint_pattern: path_without_query={path_without_query}, "
            f"query_string={query_string}, required_params={required_query_params}"
        )

        # Check required query params if specified
        if required_query_params:
            params_match = self._matches_query_params(query_string, required_query_params)
            logger.debug(f"    query params match: {params_match}")
            if not params_match:
                return False

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
