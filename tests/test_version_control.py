import pytest

from infrastructure_agent.version_control import GitVersionControl, VersionControlError


def git_available():
    from shutil import which

    return which("git") is not None


@pytest.mark.skipif(not git_available(), reason="git binary required")
def test_git_version_control_commit(tmp_path):
    repo = tmp_path / "repo"
    tracked = repo / "data"
    tracked.mkdir(parents=True)
    (tracked / "file.txt").write_text("hello", encoding="utf-8")

    vc = GitVersionControl(
        repo_path=repo,
        auto_init=True,
        branch="main",
        user_name="Tester",
        user_email="tester@example.com",
        tracked_paths=[tracked],
        message_template="Commit {timestamp}",
    )

    commit = vc.commit()
    assert commit
    assert (repo / ".git").exists()

    # No new changes
    assert vc.commit() is None


@pytest.mark.skipif(not git_available(), reason="git binary required")
def test_git_version_control_error(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with pytest.raises(VersionControlError):
        GitVersionControl(repo_path=repo, auto_init=False)

