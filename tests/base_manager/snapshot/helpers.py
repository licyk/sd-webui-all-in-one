"""环境快照测试辅助工具"""

from pathlib import Path

from sd_webui_all_in_one.base_manager import snapshot as snapshot_utils


def make_extension_snapshot(name: str, path: Path, enabled: bool | None) -> snapshot_utils.ExtensionSnapshot:
    return snapshot_utils.ExtensionSnapshot(
        name=name,
        path=path,
        enabled=enabled,
        is_git_repo=True,
        url=f"https://example.test/{name}",
        branch="main",
        commit="abcdef",
        dirty=False,
    )


def make_webui_snapshot(path: Path) -> snapshot_utils.WebUiSnapshot:
    return snapshot_utils.WebUiSnapshot(
        schema_version=snapshot_utils.SNAPSHOT_SCHEMA_VERSION,
        created_at="2026-06-18T00:00:00Z",
        webui=snapshot_utils.WebUiIdentitySnapshot(name="Demo", type="demo", path=path),
        python=snapshot_utils.PythonSnapshot(
            version="3.11.0",
            implementation="CPython",
            executable=Path("/usr/bin/python"),
            platform="linux",
        ),
        system=snapshot_utils.SystemSnapshot(
            system="Linux",
            architecture="x86_64",
        ),
        kernel=snapshot_utils.RepositorySnapshot(
            path=path,
            name=path.name,
            is_git_repo=False,
            dirty=None,
        ),
    )


def make_package_snapshot(
    name: str,
    version: str,
    direct_url: snapshot_utils.DirectUrlSnapshot | None = None,
    editable: bool = False,
) -> snapshot_utils.PackageSnapshot:
    return snapshot_utils.PackageSnapshot(
        name=name,
        version=version,
        editable=editable,
        direct_url=direct_url,
    )


def make_git_repo_snapshot(path: Path, commit: str = "abcdef") -> snapshot_utils.RepositorySnapshot:
    return snapshot_utils.RepositorySnapshot(path=path, name=path.name, is_git_repo=True, url="https://example.test/repo.git", commit=commit)


def write_fake_git_dir(repo_path: Path, commit: str) -> None:
    """写入最小 Git 目录, 使 HEAD 可在不启动 Git 进程时解析到指定提交"""
    git_path = repo_path / ".git"
    (git_path / "refs" / "heads").mkdir(parents=True)
    (git_path / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_path / "refs" / "heads" / "main").write_text(f"{commit}\n", encoding="utf-8")
