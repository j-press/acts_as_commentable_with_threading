"""Simple encrypted vault for storing environment variables."""

from __future__ import annotations

import base64
import json
import pathlib
from typing import Mapping


class VaultError(RuntimeError):
    """Raised when vault operations fail."""


class Vault:
    """Persist data with a symmetric key using an XOR-based cipher."""

    def __init__(self, base_dir: str | pathlib.Path, file_name: str, key: str):
        if not key:
            raise VaultError("Vault key must be provided through the configured environment variable")
        try:
            self.key_bytes = base64.b64decode(key)
        except Exception as exc:  # pragma: no cover - defensive
            raise VaultError("Vault key must be base64 encoded") from exc
        if len(self.key_bytes) == 0:
            raise VaultError("Vault key cannot be empty")

        self.path = pathlib.Path(base_dir) / file_name
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, payload: Mapping[str, object]) -> None:
        raw = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        encrypted = self._xor(raw)
        with self.path.open("wb") as handle:
            handle.write(base64.b64encode(encrypted))

    def read(self) -> Mapping[str, object]:
        if not self.path.exists():
            return {}
        data = base64.b64decode(self.path.read_bytes())
        decrypted = self._xor(data)
        return json.loads(decrypted.decode("utf-8"))

    def _xor(self, data: bytes) -> bytes:
        key = self.key_bytes
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
