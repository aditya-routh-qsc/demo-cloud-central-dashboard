"""Configuration helpers for dashboard sync/runtime settings."""

from __future__ import annotations

import configparser
import os
from functools import lru_cache

DEFAULT_CONFIG_PATH = ".config"
DEFAULT_SYNC_INTERVAL_MINUTES = 60


@lru_cache(maxsize=1)
def load_config(config_path: str | None = None) -> configparser.ConfigParser:
    """Load .config file with safe fallback to defaults."""
    parser = configparser.ConfigParser()
    resolved_path = config_path or os.getenv("APP_CONFIG_PATH", DEFAULT_CONFIG_PATH)
    parser.read(resolved_path, encoding="utf-8")
    return parser


def get_sync_interval_minutes() -> int:
    """Return scheduler interval in minutes from .config with default fallback."""
    parser = load_config()
    raw_value = parser.get("sync", "interval_minutes", fallback=str(DEFAULT_SYNC_INTERVAL_MINUTES)).strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        return DEFAULT_SYNC_INTERVAL_MINUTES
    if parsed <= 0:
        return DEFAULT_SYNC_INTERVAL_MINUTES
    return parsed


def get_database_path() -> str:
    """Return sqlite file path from .config/env with fallback."""
    parser = load_config()
    configured = parser.get("database", "path", fallback="").strip()
    env_value = os.getenv("DASHBOARD_DB_PATH", "").strip()
    return env_value or configured or "dashboard_cache.db"
