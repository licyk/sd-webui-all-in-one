"""WebUI 与软件包更新检查测试"""

import json

import sd_webui_all_in_one.base_manager.version_manager as version_manager
from sd_webui_all_in_one.base_manager.base import PyTorchUpdateStatus
from sd_webui_all_in_one.base_manager.version_manager import checks as version_checks
from sd_webui_all_in_one.base_manager.version_manager import indexes as version_indexes


def test_check_webui_updates_aggregates_kernel_extensions_and_pytorch(monkeypatch, tmp_path):
    kernel = version_manager.RepositoryUpdateStatus(name="demo", path=tmp_path, is_git_repo=True, has_update=True, behind=2)
    pytorch = PyTorchUpdateStatus(True, "2.7.0+cu128", "cu128", "2.8.0+cu128", "Torch CUDA", True)
    extensions = [
        version_manager.ManagedExtension("git-ext", tmp_path / "git-ext", True, True, commit="local", source_type="git"),
        version_manager.ManagedExtension("file-ext", tmp_path / "file-ext.py", True, False, source_type="file"),
    ]
    monkeypatch.setattr(
        version_checks,
        "check_repository_update",
        lambda path, **_kwargs: (
            kernel
            if path == tmp_path
            else version_manager.RepositoryUpdateStatus(name=path.name, path=path, is_git_repo=True, current_commit="local", remote_commit="remote", has_update=True, behind=1)
        ),
    )
    monkeypatch.setattr(version_checks, "get_pytorch_update_status", lambda: pytorch)

    result = version_manager.check_webui_updates(
        "demo",
        "Demo WebUI",
        tmp_path,
        extension_loader=lambda: extensions,
        options=version_manager.WebUiUpdateOptions(fetch=False),
    )

    assert result.kernel is kernel
    assert result.pytorch is pytorch
    assert result.extensions_supported is True
    assert result.extensions[0].latest_version == "remote"
    assert result.extensions[1].skipped is True
    assert result.summary == version_manager.WebUiUpdateSummary(
        has_update=True,
        kernel_has_update=True,
        pytorch_has_update=True,
        extension_update_count=1,
        checked_extension_count=1,
        skipped_count=1,
        error_count=0,
    )


def test_check_webui_updates_configures_mirror_once_and_overlaps_kernel_with_extensions(monkeypatch, tmp_path):
    import threading

    extensions = [version_manager.ManagedExtension(f"ext-{index}", tmp_path / f"ext-{index}", True, True, source_type="git") for index in range(2)]
    # 内核与全部扩展必须同时处于检查中才能通过屏障, 证明内核检查不再串行阻塞扩展检查
    barrier = threading.Barrier(len(extensions) + 1, timeout=5)
    mirror_calls = []

    def fake_check(path, fetch=True, **kwargs):
        assert not kwargs, "mirror must be configured once before the parallel checks"
        assert fetch is True
        barrier.wait()
        return version_manager.RepositoryUpdateStatus(name=path.name, path=path, is_git_repo=True, has_update=path == tmp_path, behind=int(path == tmp_path))

    monkeypatch.setattr(version_checks, "configure_git_env", lambda **kwargs: mirror_calls.append(kwargs) or {})
    monkeypatch.setattr(version_checks, "check_repository_update", fake_check)

    result = version_manager.check_webui_updates(
        "demo",
        "Demo WebUI",
        tmp_path,
        extension_loader=lambda: extensions,
        options=version_manager.WebUiUpdateOptions(include_pytorch=False, use_github_mirror=True, custom_github_mirror="https://mirror.example"),
    )

    assert mirror_calls == [{"use_github_mirror": True, "custom_github_mirror": "https://mirror.example"}]
    assert result.kernel is not None and result.kernel.has_update is True
    assert [item.name for item in result.extensions] == ["ext-0", "ext-1"]
    assert result.summary.error_count == 0


def test_check_webui_updates_reports_extension_loader_failure(monkeypatch, tmp_path):
    def broken_loader():
        raise OSError("boom")

    monkeypatch.setattr(version_checks, "check_repository_update", lambda path, **_kwargs: version_manager.RepositoryUpdateStatus(name=path.name, path=path, is_git_repo=True))

    result = version_manager.check_webui_updates(
        "demo",
        "Demo WebUI",
        tmp_path,
        extension_loader=broken_loader,
        options=version_manager.WebUiUpdateOptions(include_pytorch=False, fetch=False),
    )

    assert result.errors == ["加载扩展失败: boom"]
    assert result.extensions == []
    assert result.kernel is not None


def test_check_package_update_records_versions(monkeypatch):
    monkeypatch.setattr(version_checks, "get_package_version_from_library", lambda _name: "4.0.0")
    monkeypatch.setattr(version_checks, "fetch_pypi_versions", lambda *_args, **_kwargs: [version_manager.PackageVersionInfo("5.0.0")])

    status = version_manager.check_package_update("invokeai", "InvokeAI", "https://pypi.example")

    assert status.installed is True
    assert status.current_version == "4.0.0"
    assert status.latest_version == "5.0.0"
    assert status.has_update is True
    assert status.error is None


_DEFAULT_PYPI_RELEASES = {
    "6.7.0": [{"upload_time": "2025-10-05T00:00:00"}],
    "6.8.1": [{"upload_time": "2025-12-01T00:00:00"}],
    "6.9.0": [{"upload_time": "2026-01-02T00:00:00"}],
}


def _stub_pypi_payload(monkeypatch, releases=None):
    payload = json.dumps(
        {
            "info": {"summary": "InvokeAI"},
            "releases": _DEFAULT_PYPI_RELEASES if releases is None else releases,
        }
    ).encode("utf-8")

    class _Response:
        def read(self):
            return payload

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

    monkeypatch.setattr(version_indexes.urllib.request, "urlopen", lambda *_args, **_kwargs: _Response())


def test_fetch_pypi_versions_resolves_the_installed_release_when_not_given_one(monkeypatch):
    _stub_pypi_payload(monkeypatch)
    monkeypatch.setattr(version_indexes, "get_package_version_from_library", lambda _name: "6.8.1")

    versions = version_manager.fetch_pypi_versions("invokeai")

    assert [item.version for item in versions] == ["6.9.0", "6.8.1", "6.7.0"]
    assert [item.is_current for item in versions] == [False, True, False]


def test_fetch_pypi_versions_keeps_an_explicitly_supplied_current_version(monkeypatch):
    _stub_pypi_payload(monkeypatch)
    monkeypatch.setattr(version_indexes, "get_package_version_from_library", lambda _name: "6.8.1")

    versions = version_manager.fetch_pypi_versions("invokeai", current_version="6.7.0")

    assert [item.is_current for item in versions] == [False, False, True]


# PyPI 上正式版本与预发布版本混排, 且 post-release 排在同号正式版本之后。
_MIXED_CHANNEL_RELEASES = {
    "6.9.0": [{"upload_time": "2026-01-02T00:00:00"}],
    "6.9.0rc1": [{"upload_time": "2025-12-20T00:00:00"}],
    "6.9.0.post1": [{"upload_time": "2026-01-09T00:00:00"}],
    "6.10.0rc1": [{"upload_time": "2026-02-01T00:00:00"}],
    "6.11.0.dev1": [{"upload_time": "2026-02-10T00:00:00"}],
}


def test_fetch_pypi_versions_flags_prereleases(monkeypatch):
    _stub_pypi_payload(monkeypatch, _MIXED_CHANNEL_RELEASES)
    monkeypatch.setattr(version_indexes, "get_package_version_from_library", lambda _name: "6.9.0")

    versions = version_manager.fetch_pypi_versions("invokeai")

    # PEP 440 顺序: dev/rc 归入各自 release 段, post-release 排在同号正式版本之后。
    assert [item.version for item in versions] == [
        "6.11.0.dev1",
        "6.10.0rc1",
        "6.9.0.post1",
        "6.9.0",
        "6.9.0rc1",
    ]
    # 预发布标记是每个版本自带的结构化字段, 调用方无需再解析版本号字符串。
    assert [item.is_prerelease for item in versions] == [True, True, False, False, True]


def test_check_package_update_ignores_prereleases(monkeypatch):
    _stub_pypi_payload(monkeypatch, _MIXED_CHANNEL_RELEASES)
    monkeypatch.setattr(version_checks, "get_package_version_from_library", lambda _name: "6.9.0.post1")

    status = version_manager.check_package_update("invokeai", "InvokeAI", "https://pypi.example")

    # 已安装的是最新正式版本, 更高版本号的 rc/dev 不构成更新。
    assert status.latest_version == "6.9.0.post1"
    assert status.has_update is False
    assert status.error is None
    # 预发布通道单独报告, 不参与更新判定。
    assert status.latest_prerelease == "6.11.0.dev1"


def test_check_package_update_can_target_prereleases(monkeypatch):
    _stub_pypi_payload(monkeypatch, _MIXED_CHANNEL_RELEASES)
    monkeypatch.setattr(version_checks, "get_package_version_from_library", lambda _name: "6.9.0.post1")

    status = version_manager.check_package_update(
        "invokeai",
        "InvokeAI",
        "https://pypi.example",
        allow_prerelease=True,
    )

    assert status.latest_version == "6.11.0.dev1"
    assert status.has_update is True
    # 最新版本本身就是预发布版本时, 预发布通道没有额外进展可报告。
    assert status.latest_prerelease is None


def test_check_package_update_reports_a_package_without_a_release(monkeypatch):
    _stub_pypi_payload(monkeypatch, {"1.0.0rc1": [{"upload_time": "2026-01-02T00:00:00"}]})
    monkeypatch.setattr(version_checks, "get_package_version_from_library", lambda _name: None)

    status = version_manager.check_package_update("invokeai", "InvokeAI", "https://pypi.example")

    # 只发布过预发布版本时没有可更新到的正式版本, 这与取不到版本列表是两回事。
    assert status.latest_version is None
    assert status.has_update is False
    assert status.error == "未获取到 PyPI 正式发布版本"
    assert status.latest_prerelease == "1.0.0rc1"
