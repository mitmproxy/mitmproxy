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
from urllib.request import urlopen

logger = logging.getLogger(__name__)

DEFAULT_BUNDLE_URL = "https://oisp.dev/spec/v0.1/oisp-spec-bundle.json"
DEFAULT_CACHE_DIR = Path.home() / ".oximy"
CACHE_FILENAME = "bundle_cache.json"

# Local registry path (for development)
# This is relative to the mitmproxy repo root
LOCAL_BUNDLE_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "registry"
    / "dist"
    / "oximy-bundle.json"
)
LOCAL_WEBSITES_PATH = (
    Path(__file__).parent.parent.parent.parent / "registry" / "websites.json"
)
LOCAL_APPS_PATH = Path(__file__).parent.parent.parent.parent / "registry" / "apps.json"


@dataclass
class CompiledDomainPattern:
    """A compiled regex pattern for matching dynamic domains."""

    pattern_str: str
    compiled: re.Pattern[str]
    provider_id: str


# Local overrides for website features not yet in the remote bundle
# This allows us to add new endpoint patterns without waiting for bundle updates
# NOTE: All website-specific configs should be in websites.json, not hardcoded here
LOCAL_WEBSITE_OVERRIDES: dict[str, dict[str, Any]] = {}


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

        # Get websites from bundle and merge local overrides
        websites = data.get("registry", {}).get("websites", {})
        websites = cls._apply_local_overrides(websites)

        # Get apps from bundle and merge local apps.json configs
        apps = data.get("registry", {}).get("apps", {})
        apps = cls._apply_apps_json(apps)

        return cls(
            domain_lookup=data.get("domain_lookup", {}),
            domain_patterns=domain_patterns,
            providers=data.get("providers", {}),
            parsers=data.get("parsers", {}),
            models=data.get("models", {}),
            apps=apps,
            websites=websites,
            bundle_version=data.get("bundle_version", "unknown"),
            loaded_at=time.time(),
        )

    @classmethod
    def _apply_local_overrides(
        cls, websites: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Apply local feature overrides and parser configs to websites."""
        import copy

        result = copy.deepcopy(websites)

        # Apply hardcoded overrides (file_download, subscription endpoints)
        for website_id, overrides in LOCAL_WEBSITE_OVERRIDES.items():
            if website_id not in result:
                continue  # Only extend existing websites

            # Merge features
            if "features" in overrides:
                if "features" not in result[website_id]:
                    result[website_id]["features"] = {}
                result[website_id]["features"].update(overrides["features"])
                logger.debug(
                    f"Applied local overrides to {website_id}: {list(overrides['features'].keys())}"
                )

        # Load parser configs from local websites.json
        result = cls._apply_websites_json(result)

        return result

    @classmethod
    def _apply_websites_json(
        cls, websites: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Load and merge parser configs from local websites.json."""
        if not LOCAL_WEBSITES_PATH.exists():
            logger.debug(f"Local websites.json not found at {LOCAL_WEBSITES_PATH}")
            return websites

        try:
            with open(LOCAL_WEBSITES_PATH, encoding="utf-8") as f:
                local_data = json.load(f)

            local_websites = local_data.get("websites", {})
            logger.info(
                f"Loading parser configs from websites.json: {list(local_websites.keys())}"
            )

            for website_id, local_website in local_websites.items():
                if website_id not in websites:
                    # Add new website entirely
                    websites[website_id] = local_website
                    logger.debug(f"Added website from websites.json: {website_id}")
                else:
                    # Merge features with parser configs
                    local_features = local_website.get("features", {})
                    if "features" not in websites[website_id]:
                        websites[website_id]["features"] = {}

                    for feature_name, local_feature in local_features.items():
                        if feature_name not in websites[website_id]["features"]:
                            websites[website_id]["features"][feature_name] = (
                                local_feature
                            )
                        else:
                            # Merge parser config into existing feature
                            if "parser" in local_feature:
                                websites[website_id]["features"][feature_name][
                                    "parser"
                                ] = local_feature["parser"]
                                logger.debug(
                                    f"Merged parser config for {website_id}/{feature_name}"
                                )

            return websites
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load websites.json: {e}")
            return websites

    @classmethod
    def _apply_apps_json(
        cls, apps: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Load and merge parser configs from local apps.json."""
        if not LOCAL_APPS_PATH.exists():
            logger.debug(f"Local apps.json not found at {LOCAL_APPS_PATH}")
            return apps

        try:
            with open(LOCAL_APPS_PATH, encoding="utf-8") as f:
                local_data = json.load(f)

            local_apps = local_data.get("apps", {})
            logger.info(
                f"Loading parser configs from apps.json: {list(local_apps.keys())}"
            )

            for app_id, local_app in local_apps.items():
                if app_id not in apps:
                    # Add new app entirely
                    apps[app_id] = local_app
                    logger.debug(f"Added app from apps.json: {app_id}")
                else:
                    # Merge api_domains if present
                    if "api_domains" in local_app:
                        apps[app_id]["api_domains"] = local_app["api_domains"]
                        logger.debug(f"Merged api_domains for app {app_id}")

                    # Merge features with parser configs
                    local_features = local_app.get("features", {})
                    if "features" not in apps[app_id]:
                        apps[app_id]["features"] = {}

                    for feature_name, local_feature in local_features.items():
                        if feature_name not in apps[app_id]["features"]:
                            apps[app_id]["features"][feature_name] = local_feature
                            logger.debug(
                                f"Added feature {feature_name} for app {app_id}"
                            )
                        else:
                            # Merge parser config into existing feature
                            if "parser" in local_feature:
                                apps[app_id]["features"][feature_name]["parser"] = (
                                    local_feature["parser"]
                                )
                                logger.debug(
                                    f"Merged parser config for {app_id}/{feature_name}"
                                )
                            # Merge patterns if present
                            if "patterns" in local_feature:
                                apps[app_id]["features"][feature_name]["patterns"] = (
                                    local_feature["patterns"]
                                )
                                logger.debug(
                                    f"Merged patterns for {app_id}/{feature_name}"
                                )

            return apps
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load apps.json: {e}")
            return apps

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
        max_age_hours: float = 24.0,
        local_bundle_path: Path | None = None,
    ):
        self.bundle_url = bundle_url
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.max_age_hours = max_age_hours
        self.local_bundle_path = local_bundle_path or LOCAL_BUNDLE_PATH
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
        """Load bundle from local registry (development mode)."""
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
        """Fetch bundle from the configured URL."""
        logger.debug(f"Fetching bundle from {self.bundle_url}")
        try:
            with urlopen(self.bundle_url, timeout=30) as response:
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
