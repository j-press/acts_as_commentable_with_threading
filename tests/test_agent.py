import base64
import json
import os
import pathlib

from infrastructure_agent.agent import AutomationAgent


def sample_config(tmp_path):
    config = {
        "runtime": {"work_dir": str(tmp_path / "work"), "log_file": None},
        "inventory": {"collectors": [{"type": "environment", "include": ["USER"]}]},
        "vault": {"enabled": True, "file": "vault.json", "key_env": "INFRA_AGENT_KEY"},
        "backups": {"targets": [{"type": "local", "name": "state", "source": [str(tmp_path)], "destination": str(tmp_path / "backups"), "archive": True, "retention": {"max_files": 2}}]},
        "version_control": {
            "enabled": True,
            "repository": ".",
            "auto_init": True,
            "branch": "main",
            "user": {"name": "Agent", "email": "agent@example.com"},
            "tracked_paths": ["."],
            "message": "Snapshot {timestamp}",
        },
    }
    return config


def test_agent_run(tmp_path, monkeypatch):
    key = base64.b64encode(b"unit-test-key-1234567890123456").decode("ascii")
    monkeypatch.setenv("INFRA_AGENT_KEY", key)
    config = sample_config(tmp_path)
    agent = AutomationAgent(config)
    summary = agent.run()
    assert summary["vault"] is True
    vault_path = pathlib.Path(config["runtime"]["work_dir"]) / "vault.json"
    assert vault_path.exists()
    assert agent.status.snapshot()
    backups_dir = pathlib.Path(config["backups"]["targets"][0]["destination"])
    assert backups_dir.exists()
    assert any(backups_dir.iterdir())
    git_dir = pathlib.Path(config["runtime"]["work_dir"]) / ".git"
    assert git_dir.exists()
    commit = summary["version_control"]
    assert commit and len(commit) == 40
