"""Configuration management for dsdown."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Default configuration directory
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "dsdown"
DEFAULT_DB_PATH = DEFAULT_CONFIG_DIR / "dsdown.db"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"

# Dynasty Scans base URL
DYNASTY_BASE_URL = "https://dynasty-scans.com"
DYNASTY_RELEASES_URL = f"{DYNASTY_BASE_URL}/chapters/added"

# Download rate limiting
MAX_DOWNLOADS_PER_24H = 8


class Config:
    """Application configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load configuration from file."""
        if self.config_path.exists():
            with open(self.config_path) as f:
                self._data = json.load(f)
        else:
            self._data = {}

    def _save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._data, f, indent=2)

    @property
    def last_fetched_chapter_url(self) -> str | None:
        """Get the URL of the last fetched chapter."""
        return self._data.get("last_fetched_chapter_url")

    @last_fetched_chapter_url.setter
    def last_fetched_chapter_url(self, value: str | None) -> None:
        """Set the URL of the last fetched chapter."""
        self._data["last_fetched_chapter_url"] = value
        self._save()

    @property
    def db_path(self) -> Path:
        """Get the database path."""
        path_str = self._data.get("db_path")
        if path_str:
            return Path(path_str)
        return DEFAULT_DB_PATH

    @db_path.setter
    def db_path(self, value: Path) -> None:
        """Set the database path."""
        self._data["db_path"] = str(value)
        self._save()


# Global config instance
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config
