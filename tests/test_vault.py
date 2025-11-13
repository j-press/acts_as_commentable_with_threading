import base64

from infrastructure_agent.vault import Vault, VaultError


def test_roundtrip(tmp_path):
    key = base64.b64encode(b"secret-key-1234567890").decode("ascii")
    vault = Vault(tmp_path, "vault.json", key)
    vault.write({"env": {"KEY": "value"}})
    data = vault.read()
    assert data["env"]["KEY"] == "value"


def test_missing_key(tmp_path):
    try:
        Vault(tmp_path, "vault.json", "")
    except VaultError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Vault should require a key")
