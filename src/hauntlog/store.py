"""One folder on this computer (~/.hauntlog, or HAUNTLOG_HOME): the nights you saved and the stories told.
Readable JSON; copy it to keep it, delete it to forget everything."""

from __future__ import annotations

import copy
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def home_dir() -> Path:
    raw = os.environ.get("HAUNTLOG_HOME", "").strip()
    return Path(raw).expanduser() if raw else Path.home() / ".hauntlog"


class Store:
    def __init__(self, home: Path | None = None) -> None:
        self.home = home or home_dir()
        self.home.mkdir(parents=True, exist_ok=True)
        self.path = self.home / "hauntlog.json"
        self._lock = threading.RLock()
        self.data = {"nights": {}, "stories": {}, "next": 1}
        if self.path.exists():
            try:
                self.data.update(json.loads(self.path.read_text("utf-8")))
            except ValueError:
                self.path.replace(self.path.with_suffix(".unreadable.json"))  # never silently lose records

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), "utf-8")
        tmp.replace(self.path)

    def _id(self) -> int:
        n = self.data["next"]
        self.data["next"] += 1
        return n

    def add_night(self, **n) -> int:
        with self._lock:
            nid = self._id()
            self.data["nights"][str(nid)] = {"id": nid, "created_at": now_iso(), **n}
            self._save()
            return nid

    def night(self, nid: int) -> dict | None:
        with self._lock:
            n = self.data["nights"].get(str(nid))
            return copy.deepcopy(n) if n else None

    def nights(self) -> list[dict]:
        with self._lock:
            return [copy.deepcopy(n) for n in reversed(list(self.data["nights"].values()))]

    def add_story(self, **s) -> int:
        with self._lock:
            sid = self._id()
            self.data["stories"][str(sid)] = {"id": sid, "at": now_iso(), **s}
            self._save()
            return sid

    def story(self, sid: int) -> dict | None:
        with self._lock:
            s = self.data["stories"].get(str(sid))
            return copy.deepcopy(s) if s else None

    def stories(self, night_id: int) -> list[dict]:
        with self._lock:
            return [copy.deepcopy(s) for s in reversed(list(self.data["stories"].values())) if s["night_id"] == night_id]
