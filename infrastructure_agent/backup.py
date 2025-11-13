"""Backup utilities."""

from __future__ import annotations

import os
import pathlib
import shutil
import tarfile
import time
from typing import Iterable, List, Mapping


def _resolve_path(base_dir: pathlib.Path, value: str | pathlib.Path | None) -> pathlib.Path:
    if value is None:
        raise BackupError("Backup destination must be provided")
    expanded = os.path.expandvars(str(value))
    if not expanded.strip():
        return base_dir
    path = pathlib.Path(expanded).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path


class BackupError(RuntimeError):
    """Raised when backup targets fail."""


class BackupTarget:
    def run(self) -> str:
        raise NotImplementedError


class LocalBackupTarget(BackupTarget):
    """Create tar archives for local directories."""

    def __init__(self, name: str, sources: Iterable[pathlib.Path], destination: pathlib.Path, archive: bool, retention: Mapping[str, int] | None = None):
        self.name = name
        self.sources = list(sources)
        self.destination = destination
        self.archive = archive
        self.retention = retention or {}
        self.destination.mkdir(parents=True, exist_ok=True)

    def run(self) -> str:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        archive_path = self.destination / f"{self.name}-{timestamp}"
        if self.archive:
            archive_path = archive_path.with_suffix(".tar.gz")
            with tarfile.open(archive_path, "w:gz") as bundle:
                for source in self.sources:
                    if source.exists():
                        bundle.add(source, arcname=source.name)
        else:
            archive_path.mkdir(parents=True, exist_ok=True)
            for source in self.sources:
                if source.is_file():
                    shutil.copy2(source, archive_path / source.name)
                elif source.is_dir():
                    shutil.copytree(source, archive_path / source.name, dirs_exist_ok=True)
        self._enforce_retention()
        return str(archive_path)

    def _enforce_retention(self) -> None:
        max_files = self.retention.get("max_files") if self.retention else None
        if not max_files:
            return
        archives = sorted(self.destination.glob(f"{self.name}-*"))
        while len(archives) > max_files:
            oldest = archives.pop(0)
            oldest.unlink(missing_ok=True)


def build_targets(config: Iterable[Mapping[str, object]], base_dir: pathlib.Path) -> List[BackupTarget]:
    targets: List[BackupTarget] = []
    for entry in config:
        target_type = (entry.get("type") or "").lower()
        if target_type == "local":
            destination = _resolve_path(base_dir, entry.get("destination"))
            sources = [
                _resolve_path(base_dir, source)
                for source in entry.get("source", [])
            ]
            targets.append(
                LocalBackupTarget(
                    name=str(entry.get("name", "backup")),
                    sources=sources,
                    destination=destination,
                    archive=bool(entry.get("archive", True)),
                    retention=entry.get("retention"),
                )
            )
        else:
            raise BackupError(f"Unsupported backup target: {target_type}")
    return targets
