"""Implementation grouped from the former ``extensions.py`` module."""

from __future__ import annotations

import os
from pathlib import Path
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    clone_repo,
    get_repo_name_from_url,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
)
from ..shared import logger

from .local import list_comfyui_custom_nodes


def install_comfyui_custom_node(
    comfyui_path: Path,
    custom_node_url: str | list[str],
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """安装 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        custom_node_url (str | list[str]):
            ComfyUI 扩展下载链接
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            安装 ComfyUI 扩展发生错误时
    """
    urls = [custom_node_url] if isinstance(custom_node_url, str) else custom_node_url

    # 获取已安装扩展列表
    custom_node_list = list_comfyui_custom_nodes(comfyui_path)
    installed_names = {x["name"] for x in custom_node_list}
    err: list[Exception] = []

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    for url in urls:
        custom_node_name = get_repo_name_from_url(url)
        custom_node_path = comfyui_path / "custom_nodes" / custom_node_name
        custom_node_diaabled_path = comfyui_path / "custom_nodes" / f"{custom_node_name}.disabled"

        if custom_node_name in installed_names or custom_node_path.exists() or custom_node_diaabled_path.exists():
            logger.info("'%s' 扩展已安装", custom_node_name)
            continue

        logger.info("安装 '%s' 扩展到 '%s' 中", custom_node_name, custom_node_path)
        try:
            clone_repo(
                repo=url,
                path=custom_node_path,
            )
            logger.info("'%s' 扩展安装成功", custom_node_name)
            installed_names.add(custom_node_name)
        except Exception as e:
            err.append(e)
            logger.error("'%s' 扩展安装失败: %s", custom_node_name, e)

    if err:
        raise AggregateError("安装 ComfyUI 扩展时发生错误", err)

    logger.info("安装 ComfyUI 扩展完成")
