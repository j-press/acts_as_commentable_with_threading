"""Automation agent orchestration."""

from __future__ import annotations

import json
import os
import pathlib
import time
from typing import Dict, Mapping

from .backup import build_targets
from .inventory import build_collectors
from .logging import configure_logger
from .status import StatusStore
from .vault import Vault, VaultError
from .version_control import GitVersionControl, VersionControlError


class AutomationAgent:
    """Coordinate discovery, vault storage, and backups."""

    def __init__(self, config: Mapping[str, object]):
        self.config = config
        runtime = config.get("runtime", {})
        work_dir_value = runtime.get("work_dir", "tmp/infrastructure_agent")
        expanded_work_dir = os.path.expandvars(str(work_dir_value))
        if not expanded_work_dir.strip():
            expanded_work_dir = "tmp/infrastructure_agent"
        work_dir = pathlib.Path(expanded_work_dir).expanduser()
        if not work_dir.is_absolute():
            work_dir = pathlib.Path.cwd() / work_dir
        work_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir = work_dir

        log_file_value = runtime.get("log_file")
        log_file = None
        if log_file_value:
            expanded_log = os.path.expandvars(str(log_file_value))
            if expanded_log.strip():
                log_path = pathlib.Path(expanded_log).expanduser()
                if not log_path.is_absolute():
                    log_path = work_dir / log_path
                log_file = str(log_path)
        self.logger = configure_logger(log_file)
        self.status = StatusStore()

        collectors_config = config.get("inventory", {}).get("collectors", [])
        self.collectors = build_collectors(collectors_config)

        backup_config = config.get("backups", {}).get("targets", [])
        self.backups = build_targets(backup_config, base_dir=self.work_dir)

        vault_config = config.get("vault", {})
        self.vault_enabled = bool(vault_config.get("enabled", True))
        self.vault = None
        if self.vault_enabled:
            key_env = str(vault_config.get("key_env"))
            key_value = os.environ.get(key_env, "") if key_env else ""
            file_name = vault_config.get("file", "vault.json")
            self.vault = Vault(self.work_dir, file_name, key_value)

        version_config = config.get("version_control", {})
        self.version_control = None
        if version_config.get("enabled"):
            repo_value = version_config.get("repository", ".")
            expanded_repo = os.path.expandvars(str(repo_value))
            if not expanded_repo.strip():
                expanded_repo = "."
            repo_path = pathlib.Path(expanded_repo).expanduser()
            if not repo_path.is_absolute():
                repo_path = self.work_dir / repo_path
            resolved_paths = []
            for path_value in version_config.get("tracked_paths", ["."]):
                expanded_path = os.path.expandvars(str(path_value))
                if not expanded_path.strip():
                    expanded_path = "."
                candidate = pathlib.Path(expanded_path).expanduser()
                if not candidate.is_absolute():
                    resolved_paths.append(repo_path / candidate)
                else:
                    resolved_paths.append(candidate)
            user_config = version_config.get("user", {})
            self.version_control = GitVersionControl(
                repo_path=repo_path,
                branch=str(version_config.get("branch", "main")),
                auto_init=bool(version_config.get("auto_init", True)),
                user_name=user_config.get("name"),
                user_email=user_config.get("email"),
                message_template=str(version_config.get("message", "Infrastructure snapshot at {timestamp}")),
                tracked_paths=resolved_paths,
            )

        self.dashboard_config = runtime.get("dashboard", {})

    def run(self) -> Dict[str, object]:
        self.logger.info("Starting infrastructure automation run")
        inventory_data: Dict[str, object] = {}
        self._run_inventory(inventory_data)
        if self.vault_enabled and self.vault:
            self._write_vault(inventory_data.get("environment", {}))
        self._run_backups()
        commit = self._commit_version_control()
        summary = {
            "inventory": inventory_data,
            "vault": bool(self.vault_enabled),
            "backups": len(self.backups),
            "version_control": commit,
        }
        self.logger.info("Automation run completed")
        return summary

    def _run_inventory(self, result: Dict[str, object]) -> None:
        for collector in self.collectors:
            name = collector.__class__.__name__
            self.status.update(name, state="running", started_at=time.time())
            try:
                data = collector.collect()
                for key, payload in data.items():
                    result[key] = payload
                    self._persist_inventory(key, payload)
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

    def _persist_inventory(self, key: str, payload: object) -> None:
        inventory_dir = self.work_dir / "inventory"
        inventory_dir.mkdir(parents=True, exist_ok=True)
        file_path = inventory_dir / f"{key}.json"
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    def _commit_version_control(self) -> str | None:
        if not self.version_control:
            return None
        name = "VersionControl"
        self.status.update(name, state="running", started_at=time.time())
        try:
            commit = self.version_control.commit()
            finished = {"finished_at": time.time()}
            if commit:
                details = {"commit": commit}
                self.status.update(name, state="completed", **finished, details=details)
                self.logger.info("Version control snapshot recorded: %s", commit)
            else:
                details = {"commit": None, "message": "No changes detected"}
                self.status.update(name, state="completed", **finished, details=details)
                self.logger.info("Version control snapshot skipped (no changes)")
            return commit
        except VersionControlError as exc:
            self.status.update(name, state="failed", finished_at=time.time(), details={"error": str(exc)})
            self.logger.error("Version control operation failed: %s", exc)
            return None
