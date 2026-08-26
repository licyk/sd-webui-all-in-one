"""Implementation grouped from the former ``extensions.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.base_manager.base import (
    get_repo_name_from_url,
)
from sd_webui_all_in_one.base_manager.version_manager import (
    DEFAULT_EXTENSION_INDEX_URL,
    ExtensionIndexItem,
    fetch_extension_index,
    filter_extension_index,
)

from sd_webui_all_in_one.base_manager.sd_webui_base.extensions.service import install_sd_webui_extension, list_sd_webui_extensions


def fetch_sd_webui_extension_index(
    sd_webui_path: Path,
    query: str = "",
    tags: list[str] | None = None,
    index_url: str | None = None,
    timeout: int | None = 20,
) -> list[ExtensionIndexItem]:
    """获取并过滤 Stable Diffusion WebUI 扩展源列表。

    Args:
        sd_webui_path (Path): Stable Diffusion WebUI 根目录。
        query (str): 搜索关键词。
        tags (list[str] | None): 标签过滤条件。
        index_url (str | None): 扩展源索引 URL。
        timeout (int | None): 请求超时秒数。

    Returns:
        list[ExtensionIndexItem]: 带安装状态的扩展源条目。
    """
    installed_names = {item["name"] for item in list_sd_webui_extensions(sd_webui_path)}
    items = fetch_extension_index(index_url or DEFAULT_EXTENSION_INDEX_URL, timeout=timeout)
    filtered = filter_extension_index(items, keyword=query, tags=tags)
    for item in filtered:
        repo_name = get_repo_name_from_url(item.reference or item.url or item.name)
        item.installed = item.name in installed_names or repo_name in installed_names
    return filtered


def install_sd_webui_extension_index_item(
    sd_webui_path: Path,
    item: ExtensionIndexItem,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> Path:
    """安装 Stable Diffusion WebUI 扩展源条目。

    Args:
        sd_webui_path (Path): Stable Diffusion WebUI 根目录。
        item (ExtensionIndexItem): 扩展源条目。
        use_github_mirror (bool): 是否使用 GitHub 镜像。
        custom_github_mirror (str | list[str] | None): 自定义 GitHub 镜像。

    Returns:
        Path: 扩展安装目录。

    Raises:
        ValueError: 条目不可安装、不是 Git 仓库或缺少仓库地址。
    """
    if not item.installable:
        raise ValueError(f"'{item.name}' is not installable: {item.install_status or 'not installable'}")
    if item.install_type.lower() != "git-clone":
        raise ValueError(f"Unsupported install_type for Stable Diffusion WebUI: {item.install_type}")
    repository = (item.files[0] if item.files else "") or item.reference or item.url
    if not repository:
        raise ValueError(f"'{item.name}' does not provide a repository URL")
    install_sd_webui_extension(
        sd_webui_path=sd_webui_path,
        extension_url=repository,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    return sd_webui_path / "extensions" / get_repo_name_from_url(repository)
