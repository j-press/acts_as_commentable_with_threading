from infrastructure_agent.config import ConfigError, load_config
import pathlib
import textwrap


def write_config(tmp_path, content):
    path = tmp_path / "config.yml"
    path.write_text(textwrap.dedent(content))
    return path


def test_load_config(tmp_path):
    config_path = write_config(
        tmp_path,
        """
        runtime:
          work_dir: ./tmp
        """,
    )
    data = load_config(config_path)
    assert data["runtime"]["work_dir"] == "./tmp"


def test_missing_runtime(tmp_path):
    config_path = write_config(
        tmp_path,
        """
        vault:
          enabled: false
        """,
    )
    try:
        load_config(config_path)
    except ConfigError as exc:
        assert "runtime" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected ConfigError")
