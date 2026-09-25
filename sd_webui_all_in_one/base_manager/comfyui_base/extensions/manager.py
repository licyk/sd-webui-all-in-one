"""Implementation grouped from the former ``extensions.py`` module."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    DEFAULT_GIT_UPDATE_WORKERS,
    MIRROR_GIT_UPDATE_WORKERS,
    get_repo_name_from_url,
    update_git_repositories,
)
from sd_webui_all_in_one.base_manager.comfy_registry import (
    fetch_comfy_registry_install_info,
    switch_comfy_registry_node_version,
    install_comfy_registry_node,
    update_comfy_registry_nodes,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    ExtensionUpdateStatus,
    ManagedExtension,
    check_extension_updates,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError

from sd_webui_all_in_one.base_manager.comfyui_base.extensions.install import install_comfyui_custom_node
from sd_webui_all_in_one.base_manager.comfyui_base.extensions.local import (
    _normalize_custom_node_name,
    list_comfyui_custom_nodes,
    resolve_comfyui_custom_node_path,
    set_comfyui_custom_node_status,
    uninstall_comfyui_custom_node,
)


class ComfyUiExtensionManager:
    """ComfyUI 专属扩展管理器，支持 Git 和 Comfy Registry 节点。"""

    def __init__(self, comfyui_path: Path, include_files: bool = True, use_github_mirror: bool = False) -> None:
        self.root_path = Path(comfyui_path)
        self.extension_path = self.root_path / "custom_nodes"
        self.include_files = include_files
        self.use_github_mirror = use_github_mirror
        """是否正在使用 GitHub 镜像源, 用于选择较低的并行线程数以避免镜像源限流"""

    def list_extensions(self) -> list[ManagedExtension]:
        """获取本地 ComfyUI 自定义节点列表。

        Returns:
            list[ManagedExtension]:
                本地自定义节点列表。
        """
        result: list[ManagedExtension] = []
        for info in list_comfyui_custom_nodes(self.root_path, include_files=self.include_files):
            path = info["path"]
            if path.is_file() and not self.include_files:
                continue
            source_type = info.get("source_type") or "unknown"
            result.append(
                ManagedExtension(
                    name=info["name"],
                    path=path,
                    enabled=bool(info["status"]),
                    is_git_repo=source_type == "git",
                    url=info.get("url") or info.get("repository"),
                    branch=info.get("branch"),
                    commit=info.get("commit"),
                    error=info.get("error"),
                    source_type="comfy-registry" if source_type == "comfy-registry" else ("git" if source_type == "git" else ("file" if source_type == "file" else "unknown")),
                    registry_id=info.get("registry_id"),
                    registry_version=info.get("registry_version"),
                    repository=info.get("repository"),
                )
            )
        return result

    def set_extension_enabled(self, name: str, enabled: bool) -> None:
        """设置自定义节点启用状态。

        Args:
            name (str):
                自定义节点名称。
            enabled (bool):
                是否启用。
        """
        set_comfyui_custom_node_status(self.root_path, name, enabled)

    def install_extension(
        self,
        url: str,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> Path:
        """从 Git URL 安装自定义节点。

        Args:
            url (str):
                Git 仓库地址。
            use_github_mirror (bool):
                是否启用 GitHub 镜像。
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像。

        Returns:
            Path:
                自定义节点安装路径。
        """
        install_comfyui_custom_node(
            comfyui_path=self.root_path,
            custom_node_url=url,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )
        return self.extension_path / get_repo_name_from_url(url)

    def install_registry_extension(self, node_id: str, version: str | None = None, use_uv: bool = True) -> Path:
        """从 Comfy Registry 安装自定义节点。

        Args:
            node_id (str):
                Comfy Registry 节点 ID。
            version (str | None):
                指定安装版本。
            use_uv (bool):
                是否使用 uv 安装依赖。

        Returns:
            Path:
                自定义节点安装路径。
        """
        install_comfy_registry_node(self.root_path, node_id=node_id, version=version, use_uv=use_uv)
        return self.extension_path / node_id

    def update_extension(self, name: str) -> None:
        """更新自定义节点。

        Args:
            name (str):
                自定义节点名称。

        Raises:
            FileNotFoundError:
                节点未安装时抛出。
            ValueError:
                节点不是可更新来源时抛出。
        """
        ext = next((item for item in self.list_extensions() if item.name == name), None)
        if ext is None:
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        self._update_extension(ext)

    def _update_extension(self, ext: ManagedExtension) -> None:
        """根据已解析的扩展信息更新自定义节点。

        Args:
            ext (ManagedExtension):
                已解析的自定义节点信息。

        Raises:
            ValueError:
                节点不是可更新来源时抛出。
        """
        if ext.source_type == "comfy-registry":
            node_id = ext.registry_id or _normalize_custom_node_name(ext.name)
            switch_comfy_registry_node_version(self.root_path, node_id=node_id, version=None, target_path=ext.path)
            return
        if not ext.is_git_repo:
            raise ValueError(f"'{ext.name}' 不是 Git 仓库或 Comfy Registry 节点，无法更新")
        git_warpper.update(ext.path)

    def update_extensions(self, names: Iterable[str], fetch: bool = True) -> list[str]:
        """批量更新指定的自定义节点。

        Git 节点并行拉取更新, Comfy Registry 节点仅在版本变化时重新安装。

        Args:
            names (Iterable[str]):
                自定义节点名称列表。
            fetch (bool):
                Git 节点是否先拉取远程更新; 刚执行过 `check_updates()` 时可关闭以复用已拉取的远程引用。

        Returns:
            list[str]:
                实际发生更新的节点名称列表。

        Raises:
            FileNotFoundError:
                存在未安装的节点时抛出。
            AggregateError:
                一个或多个节点更新失败时抛出。
        """
        wanted = list(dict.fromkeys(names))
        extensions = {ext.name: ext for ext in self.list_extensions()}
        missing = [name for name in wanted if name not in extensions]
        if missing:
            raise FileNotFoundError(f"扩展未安装: {', '.join(missing)}")
        errors: list[Exception] = []
        targets: list[ManagedExtension] = []
        for name in wanted:
            ext = extensions[name]
            if ext.is_git_repo or ext.source_type == "comfy-registry":
                targets.append(ext)
            else:
                errors.append(ValueError(f"'{ext.name}' 不是 Git 仓库或 Comfy Registry 节点，无法更新"))
        return self._update_many(targets, errors, fetch=fetch)

    def _update_many(self, extensions: list[ManagedExtension], errors: list[Exception], fetch: bool = True) -> list[str]:
        """批量更新已解析的自定义节点并汇总结果。

        Args:
            extensions (list[ManagedExtension]):
                已解析的自定义节点列表。
            errors (list[Exception]):
                已收集的错误列表。
            fetch (bool):
                Git 节点是否先拉取远程更新。

        Returns:
            list[str]:
                实际发生更新的节点名称列表。

        Raises:
            AggregateError:
                一个或多个节点更新失败时抛出。
        """
        git_extensions = [ext for ext in extensions if ext.is_git_repo]
        registry_extensions = [ext for ext in extensions if ext.source_type == "comfy-registry"]
        git_results = update_git_repositories([ext.path for ext in git_extensions], use_github_mirror=self.use_github_mirror, fetch=fetch)
        registry_results = update_comfy_registry_nodes([(ext.registry_id or _normalize_custom_node_name(ext.name), ext.path) for ext in registry_extensions])
        updated: list[str] = []
        for ext, result in [*zip(git_extensions, git_results), *zip(registry_extensions, registry_results)]:
            if result.error is not None:
                errors.append(result.error)
            elif result.updated:
                updated.append(ext.name)
        if errors:
            raise AggregateError("更新 ComfyUI 扩展时发生错误", errors)
        return updated

    def update_all(self) -> list[str]:
        """更新所有可更新的自定义节点。

        Returns:
            list[str]:
                实际发生更新的节点名称列表。

        Raises:
            AggregateError:
                一个或多个节点更新失败时抛出。
        """
        return self._update_many([ext for ext in self.list_extensions() if ext.is_git_repo or ext.source_type == "comfy-registry"], [])

    def check_updates(self, fetch: bool = True) -> list[ExtensionUpdateStatus]:
        """并行检查所有自定义节点的更新状态。

        Args:
            fetch (bool):
                是否先拉取 Git 远程引用。

        Returns:
            list[ExtensionUpdateStatus]:
                与节点列表顺序一致的更新状态。
        """

        def resolve_registry_version(extension: ManagedExtension) -> str | None:
            node_id = extension.registry_id or _normalize_custom_node_name(extension.name)
            return fetch_comfy_registry_install_info(node_id).version or None

        workers = MIRROR_GIT_UPDATE_WORKERS if self.use_github_mirror else DEFAULT_GIT_UPDATE_WORKERS
        return check_extension_updates(self.list_extensions(), fetch=fetch, registry_version_resolver=resolve_registry_version, max_workers=workers)

    def uninstall_extension(self, name: str) -> None:
        """卸载自定义节点。

        Args:
            name (str):
                自定义节点名称。
        """
        uninstall_comfyui_custom_node(self.root_path, name)

    def switch_extension_commit(self, name: str, commit: str) -> None:
        """切换 Git 自定义节点到指定提交。

        Args:
            name (str):
                自定义节点名称。
            commit (str):
                目标提交 ID。

        Raises:
            FileNotFoundError:
                节点未安装时抛出。
        """
        resolved = resolve_comfyui_custom_node_path(self.root_path, name)
        if resolved is None:
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        git_warpper.switch_commit(path=resolved[0], commit=commit)

    def switch_extension_branch(self, name: str, branch: str) -> None:
        """切换 Git 自定义节点分支。

        Args:
            name (str):
                自定义节点名称。
            branch (str):
                目标分支。

        Raises:
            FileNotFoundError:
                节点未安装时抛出。
        """
        resolved = resolve_comfyui_custom_node_path(self.root_path, name)
        if resolved is None:
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        git_warpper.switch_branch(path=resolved[0], branch=branch)

    def switch_registry_extension_version(self, name: str, version: str, use_uv: bool = True) -> None:
        """切换 Comfy Registry 自定义节点版本。

        Args:
            name (str):
                自定义节点名称。
            version (str):
                目标 Registry 版本。
            use_uv (bool):
                是否使用 uv 安装依赖。

        Raises:
            FileNotFoundError:
                节点未安装时抛出。
            ValueError:
                节点不是 Comfy Registry 来源时抛出。
        """
        ext = next((item for item in self.list_extensions() if item.name == name), None)
        if ext is None:
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        if ext.source_type != "comfy-registry":
            raise ValueError(f"'{name}' 不是 Comfy Registry 节点")
        node_id = ext.registry_id or _normalize_custom_node_name(ext.name)
        switch_comfy_registry_node_version(self.root_path, node_id=node_id, version=version, target_path=ext.path, use_uv=use_uv)
