"""Configuration helpers for the infrastructure agent."""

from __future__ import annotations

import pathlib
from typing import Any, Dict, Iterable, Tuple


class ConfigError(RuntimeError):
    """Raised when configuration files are invalid."""


def load_config(path: str | pathlib.Path) -> Dict[str, Any]:
    """Load a YAML configuration file.

    Parameters
    ----------
    path: str | pathlib.Path
        Path to the YAML configuration file.

    Returns
    -------
    dict
        Parsed configuration data.
    """

    config_path = pathlib.Path(path)
    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        data = _parse(handle.read())

    if "runtime" not in data:
        raise ConfigError("Missing 'runtime' section in configuration")

    return data


def _parse(content: str) -> Dict[str, Any]:
    """Parse a minimal subset of YAML.

    The loader supports the constructs used in the sample configuration:

    * mappings of scalar keys to scalar values or nested mappings
    * lists introduced with ``-`` where each item is either a scalar or mapping
    * strings, booleans, and integers as scalar values
    """

    lines = [line.rstrip() for line in content.splitlines() if line.strip() and not line.strip().startswith("#")]
    parsed, _ = _parse_block(lines, 0, 0)
    if not isinstance(parsed, dict):
        raise ConfigError("Top level of configuration must be a mapping")
    return parsed


def _parse_block(lines: Iterable[str], start: int, indent: int) -> Tuple[Any, int]:
    items = {}
    seq = []
    is_seq = False
    i = start
    while i < len(lines):
        line = lines[i]
        current_indent = _indent_of(line)
        if current_indent < indent:
            break
        if current_indent > indent:
            raise ConfigError(f"Unexpected indentation on line: {line}")

        stripped = line.strip()
        if stripped.startswith("- "):
            if not is_seq:
                if items:
                    raise ConfigError("Cannot mix mappings and lists at the same indentation level")
                is_seq = True
            value_str = stripped[2:]
            if value_str:
                seq.append(_parse_scalar(value_str))
                i += 1
            else:
                nested, next_index = _parse_block(lines, i + 1, indent + 2)
                seq.append(nested)
                i = next_index
        else:
            if is_seq:
                raise ConfigError("Cannot mix mappings and lists at the same indentation level")
            if ":" not in stripped:
                raise ConfigError(f"Expected ':' in mapping line: {line}")
            key, value_str = stripped.split(":", 1)
            key = key.strip()
            value_str = value_str.strip()
            if value_str:
                items[key] = _parse_scalar(value_str)
                i += 1
            else:
                nested, next_index = _parse_block(lines, i + 1, indent + 2)
                items[key] = nested
                i = next_index
    return (seq if is_seq else items), i


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        return value


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))
