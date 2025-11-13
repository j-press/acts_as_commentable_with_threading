"""Status tracking utilities."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class TaskStatus:
    name: str
    state: str = "pending"
    started_at: float | None = None
    finished_at: float | None = None
    details: Dict[str, object] = field(default_factory=dict)


class StatusStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: Dict[str, TaskStatus] = {}

    def update(self, name: str, **fields) -> TaskStatus:
        with self._lock:
            status = self._tasks.setdefault(name, TaskStatus(name=name))
            for key, value in fields.items():
                setattr(status, key, value)
            return status

    def snapshot(self) -> Dict[str, Dict[str, object]]:
        with self._lock:
            return {name: status.__dict__.copy() for name, status in self._tasks.items()}

    def to_json(self) -> str:
        return json.dumps(self.snapshot(), indent=2, sort_keys=True, default=str)
