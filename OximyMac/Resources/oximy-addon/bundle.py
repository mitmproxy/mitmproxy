"""
OISP Bundle loading and caching.

Fetches the OISP spec bundle from URL, caches locally,
and provides structured access to domain lookups, parsers, etc.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import ProxyHandler
from urllib.request import build_opener
from urllib.request import urlopen

logger = logging.getLogger(__name__)

DEFAULT_BUNDLE_URL = "https://oisp.dev/spec/v0.1/oisp-spec-bundle.json"
DEFAULT_CACHE_DIR = Path.home() / ".oximy"
CACHE_FILENAME = "bundle_cache.json"

# Production builds: No local bundle path - always fetch from remote URL
# Local bundle is only used in development when running from mitmproxy source
LOCAL_BUNDLE_PATH = None


@dataclass
class CompiledDomainPattern:
    """A compiled regex pattern for matching dynamic domains."""

    pattern_str: str
    compiled: re.Pattern[str]
    provider_id: str


@dataclass
class OISPBundle:
    """
    Parsed OISP bundle with efficient lookup structures.
    """

    # Direct domain -> provider_id mapping
    domain_lookup: dict[str, str]

    # Compiled regex patterns for dynamic domains (Azure, Bedrock)
    domain_patterns: list[CompiledDomainPattern]

    # Provider definitions: provider_id -> {api_format, name, ...}
    providers: dict[str, dict[str, Any]]

    # Parser configurations: api_format -> {request: {...}, response: {...}}
    parsers: dict[str, dict[str, Any]]

    # Model definitions: model_id -> {costs, capabilities, ...}
    models: dict[str, dict[str, Any]]

    # App registry: app_id -> {signatures, endpoints, ...}
    apps: dict[str, dict[str, Any]]

    # Website registry: website_id -> {domains, endpoints, ...}
    websites: dict[str, dict[str, Any]]

    # Metadata
    bundle_version: str
    loaded_at: float  # Unix timestamp

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OISPBundle:
        """Parse raw bundle JSON into structured OISPBundle."""
        # Compile domain patterns
        domain_patterns = []
        for pattern_def in data.get("domain_patterns", []):
            try:
                compiled = re.compile(pattern_def["pattern"])
                domain_patterns.append(
                    CompiledDomainPattern(
                        pattern_str=pattern_def["pattern"],
                        compiled=compiled,
                        provider_id=pattern_def["provider"],
                    )
                )
            except re.error as e:
                logger.warning(
                    f"Invalid domain pattern '{pattern_def['pattern']}': {e}"
                )

        return cls(
            domain_lookup=data.get("domain_lookup", {}),
            domain_patterns=domain_patterns,
            providers=data.get("providers", {}),
            parsers=data.get("parsers", {}),
            models=data.get("models", {}),
            apps=data.get("registry", {}).get("apps", {}),
            websites=data.get("registry", {}).get("websites", {}),
            bundle_version=data.get("bundle_version", "unknown"),
            loaded_at=time.time(),
        )

    def is_stale(self, max_age_hours: float) -> bool:
        """Check if the bundle is older than max_age_hours."""
        age_seconds = time.time() - self.loaded_at
        return age_seconds > (max_age_hours * 3600)

    def get_provider_api_format(self, provider_id: str) -> str | None:
        """Get the API format for a provider."""
        provider = self.providers.get(provider_id)
        if provider:
            return provider.get("api_format")
        return None


class BundleLoader:
    """
    Manages OISP bundle loading, caching, and refresh.

    Load priority:
    1. Local bundle (registry/dist/oximy-bundle.json) - for development
    2. Cached bundle (if fresh)
    3. Remote URL
    4. Stale cache (fallback)
    """

    def __init__(
        self,
        bundle_url: str = DEFAULT_BUNDLE_URL,
        cache_dir: Path | None = None,
        max_age_hours: float = 0.5,  # 30 minutes default for production
        local_bundle_path: Path | None = None,
    ):
        self.bundle_url = bundle_url
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.max_age_hours = max_age_hours
        # In production, LOCAL_BUNDLE_PATH is None, so no local bundle loading
        self.local_bundle_path = local_bundle_path if local_bundle_path else LOCAL_BUNDLE_PATH
        self._bundle: OISPBundle | None = None

    @property
    def cache_path(self) -> Path:
        return self.cache_dir / CACHE_FILENAME

    def load(self, force_refresh: bool = False) -> OISPBundle:
        """
        Load the bundle, using cache if available and fresh.

        Priority:
        1. Local bundle (for development)
        2. Cached bundle (if fresh)
        3. Remote URL
        4. Stale cache (fallback)

        Args:
            force_refresh: If True, skip cache and local (fetch from URL)

        Returns:
            Loaded OISPBundle
        """
        # Try local bundle first (development mode)
        if not force_refresh:
            local = self._load_from_local()
            if local:
                logger.info(f"Using local bundle (version {local.bundle_version})")
                self._bundle = local
                return local

        # Try cache (unless force refresh)
        if not force_refresh:
            cached = self._load_from_cache()
            if cached and not cached.is_stale(self.max_age_hours):
                logger.info(f"Using cached bundle (version {cached.bundle_version})")
                self._bundle = cached
                return cached

        # Fetch from URL
        try:
            bundle = self._fetch_from_url()
            self._save_to_cache(bundle)
            self._bundle = bundle
            logger.info(f"Loaded bundle from URL (version {bundle.bundle_version})")
            return bundle
        except Exception as e:
            logger.warning(f"Failed to fetch bundle from URL: {e}")
            # Fall back to stale cache if available
            if self._bundle:
                logger.info("Using previously loaded bundle")
                return self._bundle
            cached = self._load_from_cache()
            if cached:
                logger.info("Using stale cached bundle as fallback")
                self._bundle = cached
                return cached
            raise RuntimeError("No bundle available (fetch failed, no cache)") from e

    def _load_from_local(self) -> OISPBundle | None:
        """Load bundle from local registry (development mode only)."""
        # In production, local_bundle_path is None - skip local loading
        if self.local_bundle_path is None:
            return None
        if not self.local_bundle_path.exists():
            return None

        try:
            with open(self.local_bundle_path, encoding="utf-8") as f:
                data = json.load(f)
            bundle = OISPBundle.from_dict(data)
            logger.debug(f"Loaded local bundle from {self.local_bundle_path}")
            return bundle
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load local bundle: {e}")
            return None

    def _fetch_from_url(self) -> OISPBundle:
        """Fetch bundle from the configured URL, bypassing system proxy."""
        logger.debug(f"Fetching bundle from {self.bundle_url}")
        try:
            # IMPORTANT: Use a direct connection without proxy
            # This is necessary because when mitmproxy restarts, the system proxy
            # may still be enabled but the proxy isn't running yet, causing
            # "Connection refused" errors
            no_proxy_handler = ProxyHandler({})  # Empty dict = no proxy
            opener = build_opener(no_proxy_handler)
            with opener.open(self.bundle_url, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except URLError as e:
            raise RuntimeError(f"Failed to fetch bundle: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in bundle: {e}") from e

        return OISPBundle.from_dict(data)

    def _load_from_cache(self) -> OISPBundle | None:
        """Load bundle from local cache file."""
        if not self.cache_path.exists():
            return None

        try:
            with open(self.cache_path, encoding="utf-8") as f:
                cache_data = json.load(f)

            # Cache stores both the bundle and metadata
            bundle_data = cache_data.get("bundle", cache_data)
            loaded_at = cache_data.get("loaded_at", 0)

            bundle = OISPBundle.from_dict(bundle_data)
            bundle.loaded_at = loaded_at
            return bundle
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Failed to load bundle from cache: {e}")
            return None

    def _save_to_cache(self, bundle: OISPBundle) -> None:
        """Save bundle to local cache file."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # Store original bundle data plus load timestamp
            cache_data = {
                "loaded_at": bundle.loaded_at,
                "bundle": self._bundle_to_dict(bundle),
            }

            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, separators=(",", ":"))

            logger.debug(f"Saved bundle to cache: {self.cache_path}")
        except OSError as e:
            logger.warning(f"Failed to save bundle to cache: {e}")

    def _bundle_to_dict(self, bundle: OISPBundle) -> dict[str, Any]:
        """Convert bundle back to dict for caching."""
        return {
            "bundle_version": bundle.bundle_version,
            "domain_lookup": bundle.domain_lookup,
            "domain_patterns": [
                {"pattern": p.pattern_str, "provider": p.provider_id}
                for p in bundle.domain_patterns
            ],
            "providers": bundle.providers,
            "parsers": bundle.parsers,
            "models": bundle.models,
            "registry": {
                "apps": bundle.apps,
                "websites": bundle.websites,
            },
        }

    @property
    def bundle(self) -> OISPBundle | None:
        """Get the currently loaded bundle."""
        return self._bundle
