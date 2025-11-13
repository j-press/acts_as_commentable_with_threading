"""Utilities for version controlling collected artefacts."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Iterable, List, Optional


class VersionControlError(RuntimeError):
    """Raised when version control operations fail."""


class GitVersionControl:
    """Commit generated artefacts into a Git repository."""

    def __init__(
        self,
        repo_path: Path,
        branch: str = "main",
        auto_init: bool = True,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        message_template: str = "Infrastructure snapshot at {timestamp}",
        tracked_paths: Optional[Iterable[Path]] = None,
    ) -> None:
        self.repo_path = repo_path
        self.branch = branch
        self.auto_init = auto_init
        self.user_name = user_name
        self.user_email = user_email
        self.message_template = message_template
        default_tracked = [Path(".")]
        self.tracked_paths: List[Path] = list(tracked_paths or default_tracked)

        self.repo_path.mkdir(parents=True, exist_ok=True)
        if auto_init:
            self._run(["git", "init", str(self.repo_path)], cwd=self.repo_path.parent)

        if self.branch:
            self._run(["git", "checkout", "-B", self.branch])

        if self.user_name:
            self._run(["git", "config", "user.name", self.user_name])
        if self.user_email:
            self._run(["git", "config", "user.email", self.user_email])

    def commit(self) -> str | None:
        """Commit tracked paths if there are changes.

        Returns the commit hash when changes were committed or ``None`` when no
        modifications were detected.
        """

        for path in self.tracked_paths:
            relative = path
            if path.is_absolute():
                try:
                    relative = path.relative_to(self.repo_path)
                except ValueError:
                    # Path outside repository; add via absolute path
                    relative = path
            self._run(["git", "add", str(relative)])

        if not self._has_changes():
            return None

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        message = self.message_template.format(timestamp=timestamp)
        self._run(["git", "commit", "-m", message])
        result = self._run(["git", "rev-parse", "HEAD"], capture_output=True)
        return result.stdout.strip()

    def _has_changes(self) -> bool:
        result = self._run(["git", "status", "--porcelain"], capture_output=True)
        return bool(result.stdout.strip())

    def _run(self, command: List[str], cwd: Path | None = None, capture_output: bool = False) -> subprocess.CompletedProcess:
        run_cwd = cwd or self.repo_path
        try:
            return subprocess.run(
                command,
                cwd=run_cwd,
                check=True,
                text=True,
                capture_output=capture_output,
            )
        except subprocess.CalledProcessError as exc:  # pragma: no cover - defensive
            raise VersionControlError(exc.stderr or str(exc)) from exc


__all__ = ["GitVersionControl", "VersionControlError"]

