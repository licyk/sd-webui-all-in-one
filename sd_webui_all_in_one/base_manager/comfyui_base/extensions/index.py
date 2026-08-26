"""Implementation grouped from the former ``extensions.py`` module."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from sd_webui_all_in_one.base_manager.base import (
    get_repo_name_from_url,
)
from sd_webui_all_in_one.base_manager.comfy_registry import (
    fetch_comfy_registry_extension_index,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    ExtensionIndexItem,
    fetch_comfyui_custom_node_index,
    filter_extension_index,
)
from sd_webui_all_in_one.downloader import (
    download_archive_and_unpack,
    download_file,
)

from .catalog import COMFYUI_CUSTOM_NODE_INDEX_URL
from .local import list_comfyui_custom_nodes
from .manager import ComfyUiExtensionManager


def _download_name_from_url(url: str) -> str:
    filename = Path(urlparse(url).path).name
    return filename or get_repo_name_from_url(url)


def fetch_comfyui_extension_index(
    comfyui_path: Path,
    query: str = "",
    tags: list[str] | None = None,
    index_url: str | None = None,
    timeout: int | None = 20,
    registry_search: str | None = None,
    registry_limit: int | None = None,
    registry_page_size: int = 500,
    force_refresh: bool = False,
) -> list[ExtensionIndexItem]:
    """获取并过滤 ComfyUI-Manager 与 Comfy Registry 扩展源。

    Args:
        comfyui_path (Path): ComfyUI 根目录。
        query (str): 本地搜索关键词。
        tags (list[str] | None): 本地标签过滤条件。
        index_url (str | None): ComfyUI-Manager 索引地址。
        timeout (int | None): Manager 索引请求超时秒数。
        registry_search (str | None): Registry 服务端搜索词。
        registry_limit (int | None): Registry 最大结果数。
        registry_page_size (int): Registry 单页数量。
        force_refresh (bool): 是否强制刷新 Registry 缓存。

    Returns:
        list[ExtensionIndexItem]: 带安装状态的扩展源条目。
    """
    installed = list_comfyui_custom_nodes(comfyui_path, include_files=True)
    installed_names = {item["name"] for item in installed}
    installed_registry_ids = {item["registry_id"] for item in installed if item.get("registry_id")}
    manager_items = fetch_comfyui_custom_node_index(index_url or COMFYUI_CUSTOM_NODE_INDEX_URL, timeout=timeout)
    registry_items = fetch_comfy_registry_extension_index(
        search=registry_search,
        limit=registry_limit,
        page_size=registry_page_size,
        force_refresh=force_refresh,
    )
    filtered = filter_extension_index([*manager_items, *registry_items], keyword=query, tags=tags)
    for item in filtered:
        repo_name = get_repo_name_from_url(item.reference or item.url or item.name)
        item.installed = item.name in installed_names or item.registry_id in installed_registry_ids or repo_name in installed_names
    return filtered


def install_comfyui_extension_index_item(
    comfyui_path: Path,
    item: ExtensionIndexItem,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> Path:
    """安装 ComfyUI-Manager 或 Comfy Registry 扩展源条目。

    Args:
        comfyui_path (Path): ComfyUI 根目录。
        item (ExtensionIndexItem): 扩展源条目。
        use_github_mirror (bool): 是否使用 GitHub 镜像。
        custom_github_mirror (str | list[str] | None): 自定义 GitHub 镜像。

    Returns:
        Path: 扩展安装位置。

    Raises:
        ValueError: 条目不可安装、缺少下载地址或安装类型不受支持。
    """
    if not item.installable:
        raise ValueError(f"'{item.name}' is not installable: {item.install_status or 'not installable'}")

    install_type = item.install_type.lower()
    manager = ComfyUiExtensionManager(comfyui_path, include_files=True)
    if item.source_type == "comfy-registry" or install_type == "comfy-registry":
        return manager.install_registry_extension(item.registry_id or item.name, version=item.registry_version or None)

    if install_type == "git-clone":
        repository = (item.files[0] if item.files else "") or item.reference or item.url
        if not repository:
            raise ValueError(f"'{item.name}' does not provide a repository URL")
        return manager.install_extension(
            repository,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )

    custom_nodes_path = comfyui_path / "custom_nodes"
    custom_nodes_path.mkdir(parents=True, exist_ok=True)
    files = item.files or ((item.url,) if item.url else ())
    if not files:
        raise ValueError(f"'{item.name}' does not provide download files")
    if install_type == "copy":
        for url in files:
            download_file(url=url, path=custom_nodes_path, save_name=_download_name_from_url(url), progress=False)
        return custom_nodes_path
    if install_type in {"unzip", "zip"}:
        target_name = get_repo_name_from_url(item.reference or item.url or item.name).removesuffix(".zip")
        target_path = custom_nodes_path / target_name
        for url in files:
            download_archive_and_unpack(url=url, local_dir=target_path, name=_download_name_from_url(url))
        return target_path
    raise ValueError(f"Unsupported install_type: {item.install_type}")


def switch_comfyui_registry_extension_version(
    comfyui_path: Path,
    name: str,
    version: str,
    use_uv: bool = True,
) -> None:
    """切换已安装 Comfy Registry 节点的版本。

    Args:
        comfyui_path (Path): ComfyUI 根目录。
        name (str): 已安装节点名称。
        version (str): 目标版本。
        use_uv (bool): 是否使用 uv 安装依赖。
    """
    ComfyUiExtensionManager(comfyui_path, include_files=True).switch_registry_extension_version(name, version, use_uv=use_uv)
