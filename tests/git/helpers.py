"""Git 测试辅助工具"""

from pathlib import Path

from sd_webui_all_in_one import git_warpper
from tests.support.git import real_git


def git_command(repo: Path, *args: str) -> list[str]:
    return ["/bin/git", "-c", "safe.directory=*", "-c", "core.longpaths=true", "-C", repo.as_posix(), *args]


def push_commit(upstream: Path, content: str) -> str:
    (upstream / "file.txt").write_text(content, encoding="utf-8")
    real_git(upstream, "commit", "-q", "-am", content.strip())
    real_git(upstream, "push", "-q", "origin", "main")
    return real_git(upstream, "rev-parse", "HEAD")


def record_git_subcommands(monkeypatch) -> list[str]:
    subcommands: list[str] = []
    real_run_cmd = git_warpper.run_cmd

    def recording_run_cmd(command, *args, **kwargs):
        subcommands.append(command[command.index("-C") + 2] if "-C" in command else command[5])
        return real_run_cmd(command, *args, **kwargs)

    monkeypatch.setattr(git_warpper, "run_cmd", recording_run_cmd)
    return subcommands
