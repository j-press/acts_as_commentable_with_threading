"""Inventory collectors used by the automation agent."""

from __future__ import annotations

import os
import platform
import socket
from typing import Dict, Iterable, List, Mapping


class InventoryCollector:
    """Base class for collectors."""

    def collect(self) -> Mapping[str, object]:
        raise NotImplementedError


class EnvironmentCollector(InventoryCollector):
    """Collect a subset of environment variables."""

    def __init__(self, include: Iterable[str] | None = None):
        self.include = list(include) if include else []

    def collect(self) -> Mapping[str, object]:
        if not self.include:
            return {"environment": dict(os.environ)}
        return {"environment": {key: os.environ.get(key) for key in self.include}}


class HostCollector(InventoryCollector):
    """Collect basic host metadata."""

    def collect(self) -> Mapping[str, object]:
        return {
            "host": {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "architecture": platform.machine(),
            }
        }


def build_collectors(config: List[Mapping[str, object]]) -> List[InventoryCollector]:
    """Instantiate collectors based on configuration."""

    collectors: List[InventoryCollector] = []
    for entry in config:
        collector_type = (entry.get("type") or "").lower()
        if collector_type == "environment":
            collectors.append(EnvironmentCollector(entry.get("include")))
        elif collector_type == "host":
            collectors.append(HostCollector())
        else:
            raise ValueError(f"Unsupported collector type: {collector_type}")
    return collectors
