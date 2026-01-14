"""
Oximy Configuration Module

Central configuration for DEV vs PROD mode.

Configuration priority (highest to lowest):
1. Environment variables (OXIMY_DEV, OXIMY_API_URL, etc.)
2. Local config file (~/.oximy/dev.json)
3. Production defaults (safe fallback)

Usage:
    from config import config

    if config.DEV_MODE:
        # Development behavior

    bundle_url = config.BUNDLE_URL
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Production defaults (NEVER change these - they are the safe fallback)
_PROD_DEFAULTS: dict[str, Any] = {
    "DEV_MODE": False,
    "BUNDLE_URL": "https://oisp.dev/spec/v0.1/oisp-spec-bundle.json",
    "API_URL": "https://api.oximy.com/api/v1",
    "AUTO_PROXY_ENABLED": False,  # Production: proxy managed externally
    "PROXY_HOST": "127.0.0.1",
    "PROXY_PORT": "8088",
}

# Dev overrides (applied when DEV_MODE=true)
_DEV_OVERRIDES: dict[str, Any] = {
    "BUNDLE_URL": None,  # None = use local bundle file
    "API_URL": "http://localhost:4000/api/v1",
    "AUTO_PROXY_ENABLED": True,
}

LOCAL_CONFIG_PATH = Path.home() / ".oximy" / "dev.json"


def _load_local_config() -> dict[str, Any]:
    """Load local dev config if it exists."""
    if LOCAL_CONFIG_PATH.exists():
        try:
            with open(LOCAL_CONFIG_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load dev config from {LOCAL_CONFIG_PATH}: {e}")
    return {}


def _get_bool_env(key: str, default: bool) -> bool:
    """Get boolean from environment variable."""
    val = os.environ.get(key, "").lower()
    if val in ("1", "true", "yes", "on"):
        return True
    if val in ("0", "false", "no", "off"):
        return False
    return default


@dataclass(frozen=True)
class OximyConfig:
    """Immutable configuration object."""

    DEV_MODE: bool
    BUNDLE_URL: str | None  # None means use local bundle
    API_URL: str
    AUTO_PROXY_ENABLED: bool
    PROXY_HOST: str
    PROXY_PORT: str

    @property
    def USE_LOCAL_BUNDLE(self) -> bool:
        """Whether to prefer local bundle over remote URL."""
        return self.DEV_MODE or self.BUNDLE_URL is None


def _build_config() -> OximyConfig:
    """Build configuration from all sources."""
    local_config = _load_local_config()

    # Determine DEV_MODE first (controls other defaults)
    dev_mode = _get_bool_env(
        "OXIMY_DEV", local_config.get("DEV_MODE", _PROD_DEFAULTS["DEV_MODE"])
    )

    # Select base defaults
    defaults = {**_PROD_DEFAULTS}
    if dev_mode:
        defaults.update(_DEV_OVERRIDES)

    # Apply local config overrides
    for key in defaults:
        if key in local_config:
            defaults[key] = local_config[key]

    # Environment variables have highest priority
    bundle_url_env = os.environ.get("OXIMY_BUNDLE_URL")
    bundle_url = bundle_url_env if bundle_url_env is not None else defaults["BUNDLE_URL"]

    return OximyConfig(
        DEV_MODE=dev_mode,
        BUNDLE_URL=bundle_url,
        API_URL=os.environ.get("OXIMY_API_URL", defaults["API_URL"]),
        AUTO_PROXY_ENABLED=_get_bool_env(
            "OXIMY_AUTO_PROXY", defaults["AUTO_PROXY_ENABLED"]
        ),
        PROXY_HOST=os.environ.get("OXIMY_PROXY_HOST", defaults["PROXY_HOST"]),
        PROXY_PORT=os.environ.get("OXIMY_PROXY_PORT", defaults["PROXY_PORT"]),
    )


# Singleton config instance
config = _build_config()

# Log config on load (only in dev mode to avoid noise in production)
if config.DEV_MODE:
    logger.info(f"Oximy DEV MODE enabled: API={config.API_URL}, AutoProxy={config.AUTO_PROXY_ENABLED}")
