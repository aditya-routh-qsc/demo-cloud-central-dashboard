"""Configuration helpers for dashboard sync/runtime settings."""

from __future__ import annotations

import configparser
import logging
import os
from functools import lru_cache

from dotenv import load_dotenv

DEFAULT_CONFIG_PATH = ".config"
DEFAULT_SYNC_INTERVAL_MINUTES = 60
MIN_SYNC_INTERVAL_MINUTES = 1
MAX_SYNC_INTERVAL_MINUTES = 1440

load_dotenv(override=True)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_config(config_path: str | None = None) -> configparser.ConfigParser:
    """Load .config file with safe fallback to defaults."""
    parser = configparser.ConfigParser()
    resolved_path = config_path or os.getenv("APP_CONFIG_PATH", DEFAULT_CONFIG_PATH)
    parser.read(resolved_path, encoding="utf-8")
    return parser


def get_sync_interval_minutes() -> int:
    """Return scheduler interval in minutes from .config with safe fallback."""
    parser = load_config()
    raw_value = parser.get("sync", "interval_minutes", fallback=str(DEFAULT_SYNC_INTERVAL_MINUTES)).strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid .config sync.interval_minutes='%s'. Using default %s.",
            raw_value,
            DEFAULT_SYNC_INTERVAL_MINUTES,
        )
        return DEFAULT_SYNC_INTERVAL_MINUTES

    if parsed < MIN_SYNC_INTERVAL_MINUTES or parsed > MAX_SYNC_INTERVAL_MINUTES:
        logger.warning(
            "Legacy .config sync.interval_minutes='%s' is out of range %s-%s. Using default %s.",
            raw_value,
            MIN_SYNC_INTERVAL_MINUTES,
            MAX_SYNC_INTERVAL_MINUTES,
            DEFAULT_SYNC_INTERVAL_MINUTES,
        )
        return DEFAULT_SYNC_INTERVAL_MINUTES

    return parsed


def get_sync_cooldown_seconds() -> int:
    """Return sync cooldown in seconds from .config with safe fallback."""
    parser = load_config()
    raw_value = parser.get("sync", "cooldown_seconds", fallback="300").strip()
    try:
        return int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid .config sync.cooldown_seconds='%s'. Using default 300.",
            raw_value,
        )
        return 300


def get_database_path() -> str:
    """Return sqlite file path from .config with fallback."""
    parser = load_config()
    configured = parser.get("database", "path", fallback="dashboard_cache.db").strip()
    return configured
