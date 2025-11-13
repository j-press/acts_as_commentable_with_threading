"""Automation agent orchestration."""

from __future__ import annotations

import os
import pathlib
import time
from typing import Dict, Mapping

from .backup import build_targets
from .inventory import build_collectors
from .logging import configure_logger
from .status import StatusStore
from .vault import Vault, VaultError


class AutomationAgent:
    """Coordinate discovery, vault storage, and backups."""

    def __init__(self, config: Mapping[str, object]):
        self.config = config
        runtime = config.get("runtime", {})
        work_dir = pathlib.Path(runtime.get("work_dir", "tmp/infrastructure_agent"))
        work_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir = work_dir

        log_file = runtime.get("log_file")
        self.logger = configure_logger(log_file)
        self.status = StatusStore()

        collectors_config = config.get("inventory", {}).get("collectors", [])
        self.collectors = build_collectors(collectors_config)

        backup_config = config.get("backups", {}).get("targets", [])
        self.backups = build_targets(backup_config)

        vault_config = config.get("vault", {})
        self.vault_enabled = bool(vault_config.get("enabled", True))
        self.vault = None
        if self.vault_enabled:
            key_env = str(vault_config.get("key_env"))
            key_value = os.environ.get(key_env, "") if key_env else ""
            file_name = vault_config.get("file", "vault.json")
            self.vault = Vault(self.work_dir, file_name, key_value)

        self.dashboard_config = runtime.get("dashboard", {})

    def run(self) -> Dict[str, object]:
        self.logger.info("Starting infrastructure automation run")
        inventory_data: Dict[str, object] = {}
        self._run_inventory(inventory_data)
        if self.vault_enabled and self.vault:
            self._write_vault(inventory_data.get("environment", {}))
        self._run_backups()
        summary = {"inventory": inventory_data, "vault": bool(self.vault_enabled), "backups": len(self.backups)}
        self.logger.info("Automation run completed")
        return summary

    def _run_inventory(self, result: Dict[str, object]) -> None:
        for collector in self.collectors:
            name = collector.__class__.__name__
            status = self.status.update(name, state="running", started_at=time.time())
            try:
                data = collector.collect()
                result.update(data)
                self.status.update(name, state="completed", finished_at=time.time(), details={"keys": list(data.keys())})
                self.logger.info("Collector %s completed", name)
            except Exception as exc:  # pragma: no cover - defensive
                self.status.update(name, state="failed", finished_at=time.time(), details={"error": str(exc)})
                self.logger.exception("Collector %s failed", name)

    def _write_vault(self, environment: Mapping[str, object]) -> None:
        status = self.status.update("Vault", state="running", started_at=time.time())
        try:
            assert self.vault is not None
            self.vault.write(environment)
            self.status.update("Vault", state="completed", finished_at=time.time(), details={"items": len(environment)})
            self.logger.info("Vault write completed with %s entries", len(environment))
        except VaultError as exc:
            self.status.update("Vault", state="failed", finished_at=time.time(), details={"error": str(exc)})
            self.logger.error("Vault operation failed: %s", exc)

    def _run_backups(self) -> None:
        for index, target in enumerate(self.backups):
            name = f"Backup-{index + 1}"
            self.status.update(name, state="running", started_at=time.time())
            try:
                location = target.run()
                self.status.update(name, state="completed", finished_at=time.time(), details={"location": location})
                self.logger.info("Backup stored at %s", location)
            except Exception as exc:  # pragma: no cover - defensive
                self.status.update(name, state="failed", finished_at=time.time(), details={"error": str(exc)})
                self.logger.exception("Backup target failed")
