"""WebUI API adapter。"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Callable, Literal, TypeAlias, cast
from urllib.parse import urlparse

from sd_webui_all_in_one.base_manager import comfyui_base, fooocus_base, invokeai_base, qwen_tts_webui_base, sd_scripts_base, sd_trainer_base, sd_webui_base
from sd_webui_all_in_one.base_manager.base import get_repo_name_from_url
from sd_webui_all_in_one.base_manager.comfy_registry import (
    fetch_comfy_registry_extension_index,
    fetch_comfy_registry_versions,
)
from sd_webui_all_in_one.base_manager.comfyui_base import ComfyUiExtensionManager
from sd_webui_all_in_one.base_manager.hotpatcher_manager import DEFAULT_RUNTIME_PORT
from sd_webui_all_in_one.base_manager.snapshot import (
    WebUiSnapshot,
    default_snapshot_output,
    json_safe,
    load_snapshot,
    save_snapshot,
    snapshot_to_dict,
)
from sd_webui_all_in_one.base_manager.snapshot_restore import (
    SnapshotRestoreOptions,
    preview_webui_snapshot_restore,
    restore_webui_snapshot,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    DEFAULT_EXTENSION_INDEX_URL,
    ExtensionIndexItem,
    ExtensionManager,
    WebUiUpdateOptions,
    WebUiUpdateStatus,
    fetch_comfyui_custom_node_index,
    fetch_extension_index,
    fetch_pypi_versions,
    filter_extension_index,
    inspect_repository,
    list_branches,
    list_commits,
    switch_repository_branch,
    switch_repository_commit,
    update_repository,
)
from sd_webui_all_in_one.downloader import download_archive_and_unpack, download_file
from sd_webui_all_in_one.file_manager import move_files, remove_files
from sd_webui_all_in_one.mirror_manager import PYPI_INDEX_MIRROR_OFFICIAL, PYPI_INDEX_MIRROR_TENCENT

SnapshotFactory = Callable[[Path, bool], WebUiSnapshot]
UpdateChecker = Callable[[Path, WebUiUpdateOptions | None], WebUiUpdateStatus]

WebUiApiType: TypeAlias = Literal[
    "sd_webui",
    "comfyui",
    "fooocus",
    "invokeai",
    "sd_trainer",
    "sd_scripts",
    "qwen_tts_webui",
]
"""API 支持的 WebUI 类型。"""


def _dataclass_list(items: Iterable[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        if not is_dataclass(item):
            raise TypeError(f"Expected dataclass instance, got {type(item).__name__}")
        data = json_safe(asdict(item))
        if not isinstance(data, dict):
            raise TypeError(f"Expected dataclass dict, got {type(data).__name__}")
        result.append(cast(dict[str, Any], data))
    return result


def _dataclass_dict(item: Any) -> dict[str, Any]:
    if not is_dataclass(item):
        raise TypeError(f"Expected dataclass instance, got {type(item).__name__}")
    data = json_safe(asdict(item))
    if not isinstance(data, dict):
        raise TypeError(f"Expected dataclass dict, got {type(data).__name__}")
    return cast(dict[str, Any], data)


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_json_object(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def _sd_webui_extension_enabled(sd_webui_path: Path, name: str, _path: Path) -> bool:
    settings = _load_json_object(sd_webui_path / "config.json")
    disabled_extensions = set(settings.get("disabled_extensions", []))
    disable_all_extensions = settings.get("disable_all_extensions", "none")
    if disable_all_extensions == "all":
        return False
    if disable_all_extensions == "extra":
        return True
    return name not in disabled_extensions


def _set_sd_webui_extension_enabled(sd_webui_path: Path, name: str, enabled: bool) -> None:
    settings = _load_json_object(sd_webui_path / "config.json")
    disabled_extensions = settings.setdefault("disabled_extensions", [])
    if not isinstance(disabled_extensions, list):
        disabled_extensions = []
        settings["disabled_extensions"] = disabled_extensions
    if enabled and name in disabled_extensions:
        disabled_extensions.remove(name)
    elif not enabled and name not in disabled_extensions:
        disabled_extensions.append(name)
    _save_json_object(sd_webui_path / "config.json", settings)


def _invokeai_node_enabled(_name: str, path: Path) -> bool:
    return (path / "__init__.py").is_file()


def _set_invokeai_node_enabled(nodes_path: Path, name: str, enabled: bool) -> None:
    init_py = nodes_path / name / "__init__.py"
    init_bak_py = nodes_path / name / "__init__.py.bak"
    if enabled:
        if init_bak_py.is_file() and not init_py.is_file():
            move_files(init_bak_py, init_py)
    else:
        if init_py.is_file():
            move_files(init_py, init_bak_py)


def _download_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    filename = Path(parsed.path).name
    return filename or get_repo_name_from_url(url)


class WebUiApiAdapter:
    """统一 WebUI API adapter。"""

    def __init__(
        self,
        webui_type: WebUiApiType,
        display_name: str,
        snapshot_factory: SnapshotFactory,
        update_checker: UpdateChecker | None = None,
    ) -> None:
        self.webui_type = webui_type
        self.display_name = display_name
        self._snapshot_factory = snapshot_factory
        self._update_checker = update_checker

    def repository_status(self, webui_path: Path) -> dict[str, Any]:
        """读取内核仓库状态。

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            dict[str, Any]: 仓库状态信息。
        """
        return {"repository": json_safe(asdict(inspect_repository(webui_path)))}

    def list_branches(self, webui_path: Path, fetch: bool = True) -> dict[str, Any]:
        """列出内核分支。

        Args:
            webui_path (Path): WebUI 根目录。
            fetch (bool): 是否先从远端拉取分支信息。

        Returns:
            dict[str, Any]: 分支列表。
        """
        return {"branches": _dataclass_list(list_branches(webui_path, fetch=fetch))}

    def list_commits(self, webui_path: Path, limit: int | None = 100) -> dict[str, Any]:
        """列出内核提交。

        Args:
            webui_path (Path): WebUI 根目录。
            limit (int | None): 最大提交数量。

        Returns:
            dict[str, Any]: 提交列表。
        """
        return {"commits": _dataclass_list(list_commits(webui_path, limit=limit))}

    def switch_branch(self, webui_path: Path, branch: str, new_url: str | None = None, recurse_submodules: bool = False) -> dict[str, Any]:
        """切换内核分支。

        Args:
            webui_path (Path): WebUI 根目录。
            branch (str): 目标分支。
            new_url (str | None): 可选的新远端地址。
            recurse_submodules (bool): 是否递归处理子模块。

        Returns:
            dict[str, Any]: 切换结果。
        """
        switch_repository_branch(webui_path, branch=branch, new_url=new_url, recurse_submodules=recurse_submodules)
        return {"changed": True}

    def switch_commit(self, webui_path: Path, commit: str) -> dict[str, Any]:
        """切换内核提交。

        Args:
            webui_path (Path): WebUI 根目录。
            commit (str): 目标提交 ID。

        Returns:
            dict[str, Any]: 切换结果。
        """
        switch_repository_commit(webui_path, commit=commit)
        return {"changed": True}

    def update(self, webui_path: Path) -> dict[str, Any]:
        """更新内核仓库。

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            dict[str, Any]: 更新结果。
        """
        update_repository(webui_path)
        return {"updated": True}

    def check_updates(
        self,
        webui_path: Path,
        fetch: bool = True,
        include_kernel: bool = True,
        include_extensions: bool = True,
        include_pytorch: bool = True,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
        use_pypi_mirror: bool = False,
        pypi_index_url: str | None = None,
        timeout: int | None = 20,
    ) -> dict[str, Any]:
        """检查 WebUI 内核、扩展和 PyTorch 更新。

        Args:
            webui_path (Path): WebUI 根目录。
            fetch (bool): 是否拉取远程引用。
            include_kernel (bool): 是否检查内核。
            include_extensions (bool): 是否检查扩展。
            include_pytorch (bool): 是否检查 PyTorch。
            use_github_mirror (bool): 是否使用 GitHub 镜像。
            custom_github_mirror (str | list[str] | None): 自定义 GitHub 镜像。
            use_pypi_mirror (bool): 是否使用 PyPI 镜像。
            pypi_index_url (str | None): 自定义 PyPI 索引地址。
            timeout (int | None): 网络请求超时秒数。

        Returns:
            dict[str, Any]: 更新检查结果。

        Raises:
            NotImplementedError: Adapter 未配置更新检查函数时抛出。
        """
        if self._update_checker is None:
            raise NotImplementedError(f"{self.display_name} does not provide an update checker")
        update_options = WebUiUpdateOptions(
            fetch=fetch,
            include_kernel=include_kernel,
            include_extensions=include_extensions,
            include_pytorch=include_pytorch,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
            pypi_index_url=pypi_index_url or (PYPI_INDEX_MIRROR_TENCENT if use_pypi_mirror else PYPI_INDEX_MIRROR_OFFICIAL),
            timeout=timeout,
        )
        return _dataclass_dict(self._update_checker(webui_path, update_options))

    def snapshot_dir(self, webui_path: Path, snapshot_dir: Path | None = None) -> Path:
        """获取快照目录。

        Args:
            webui_path (Path): WebUI 根目录。
            snapshot_dir (Path | None): 显式指定的快照目录。

        Returns:
            Path: 实际使用的快照目录。
        """
        return snapshot_dir or webui_path / "snapshots"

    def list_snapshots(self, webui_path: Path, snapshot_dir: Path | None = None) -> dict[str, Any]:
        """列出快照文件。

        Args:
            webui_path (Path): WebUI 根目录。
            snapshot_dir (Path | None): 显式指定的快照目录。

        Returns:
            dict[str, Any]: 快照文件列表。
        """
        directory = self.snapshot_dir(webui_path, snapshot_dir=snapshot_dir)
        if not directory.exists():
            return {"snapshots": []}
        snapshots: list[dict[str, Any]] = []
        for item in sorted(directory.glob("*.json"), key=lambda file: file.stat().st_mtime, reverse=True):
            try:
                snapshot = load_snapshot(item)
            except Exception as exc:
                snapshots.append({"path": item.as_posix(), "filename": item.name, "error": str(exc)})
                continue
            snapshots.append(
                {
                    "path": item.as_posix(),
                    "filename": item.name,
                    "created_at": snapshot.created_at,
                    "webui_type": snapshot.webui.type,
                    "webui_name": snapshot.webui.name,
                    "package_count": len(snapshot.packages),
                    "extension_count": len(snapshot.extensions),
                }
            )
        return {"snapshots": snapshots}

    def read_snapshot(self, snapshot_path: Path) -> dict[str, Any]:
        """读取快照文件。

        Args:
            snapshot_path (Path): 快照文件路径。

        Returns:
            dict[str, Any]: 快照内容。
        """
        return {"snapshot": snapshot_to_dict(load_snapshot(snapshot_path))}

    def create_snapshot(self, webui_path: Path, include_packages: bool = True, output_dir: Path | None = None) -> dict[str, Any]:
        """创建快照。

        Args:
            webui_path (Path): WebUI 根目录。
            include_packages (bool): 是否包含 Python 包列表。
            output_dir (Path | None): 快照输出目录。

        Returns:
            dict[str, Any]: 快照路径和内容。
        """
        snapshot = self._snapshot_factory(webui_path, include_packages)
        output = default_snapshot_output(snapshot, output_dir=output_dir)
        save_snapshot(snapshot, output)
        return {"path": output.as_posix(), "snapshot": snapshot_to_dict(snapshot)}

    def delete_snapshot(self, snapshot_path: Path) -> dict[str, Any]:
        """删除快照文件。

        Args:
            snapshot_path (Path): 快照文件路径。

        Returns:
            dict[str, Any]: 删除结果。

        Raises:
            FileNotFoundError: 快照文件不存在。
        """
        if not snapshot_path.is_file():
            raise FileNotFoundError(f"Snapshot not found: {snapshot_path}")
        remove_files(snapshot_path)
        return {"deleted": True, "path": snapshot_path.as_posix()}

    def preview_restore_snapshot(
        self,
        webui_path: Path,
        snapshot_path: Path,
        prune_packages: bool = False,
        prune_extensions: bool = False,
        force_git_reset: bool = False,
        use_uv: bool = True,
        use_pypi_mirror: bool = True,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """预览快照恢复计划。

        Args:
            webui_path (Path): WebUI 根目录。
            snapshot_path (Path): 快照文件路径。
            prune_packages (bool): 是否移除快照外的包。
            prune_extensions (bool): 是否移除快照外的扩展。
            force_git_reset (bool): 是否强制重置 Git 工作树。
            use_uv (bool): 是否使用 uv。
            use_pypi_mirror (bool): 是否使用 PyPI 镜像。
            use_github_mirror (bool): 是否使用 GitHub 镜像。
            custom_github_mirror (str | list[str] | None): 自定义 GitHub 镜像。

        Returns:
            dict[str, Any]: 恢复计划。
        """
        plan = preview_webui_snapshot_restore(
            snapshot_path=snapshot_path,
            webui_path=webui_path,
            expected_webui_type=self.webui_type,
            options=SnapshotRestoreOptions(
                prune_packages=prune_packages,
                prune_extensions=prune_extensions,
                force_git_reset=force_git_reset,
                use_uv=use_uv,
                use_pypi_mirror=use_pypi_mirror,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            ),
        )
        return {"plan": json_safe(asdict(plan))}

    def restore_snapshot(
        self,
        webui_path: Path,
        snapshot_path: Path,
        prune_packages: bool = False,
        prune_extensions: bool = False,
        force_git_reset: bool = False,
        use_uv: bool = True,
        use_pypi_mirror: bool = True,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """恢复快照。

        Args:
            webui_path (Path): WebUI 根目录。
            snapshot_path (Path): 快照文件路径。
            prune_packages (bool): 是否移除快照外的包。
            prune_extensions (bool): 是否移除快照外的扩展。
            force_git_reset (bool): 是否强制重置 Git 工作树。
            use_uv (bool): 是否使用 uv。
            use_pypi_mirror (bool): 是否使用 PyPI 镜像。
            use_github_mirror (bool): 是否使用 GitHub 镜像。
            custom_github_mirror (str | list[str] | None): 自定义 GitHub 镜像。

        Returns:
            dict[str, Any]: 恢复结果。
        """
        restore_webui_snapshot(
            snapshot_path=snapshot_path,
            webui_path=webui_path,
            expected_webui_type=self.webui_type,
            options=SnapshotRestoreOptions(
                prune_packages=prune_packages,
                prune_extensions=prune_extensions,
                force_git_reset=force_git_reset,
                use_uv=use_uv,
                use_pypi_mirror=use_pypi_mirror,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            ),
        )
        return {"restored": True}

    def extension_manager(self, webui_path: Path):
        """获取对应 WebUI 的扩展管理器。

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            Any: 对应 WebUI 的扩展管理器。

        Raises:
            NotImplementedError: 当前 WebUI 类型不支持扩展管理。
        """
        if self.webui_type == "sd_webui":
            return ExtensionManager(
                root_path=webui_path,
                extension_dir_name="extensions",
                is_enabled=lambda name, path: _sd_webui_extension_enabled(webui_path, name, path),
                set_enabled=lambda name, enabled: _set_sd_webui_extension_enabled(webui_path, name, enabled),
            )
        if self.webui_type == "comfyui":
            return ComfyUiExtensionManager(webui_path, include_files=True)
        if self.webui_type == "invokeai":
            return ExtensionManager(
                root_path=webui_path,
                extension_dir_name="nodes",
                is_enabled=_invokeai_node_enabled,
                set_enabled=lambda name, enabled: _set_invokeai_node_enabled(webui_path / "nodes", name, enabled),
            )
        raise NotImplementedError(f"{self.display_name} does not support extension management")

    def list_extensions(self, webui_path: Path) -> dict[str, Any]:
        """列出扩展。

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            dict[str, Any]: 扩展列表。
        """
        return {"extensions": _dataclass_list(self.extension_manager(webui_path).list_extensions())}

    def set_extension_enabled(self, webui_path: Path, name: str, enabled: bool) -> dict[str, Any]:
        """设置扩展启用状态。

        Args:
            webui_path (Path): WebUI 根目录。
            name (str): 扩展名称。
            enabled (bool): 是否启用扩展。

        Returns:
            dict[str, Any]: 修改结果。
        """
        self.extension_manager(webui_path).set_extension_enabled(name, enabled)
        return {"changed": True}

    def install_extension(self, webui_path: Path, url: str, use_github_mirror: bool = False, custom_github_mirror: str | list[str] | None = None) -> dict[str, Any]:
        """从 Git URL 安装扩展。

        Args:
            webui_path (Path): WebUI 根目录。
            url (str): 扩展 Git URL。
            use_github_mirror (bool): 是否使用 GitHub 镜像。
            custom_github_mirror (str | list[str] | None): 自定义 GitHub 镜像。

        Returns:
            dict[str, Any]: 安装结果。
        """
        path = self.extension_manager(webui_path).install_extension(url, use_github_mirror=use_github_mirror, custom_github_mirror=custom_github_mirror)
        return {"installed": True, "path": path.as_posix()}

    def update_extension(self, webui_path: Path, name: str) -> dict[str, Any]:
        """更新扩展。

        Args:
            webui_path (Path): WebUI 根目录。
            name (str): 扩展名称。

        Returns:
            dict[str, Any]: 更新结果。
        """
        self.extension_manager(webui_path).update_extension(name)
        return {"updated": True}

    def update_all_extensions(self, webui_path: Path) -> dict[str, Any]:
        """更新所有扩展。

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            dict[str, Any]: 更新结果。
        """
        self.extension_manager(webui_path).update_all()
        return {"updated": True}

    def uninstall_extension(self, webui_path: Path, name: str) -> dict[str, Any]:
        """卸载扩展。

        Args:
            webui_path (Path): WebUI 根目录。
            name (str): 扩展名称。

        Returns:
            dict[str, Any]: 卸载结果。
        """
        self.extension_manager(webui_path).uninstall_extension(name)
        return {"uninstalled": True}

    def switch_extension_commit(self, webui_path: Path, name: str, commit: str) -> dict[str, Any]:
        """切换扩展提交。

        Args:
            webui_path (Path): WebUI 根目录。
            name (str): 扩展名称。
            commit (str): 目标提交 ID。

        Returns:
            dict[str, Any]: 切换结果。
        """
        self.extension_manager(webui_path).switch_extension_commit(name, commit)
        return {"changed": True}

    def switch_extension_branch(self, webui_path: Path, name: str, branch: str) -> dict[str, Any]:
        """切换扩展分支。

        Args:
            webui_path (Path): WebUI 根目录。
            name (str): 扩展名称。
            branch (str): 目标分支。

        Returns:
            dict[str, Any]: 切换结果。
        """
        self.extension_manager(webui_path).switch_extension_branch(name, branch)
        return {"changed": True}

    def fetch_extension_index(
        self,
        webui_path: Path,
        query: str = "",
        tags: list[str] | None = None,
        index_url: str | None = None,
        timeout: int | None = 20,
        registry_search: str | None = None,
        registry_limit: int | None = None,
        registry_page_size: int = 500,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """获取扩展源。

        Args:
            webui_path (Path): WebUI 根目录。
            query (str): 本地过滤关键词。
            tags (list[str] | None): 本地标签过滤。
            index_url (str | None): 扩展索引地址。
            timeout (int | None): 请求超时秒数。
            registry_search (str | None): Comfy Registry 搜索词。
            registry_limit (int | None): Registry 最大结果数。
            registry_page_size (int): Registry 每页数量。
            force_refresh (bool): 是否强制刷新 Registry 缓存。

        Returns:
            dict[str, Any]: 可安装扩展列表。

        Raises:
            NotImplementedError: 当前 WebUI 类型不支持扩展源。
        """
        normalized_tags = tuple(tags or ())
        installed_names = {item.name for item in self.extension_manager(webui_path).list_extensions()}
        if self.webui_type == "sd_webui":
            items = fetch_extension_index(index_url or DEFAULT_EXTENSION_INDEX_URL, timeout=timeout)
        elif self.webui_type == "comfyui":
            manager_items = fetch_comfyui_custom_node_index(index_url or "https://raw.githubusercontent.com/Comfy-Org/ComfyUI-Manager/refs/heads/main/custom-node-list.json", timeout=timeout)
            registry_items = fetch_comfy_registry_extension_index(
                search=registry_search,
                limit=registry_limit,
                page_size=registry_page_size,
                force_refresh=force_refresh,
            )
            items = [*manager_items, *registry_items]
        else:
            raise NotImplementedError(f"{self.display_name} does not support extension index")
        filtered_items = _dataclass_list(filter_extension_index(items, keyword=query, tags=normalized_tags))
        for item in filtered_items:
            name = item.get("name")
            registry_id = item.get("registry_id")
            url = item.get("url")
            reference = item.get("reference")
            repo_name = get_repo_name_from_url(str(reference or url or name or ""))
            item["installed"] = name in installed_names or registry_id in installed_names or repo_name in installed_names
        return {"extensions": filtered_items}

    def install_extension_index_item(
        self,
        webui_path: Path,
        item: ExtensionIndexItem,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> dict[str, Any]:
        """安装扩展源条目。

        Args:
            webui_path (Path): WebUI 根目录。
            item (ExtensionIndexItem): 扩展源条目。
            use_github_mirror (bool): 是否使用 GitHub 镜像。
            custom_github_mirror (str | list[str] | None): 自定义 GitHub 镜像。

        Returns:
            dict[str, Any]: 安装结果。

        Raises:
            ValueError: 条目不可安装或安装类型不受支持。
        """
        if not item.installable:
            raise ValueError(f"'{item.name}' is not installable: {item.install_status or 'not installable'}")
        install_type = item.install_type.lower()
        manager = self.extension_manager(webui_path)
        if self.webui_type == "comfyui" and (item.source_type == "comfy-registry" or install_type == "comfy-registry"):
            node_id = item.registry_id or item.name
            path = manager.install_registry_extension(node_id, version=item.registry_version or None)
            return {"installed": True, "path": path.as_posix()}
        if install_type == "git-clone":
            repo = (item.files[0] if item.files else "") or item.reference or item.url
            path = manager.install_extension(repo, use_github_mirror=use_github_mirror, custom_github_mirror=custom_github_mirror)
            return {"installed": True, "path": path.as_posix()}
        if self.webui_type != "comfyui":
            raise ValueError(f"Unsupported install_type for {self.display_name}: {item.install_type}")
        custom_nodes_path = webui_path / "custom_nodes"
        custom_nodes_path.mkdir(parents=True, exist_ok=True)
        files = item.files or (item.url,)
        if install_type == "copy":
            for url in files:
                download_file(url=url, path=custom_nodes_path, save_name=_download_name_from_url(url), progress=False)
            return {"installed": True, "path": custom_nodes_path.as_posix()}
        if install_type in {"unzip", "zip"}:
            target_name = get_repo_name_from_url(item.reference or item.url or item.name).removesuffix(".zip")
            target_path = custom_nodes_path / target_name
            for url in files:
                download_archive_and_unpack(url=url, local_dir=target_path, name=_download_name_from_url(url))
            return {"installed": True, "path": target_path.as_posix()}
        raise ValueError(f"Unsupported install_type: {item.install_type}")

    def fetch_extension_versions(self, node_id: str, timeout: int | None = 20) -> dict[str, Any]:
        """获取扩展可切换版本。

        Args:
            node_id (str): Comfy Registry 节点 ID。
            timeout (int | None): 请求超时时间。

        Returns:
            dict[str, Any]: 可安装版本列表。

        Raises:
            NotImplementedError: 当前 WebUI 类型不支持 Registry 版本查询。
        """
        if self.webui_type != "comfyui":
            raise NotImplementedError(f"{self.display_name} does not support extension registry versions")
        return {"versions": _dataclass_list(fetch_comfy_registry_versions(node_id, timeout=timeout))}

    def check_environment_dependencies(self, webui_path: Path) -> dict[str, Any]:
        """检查环境依赖状态。

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            dict[str, Any]: 环境依赖检查结果。

        Raises:
            TypeError: 检查结果序列化后不是对象时抛出。
            NotImplementedError: 当前 WebUI 类型不支持环境依赖检查。
        """
        if self.webui_type != "comfyui":
            raise NotImplementedError(f"{self.display_name} does not support environment dependency checks")
        result = json_safe(comfyui_base.check_comfyui_custom_node_dependencies(webui_path))
        if not isinstance(result, dict):
            raise TypeError("Expected extension dependency result object")
        return {"dependencies": result}

    def switch_registry_extension_version(self, webui_path: Path, name: str, version: str, use_uv: bool = True) -> dict[str, Any]:
        """切换 Comfy Registry 扩展版本。

        Args:
            webui_path (Path): WebUI 根目录。
            name (str): 扩展名称。
            version (str): 目标版本。
            use_uv (bool): 是否使用 uv 安装依赖。

        Returns:
            dict[str, Any]: 切换结果。

        Raises:
            NotImplementedError: 当前 WebUI 类型不支持 Registry 版本切换。
        """
        if self.webui_type != "comfyui":
            raise NotImplementedError(f"{self.display_name} does not support extension registry versions")
        self.extension_manager(webui_path).switch_registry_extension_version(name, version=version, use_uv=use_uv)
        return {"changed": True}

    def list_package_versions(self, package_name: str, current_version: str | None = None, index_url: str = "https://pypi.org/pypi", timeout: int | None = 20) -> dict[str, Any]:
        """列出 PyPI 包版本。

        Args:
            package_name (str): PyPI 包名。
            current_version (str | None): 当前版本。
            index_url (str): PyPI JSON API 或镜像地址。
            timeout (int | None): 请求超时时间。

        Returns:
            dict[str, Any]: 包版本列表。
        """
        return {"versions": _dataclass_list(fetch_pypi_versions(package_name, current_version=current_version, index_url=index_url, timeout=timeout))}

    def install_invokeai_version(self, version: str | None = None, upgrade: bool = False, use_pypi_mirror: bool = False, use_uv: bool = True) -> dict[str, Any]:
        """安装或升级 InvokeAI 内核版本。

        Args:
            version (str | None): 目标 InvokeAI 版本。
            upgrade (bool): 是否升级到最新版。
            use_pypi_mirror (bool): 是否使用 PyPI 镜像。
            use_uv (bool): 是否使用 uv。

        Returns:
            dict[str, Any]: 安装结果。

        Raises:
            NotImplementedError: 当前 WebUI 类型不支持 PyPI 内核版本安装。
        """
        if self.webui_type != "invokeai":
            raise NotImplementedError(f"{self.display_name} does not support PyPI kernel version installation")
        invokeai_base.install_invokeai_component(invokeai_version=version, upgrade=upgrade, use_pypi_mirror=use_pypi_mirror, use_uv=use_uv)
        return {"installed": True}

    def prepare_launch(
        self,
        webui_path: Path,
        launch_args: list[str] | None = None,
        use_hf_mirror: bool = False,
        custom_hf_mirror: str | None = None,
        use_github_mirror: bool = False,
        custom_github_mirror: str | None = None,
        use_pypi_mirror: bool = False,
        use_cuda_malloc: bool = True,
        enable_hotpatcher: bool = False,
        hotpatcher_config_path: str | None = None,
        hotpatcher_port: int = DEFAULT_RUNTIME_PORT,
        enable_hotpatcher_runtime: bool = False,
    ) -> dict[str, Any]:
        """准备 WebUI 启动参数。

        Args:
            webui_path (Path): WebUI 根目录。
            launch_args (list[str] | None): 额外启动参数。
            use_hf_mirror (bool): 是否使用 Hugging Face 镜像。
            custom_hf_mirror (str | None): 自定义 Hugging Face 镜像。
            use_github_mirror (bool): 是否使用 GitHub 镜像。
            custom_github_mirror (str | None): 自定义 GitHub 镜像。
            use_pypi_mirror (bool): 是否使用 PyPI 镜像。
            use_cuda_malloc (bool): 是否启用 CUDA malloc 优化。
            enable_hotpatcher (bool): 是否启用 Hotpatcher。
            hotpatcher_config_path (str | None): Hotpatcher 配置路径。
            hotpatcher_port (int): Hotpatcher runtime 端口。
            enable_hotpatcher_runtime (bool): 是否启用 Hotpatcher runtime。

        Returns:
            dict[str, Any]: 启动参数信息。

        Raises:
            ValueError: 启动选项格式无效时抛出。
            TypeError: 启动信息序列化结果无效时抛出。
            NotImplementedError: 当前 WebUI 类型不支持启动。
        """
        launch_args = launch_args or []

        if self.webui_type == "sd_webui":
            launch_info = sd_webui_base.prepare_sd_webui_launch(
                webui_path,
                launch_args=launch_args,
                use_hf_mirror=use_hf_mirror,
                custom_hf_mirror=custom_hf_mirror,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
                use_pypi_mirror=use_pypi_mirror,
                use_cuda_malloc=use_cuda_malloc,
                enable_hotpatcher=enable_hotpatcher,
                hotpatcher_config_path=hotpatcher_config_path,
                hotpatcher_port=hotpatcher_port,
                enable_hotpatcher_runtime=enable_hotpatcher_runtime,
            )
        elif self.webui_type == "comfyui":
            launch_info = comfyui_base.prepare_comfyui_launch(
                webui_path,
                launch_args=launch_args,
                use_hf_mirror=use_hf_mirror,
                custom_hf_mirror=custom_hf_mirror,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
                use_pypi_mirror=use_pypi_mirror,
                use_cuda_malloc=use_cuda_malloc,
                enable_hotpatcher=enable_hotpatcher,
                hotpatcher_config_path=hotpatcher_config_path,
                hotpatcher_port=hotpatcher_port,
                enable_hotpatcher_runtime=enable_hotpatcher_runtime,
            )
        elif self.webui_type == "fooocus":
            launch_info = fooocus_base.prepare_fooocus_launch(
                webui_path,
                launch_args=launch_args,
                use_hf_mirror=use_hf_mirror,
                custom_hf_mirror=custom_hf_mirror,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
                use_pypi_mirror=use_pypi_mirror,
                use_cuda_malloc=use_cuda_malloc,
                enable_hotpatcher=enable_hotpatcher,
                hotpatcher_config_path=hotpatcher_config_path,
                hotpatcher_port=hotpatcher_port,
                enable_hotpatcher_runtime=enable_hotpatcher_runtime,
            )
        elif self.webui_type == "invokeai":
            launch_info = invokeai_base.prepare_invokeai_launch(
                webui_path,
                launch_args=launch_args,
                use_hf_mirror=use_hf_mirror,
                custom_hf_mirror=custom_hf_mirror,
                use_pypi_mirror=use_pypi_mirror,
                use_cuda_malloc=use_cuda_malloc,
                enable_hotpatcher=enable_hotpatcher,
                hotpatcher_config_path=hotpatcher_config_path,
                hotpatcher_port=hotpatcher_port,
                enable_hotpatcher_runtime=enable_hotpatcher_runtime,
            )
        elif self.webui_type == "sd_trainer":
            launch_info = sd_trainer_base.prepare_sd_trainer_launch(
                webui_path,
                launch_args=launch_args,
                use_hf_mirror=use_hf_mirror,
                custom_hf_mirror=custom_hf_mirror,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
                use_pypi_mirror=use_pypi_mirror,
                use_cuda_malloc=use_cuda_malloc,
                enable_hotpatcher=enable_hotpatcher,
                hotpatcher_config_path=hotpatcher_config_path,
                hotpatcher_port=hotpatcher_port,
                enable_hotpatcher_runtime=enable_hotpatcher_runtime,
            )
        elif self.webui_type == "qwen_tts_webui":
            launch_info = qwen_tts_webui_base.prepare_qwen_tts_webui_launch(
                webui_path,
                launch_args=launch_args,
                use_hf_mirror=use_hf_mirror,
                custom_hf_mirror=custom_hf_mirror,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
                use_pypi_mirror=use_pypi_mirror,
                use_cuda_malloc=use_cuda_malloc,
                enable_hotpatcher=enable_hotpatcher,
                hotpatcher_config_path=hotpatcher_config_path,
                hotpatcher_port=hotpatcher_port,
                enable_hotpatcher_runtime=enable_hotpatcher_runtime,
            )
        else:
            raise NotImplementedError(f"{self.display_name} does not support launch preparation")
        data = json_safe(asdict(launch_info))
        if not isinstance(data, dict):
            raise TypeError("Expected launch info object")
        return {"launch": data}


WEBUI_API_ADAPTERS: dict[WebUiApiType, WebUiApiAdapter] = {
    "sd_webui": WebUiApiAdapter("sd_webui", "Stable Diffusion WebUI", sd_webui_base.get_sd_webui_snapshot, sd_webui_base.check_sd_webui_updates),
    "comfyui": WebUiApiAdapter("comfyui", "ComfyUI", comfyui_base.get_comfyui_snapshot, comfyui_base.check_comfyui_updates),
    "fooocus": WebUiApiAdapter("fooocus", "Fooocus", fooocus_base.get_fooocus_snapshot, fooocus_base.check_fooocus_updates),
    "invokeai": WebUiApiAdapter("invokeai", "InvokeAI", invokeai_base.get_invokeai_snapshot, invokeai_base.check_invokeai_updates),
    "sd_trainer": WebUiApiAdapter("sd_trainer", "SD Trainer", sd_trainer_base.get_sd_trainer_snapshot, sd_trainer_base.check_sd_trainer_updates),
    "sd_scripts": WebUiApiAdapter("sd_scripts", "SD Scripts", sd_scripts_base.get_sd_scripts_snapshot, sd_scripts_base.check_sd_scripts_updates),
    "qwen_tts_webui": WebUiApiAdapter("qwen_tts_webui", "Qwen TTS WebUI", qwen_tts_webui_base.get_qwen_tts_webui_snapshot, qwen_tts_webui_base.check_qwen_tts_webui_updates),
}
