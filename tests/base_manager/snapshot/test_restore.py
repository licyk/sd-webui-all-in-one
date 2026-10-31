"""环境快照恢复流程与软件包恢复测试"""

from pathlib import Path

import pytest

from sd_webui_all_in_one.base_manager import snapshot as snapshot_utils
from sd_webui_all_in_one.base_manager import snapshot_restore as restore_utils
from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryProbe
from sd_webui_all_in_one.base_manager.snapshot_restore import extensions as restore_extensions
from sd_webui_all_in_one.base_manager.snapshot_restore import packages as restore_packages
from sd_webui_all_in_one.base_manager.snapshot_restore import service as restore_service
from tests.base_manager.snapshot.helpers import make_extension_snapshot, make_git_repo_snapshot, make_package_snapshot, make_webui_snapshot


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("file:///workspace/demo%20pkg", Path("/workspace/demo pkg")),
        ("file://localhost/workspace/demo", Path("/workspace/demo")),
        ("file:///C:/Users/demo/pkg", Path("C:/Users/demo/pkg")),
        ("file:///C|/Users/demo/pkg", Path("C:/Users/demo/pkg")),
        ("file://server/share/demo%20pkg", Path("//server/share/demo pkg")),
        ("relative/pkg", Path("relative/pkg")),
        ("https://example.test/pkg", None),
    ],
)
def test_snapshot_restore_local_path_from_url_handles_common_file_url_forms(url, expected):
    assert restore_packages._local_path_from_url(url) == expected


def test_restore_webui_snapshot_rejects_mismatched_webui_type(monkeypatch, tmp_path):
    snapshot = make_webui_snapshot(tmp_path / "demo")
    snapshot.webui.type = "sd_webui"
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    def fail_restore(*_args, **_kwargs):
        raise AssertionError("restore should not run for mismatched snapshots")

    monkeypatch.setattr(restore_service, "restore_python_packages", fail_restore)

    with pytest.raises(ValueError, match="快照 WebUI 类型不匹配"):
        restore_utils.restore_webui_snapshot(
            snapshot_path=output,
            webui_path=tmp_path / "ComfyUI",
            expected_webui_type="comfyui",
        )


def test_restore_webui_snapshot_rejects_missing_kernel_before_package_restore(monkeypatch, tmp_path):
    webui_path = tmp_path / "demo"
    snapshot = make_webui_snapshot(webui_path)
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    def fail_restore(*_args, **_kwargs):
        raise AssertionError("package restore should not run when kernel directory is missing")

    monkeypatch.setattr(restore_service, "restore_python_packages", fail_restore)

    with pytest.raises(FileNotFoundError, match="内核目录不存在"):
        restore_utils.restore_webui_snapshot(
            snapshot_path=output,
            webui_path=webui_path,
            expected_webui_type="demo",
        )


def test_restore_webui_snapshot_allows_missing_path_for_package_kernel_webui(monkeypatch, tmp_path):
    webui_path = tmp_path / "invokeai"
    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "invokeai"
    snapshot.webui.name = "InvokeAI"
    snapshot.kernel = snapshot_utils.RepositorySnapshot(
        path=webui_path,
        name="invokeai",
        is_git_repo=True,
        url="https://example.test/invokeai-root.git",
        commit="abcdef",
    )
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    events = []
    monkeypatch.setattr(restore_service, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(restore_service, "restore_python_packages", lambda snapshot, options: events.append(("packages", snapshot.webui.type)))
    monkeypatch.setattr(
        restore_service,
        "restore_git_repository",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("package-kernel WebUI should not restore Git kernel")),
    )
    monkeypatch.setattr(restore_service, "restore_extensions", lambda snapshot, webui_path, options: events.append(("extensions", webui_path)))

    restore_utils.restore_webui_snapshot(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="invokeai",
    )

    assert events == [("packages", "invokeai"), ("extensions", webui_path)]


def test_restore_python_packages_prioritizes_pytorch_skips_missing_local_and_prunes(monkeypatch, tmp_path):
    missing_local = tmp_path / "missing-local"
    existing_local = tmp_path / "existing-local"
    existing_local.mkdir()
    snapshot = make_webui_snapshot(tmp_path / "demo")
    snapshot.packages = [
        make_package_snapshot("sd-webui-all-in-one", "99.0.0"),
        make_package_snapshot("Torch", "2.7.0+cu128"),
        make_package_snapshot("torchvision", "0.22.0+cu128"),
        make_package_snapshot("demo-pkg", "2.0.0"),
        make_package_snapshot("other-pkg", "3.0.0"),
        make_package_snapshot(
            "editable-existing",
            "1.0.0",
            direct_url=snapshot_utils.DirectUrlSnapshot(
                url=existing_local.as_uri(),
                dir_info=snapshot_utils.DirectUrlDirInfo(editable=True),
            ),
            editable=True,
        ),
        make_package_snapshot(
            "editable-local",
            "1.0.0",
            direct_url=snapshot_utils.DirectUrlSnapshot(
                url=missing_local.as_uri(),
                dir_info=snapshot_utils.DirectUrlDirInfo(editable=True),
            ),
            editable=True,
        ),
        make_package_snapshot("already", "1.0.0"),
    ]

    monkeypatch.setattr(
        restore_packages,
        "collect_installed_packages",
        lambda **_kwargs: [
            make_package_snapshot("demo_pkg", "1.0.0"),
            make_package_snapshot("already", "1.0.0"),
            make_package_snapshot("old_pkg", "0.1.0"),
            make_package_snapshot("pip", "25.0"),
            make_package_snapshot("sd-webui-all-in-one", "1.0.0"),
        ],
    )
    monkeypatch.setattr(restore_packages, "get_pypi_mirror_config", lambda use_cn_mirror: {"PIP_INDEX_URL": "https://pypi.example"})

    mirror_calls = []
    env_calls = []
    events = []

    def fake_get_pytorch_mirror(dtype, use_cn_mirror):
        mirror_calls.append((dtype, use_cn_mirror))
        return "https://torch.example/cu128", "index_url"

    def fake_generate_env(index_url=None, extra_index_url=None, find_links=None):
        env_calls.append(
            {
                "index_url": index_url,
                "extra_index_url": extra_index_url,
                "find_links": find_links,
            }
        )
        return {"TORCH_INDEX": str(index_url)}

    def fake_install_pytorch_with_fallback(**kwargs):
        events.append(("pytorch", kwargs))

    def fake_pip_install(*args, **kwargs):
        events.append(("pip", args, kwargs))

    def fake_run_cmd(cmd, **_kwargs):
        events.append(("uninstall", cmd))

    monkeypatch.setattr(restore_packages, "get_pytorch_mirror", fake_get_pytorch_mirror)
    monkeypatch.setattr(restore_packages, "generate_uv_and_pip_env_mirror_config", fake_generate_env)
    monkeypatch.setattr(restore_packages, "install_pytorch_with_fallback", fake_install_pytorch_with_fallback)
    monkeypatch.setattr(restore_packages, "pip_install", fake_pip_install)
    monkeypatch.setattr(restore_packages, "run_cmd", fake_run_cmd)

    restore_utils.restore_python_packages(
        snapshot,
        restore_utils.SnapshotRestoreOptions(prune_packages=True, use_uv=False, use_pypi_mirror=True),
    )

    assert mirror_calls == [("cu128", True)]
    assert env_calls == [
        {
            "index_url": "https://torch.example/cu128",
            "extra_index_url": [],
            "find_links": [],
        }
    ]
    assert events[0][0] == "pytorch"
    assert events[0][1]["torch_package"] == ["Torch==2.7.0+cu128", "torchvision==0.22.0+cu128", "--no-deps"]
    assert events[0][1]["xformers_package"] is None
    assert events[0][1]["use_uv"] is False
    pip_events = [event for event in events if event[0] == "pip"]
    assert pip_events == [
        (
            "pip",
            (
                "demo-pkg==2.0.0",
                "other-pkg==3.0.0",
                "-e",
                existing_local.as_posix(),
                "--no-deps",
            ),
            {"use_uv": False, "custom_env": {"PIP_INDEX_URL": "https://pypi.example"}},
        )
    ]
    assert not any(event[0] == "pip" and "editable-local" in event[1][0] for event in events)
    assert not any(event[0] == "pip" and "sd-webui-all-in-one" in event[1][0] for event in events)
    assert events[-1][0] == "uninstall"
    uninstall_names = events[-1][1][4:-1]
    assert uninstall_names == ["old_pkg"]


def test_restore_webui_snapshot_blocks_dirty_repositories_before_modifying_environment(monkeypatch, tmp_path):
    webui_path = tmp_path / "ComfyUI"
    custom_nodes = webui_path / "custom_nodes"
    for name in ("CleanNode", "DirtyNode", "UnknownNode"):
        (custom_nodes / name).mkdir(parents=True)
    snapshot = make_webui_snapshot(webui_path)
    snapshot.webui.type = "comfyui"
    snapshot.kernel = make_git_repo_snapshot(webui_path)
    snapshot.extensions = [make_extension_snapshot(name, custom_nodes / name, True) for name in ("CleanNode", "DirtyNode", "UnknownNode", "MissingNode")]
    output = tmp_path / "snapshot.json"
    snapshot_utils.save_snapshot(snapshot, output)

    dirty_by_name = {"ComfyUI": False, "CleanNode": False, "DirtyNode": True, "UnknownNode": None}
    monkeypatch.setattr(
        restore_extensions,
        "probe_repository",
        # 仓库均需切换 commit, 已位于快照 commit 的仓库不会被修改, 不参与阻断
        lambda path: RepositoryProbe(path=path, is_git_repo=True, commit="123456", dirty=dirty_by_name[path.name]),
    )

    def fail_restore(*_args, **_kwargs):
        raise AssertionError("nothing should be modified while a repository is dirty")

    monkeypatch.setattr(restore_service, "restore_python_packages", fail_restore)
    monkeypatch.setattr(restore_service, "restore_git_repository", fail_restore)
    monkeypatch.setattr(restore_service, "restore_extensions", fail_restore)

    with pytest.raises(RuntimeError, match="存在未提交变更") as exc_info:
        restore_utils.restore_webui_snapshot(snapshot_path=output, webui_path=webui_path, expected_webui_type="comfyui")

    message = str(exc_info.value)
    assert "DirtyNode" in message
    assert "UnknownNode" in message
    assert "CleanNode" not in message

    events = []
    monkeypatch.setattr(restore_service, "apply_git_base_config_and_github_mirror", lambda **kwargs: kwargs["origin_env"])
    monkeypatch.setattr(restore_service, "restore_python_packages", lambda snapshot, options: events.append("packages"))
    monkeypatch.setattr(restore_service, "restore_git_repository", lambda repo, target_path, options: events.append("kernel"))
    monkeypatch.setattr(restore_service, "restore_extensions", lambda snapshot, webui_path, options: events.append("extensions"))

    restore_utils.restore_webui_snapshot(
        snapshot_path=output,
        webui_path=webui_path,
        expected_webui_type="comfyui",
        options=restore_utils.SnapshotRestoreOptions(force_git_reset=True),
    )

    assert events == ["packages", "kernel", "extensions"]
