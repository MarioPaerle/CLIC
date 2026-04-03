"""
Configuration manager for CLIC.
"""

from pathlib import Path
from typing import Any

import yaml


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config.yaml"

_DEFAULTS: dict[str, Any] = {
    "shell": "powershell",
    "shell_options": {
        "powershell": {
            "executable": "powershell.exe",
            "args": ["-NoLogo", "-NoProfile"],
        },
        "cmd": {
            "executable": "cmd.exe",
            "args": [],
        },
    },
    "sounds": {"enabled": True, "master_volume": 0.4},
    "file_browser": {
        "show_hidden": False,
        "exclude": ["__pycache__", "node_modules", ".git", "*.pyc", ".DS_Store", "Thumbs.db"],
    },
    "history": {
        "max_entries": 1000,
        "persistent": True,
        "file": ".clic_history",
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class Config:
    _data: dict[str, Any] = {}
    CONFIG_PATH = CONFIG_PATH

    @classmethod
    def load(cls, path: Path | None = None) -> None:
        path = path or CONFIG_PATH
        user_cfg: dict[str, Any] = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
        cls._data = _deep_merge(_DEFAULTS, user_cfg)

    @classmethod
    def get(cls, *keys: str, default: Any = None) -> Any:
        if not cls._data:
            cls.load()
        current = cls._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    @classmethod
    def set(cls, *keys: str, value: Any) -> None:
        if not cls._data:
            cls.load()
        current = cls._data
        for key in keys[:-1]:
            current = current.setdefault(key, {})
        current[keys[-1]] = value

    @classmethod
    def get_history_path(cls) -> Path:
        return BASE_DIR / cls.get("history", "file", default=".clic_history")
