"""
Command history manager for CLIC.

Stores commands with timestamps, supports search/filter,
and optionally persists to disk between sessions.
"""

import json
from datetime import datetime
from pathlib import Path

from clic.config import Config


class HistoryEntry:
    """Single command history entry."""

    __slots__ = ("command", "timestamp", "cwd", "exit_code")

    def __init__(
        self,
        command: str,
        timestamp: str | None = None,
        cwd: str = "",
        exit_code: int | None = None,
    ):
        self.command = command
        self.timestamp = timestamp or datetime.now().isoformat(timespec="seconds")
        self.cwd = cwd
        self.exit_code = exit_code

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "timestamp": self.timestamp,
            "cwd": self.cwd,
            "exit_code": self.exit_code,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(**data)

    @property
    def display(self) -> str:
        """Formatted string for history view."""
        ts = self.timestamp[:19].replace("T", " ")
        icon = "" if self.exit_code == 0 else "" if self.exit_code else ""
        return f"{icon} {ts}  {self.command}"


class HistoryManager:
    """
    Manages command history with persistence and search.

    Usage:
        hm = HistoryManager()
        hm.load()                          # load from disk
        hm.add("git status", cwd="/home")  # add entry
        results = hm.search("git")         # fuzzy-ish search
        hm.save()                          # persist to disk
    """

    def __init__(self) -> None:
        self._entries: list[HistoryEntry] = []
        self._max = Config.get("history", "max_entries", default=1000)

    @property
    def entries(self) -> list[HistoryEntry]:
        return self._entries

    def add(
        self, command: str, cwd: str = "", exit_code: int | None = None
    ) -> None:
        """Add a command to history."""
        command = command.strip()
        if not command:
            return
        entry = HistoryEntry(command=command, cwd=cwd, exit_code=exit_code)
        self._entries.append(entry)
        # Trim if over max
        if len(self._entries) > self._max:
            self._entries = self._entries[-self._max :]

    def search(self, query: str) -> list[HistoryEntry]:
        """Search history entries (case-insensitive substring match)."""
        query = query.lower()
        return [e for e in self._entries if query in e.command.lower()]

    def recent(self, n: int = 50) -> list[HistoryEntry]:
        """Get the N most recent entries."""
        return self._entries[-n:]

    def clear(self) -> None:
        self._entries.clear()

    def load(self) -> None:
        """Load history from disk."""
        if not Config.get("history", "persistent", default=True):
            return
        path = Config.get_history_path()
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._entries = [HistoryEntry.from_dict(d) for d in data]
        except (json.JSONDecodeError, KeyError):
            pass

    def save(self) -> None:
        """Save history to disk."""
        if not Config.get("history", "persistent", default=True):
            return
        path = Config.get_history_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in self._entries], f, ensure_ascii=False)
