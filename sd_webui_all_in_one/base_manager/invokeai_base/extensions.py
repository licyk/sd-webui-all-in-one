"""Implementation grouped from the former ``invokeai_base.py`` module."""

from __future__ import annotations

import os
from typing import (
    TypedDict,
)
from pathlib import Path
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    clone_repo,
    get_repo_name_from_url,
)
from sd_webui_all_in_one.base_manager.repository_inspector import inspect_repository
from sd_webui_all_in_one.base_manager.version_manager import (
    ExtensionIndexItem,
)
from sd_webui_all_in_one.custom_exceptions import (
    AggregateError,
)
from sd_webui_all_in_one.file_manager import (
    move_files,
    remove_files,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
)

from sd_webui_all_in_one.base_manager.invokeai_base.shared import logger


def install_invokeai_custom_nodes(
    invokeai_path: Path,
    custom_node_url: str | list[str],
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """安装 InvokeAI 扩展

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        custom_node_url (str | list[str]):
            InvokeAI 扩展下载链接
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            安装 InvokeAI 扩展发生错误时
    """
    urls = [custom_node_url] if isinstance(custom_node_url, str) else custom_node_url

    # 获取已安装扩展列表
    custom_node_list = list_invokeai_custom_nodes(invokeai_path)
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
        custom_node_path = invokeai_path / "nodes" / custom_node_name

        if custom_node_name in installed_names or custom_node_path.exists():
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
        raise AggregateError("安装 InvokeAI 扩展时发生错误", err)

    logger.info("安装 InvokeAI 扩展完成")


def install_invokeai_extension_index_item(
    invokeai_path: Path,
    item: ExtensionIndexItem,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> Path:
    """安装 InvokeAI 扩展源条目。

    Args:
        invokeai_path (Path): InvokeAI 根目录。
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
        raise ValueError(f"Unsupported install_type for InvokeAI: {item.install_type}")
    repository = (item.files[0] if item.files else "") or item.reference or item.url
    if not repository:
        raise ValueError(f"'{item.name}' does not provide a repository URL")
    install_invokeai_custom_nodes(
        invokeai_path=invokeai_path,
        custom_node_url=repository,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
    return invokeai_path / "nodes" / get_repo_name_from_url(repository)


def set_invokeai_custom_nodes_status(
    invokeai_path: Path,
    custom_node_name: str,
    status: bool,
) -> None:
    """设置 InvokeAI 启用状态

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        custom_node_name (str):
            InvokeAI 扩展名称
        status (bool):
            设置扩展的启用状态
            - `True`: 启用
            - `False`: 禁用

    Raises:
        FileNotFoundError:
            InvokeAI 扩展未找到时
    """

    custom_node_path = invokeai_path / "nodes"
    custom_nodes_list = [ext.name for ext in custom_node_path.iterdir() if ext.is_dir()]

    if custom_node_name not in custom_nodes_list:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未找到, 请检查该扩展是否已安装")

    init_py = custom_node_path / custom_node_name / "__init__.py"
    init_bak_py = custom_node_path / custom_node_name / "__init__.py.bak"
    if status:
        if init_bak_py.is_file() and not init_py.is_file():
            move_files(init_bak_py, init_py)
        logger.info("启用 '%s' 扩展成功", custom_node_name)
    else:
        if init_py.is_file():
            move_files(init_py, init_bak_py)
        logger.info("禁用 '%s' 扩展成功", custom_node_name)


class InvokeAILocalExtensionInfo(TypedDict, total=False):
    """InvokeAI 本地扩展信息"""

    name: str
    """InvokeAI 扩展名称"""

    status: bool
    """当前 InvokeAI 扩展是否已经启用"""

    path: Path
    """InvokeAI 本地路径"""

    url: str | None
    """InvokeAI 扩展远程地址"""

    commit: str | None
    """InvokeAI 扩展的提交信息"""

    branch: str | None
    """InvokeAI 扩展的当前分支"""


InvokeAILocalExtensionInfoList = list[InvokeAILocalExtensionInfo]


def list_invokeai_custom_nodes(
    invokeai_path: Path,
) -> InvokeAILocalExtensionInfoList:
    """获取 InvokeAI 本地扩展列表

    Args:
        invokeai_path (Path):
            InvokeAI 根目录

    Returns:
        InvokeAILocalExtensionInfoList:
            InvokeAI 本地扩展列表
    """
    custom_node_path = invokeai_path / "nodes"
    info_list: InvokeAILocalExtensionInfoList = []

    for ext in custom_node_path.iterdir():
        info: InvokeAILocalExtensionInfo = {}
        if ext.is_file():
            continue

        name = ext.name
        path = ext
        status = (path / "__init__.py").is_file()
        repo_state = inspect_repository(ext)

        info["name"] = name
        info["status"] = status
        info["path"] = path
        info["url"] = repo_state.url
        info["commit"] = repo_state.commit
        info["branch"] = repo_state.branch
        info_list.append(info)

    return info_list


def update_invokeai_custom_nodes(
    invokeai_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 InvokeAI 扩展

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            检查 InvokeAI 环境发生错误时
    """
    custom_nodes_path = invokeai_path / "nodes"
    err: list[Exception] = []

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    for ext in custom_nodes_path.iterdir():
        if ext.is_file():
            continue

        logger.info("更新 '%s' 扩展中", ext.name)
        try:
            git_warpper.update(ext)
        except Exception as e:
            err.append(e)
            logger.error("更新 '%s' 扩展时发生错误: %s", ext.name, e)

    if err:
        raise AggregateError("更新 InvokeAI 扩展时发生错误", err)

    logger.info("更新 InvokeAI 扩展完成")


def uninstall_invokeai_custom_node(
    invokeai_path: Path,
    custom_node_name: str,
) -> None:
    """卸载 InvokeAI 扩展

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
        custom_node_name (str):
            InvokeAI 扩展名称

    Raises:
        FileNotFoundError:
            要卸载的扩展未找到时
        RuntimeError:
            卸载扩展发生错误时
    """
    custom_nodes_path = invokeai_path / "nodes"
    custom_nodes_list = [ext.name for ext in custom_nodes_path.iterdir() if ext.is_dir()]
    if custom_node_name not in custom_nodes_list:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未安装")

    try:
        logger.info("卸载 '%s' 扩展中", custom_node_name)
        remove_files(custom_nodes_path / custom_node_name)
        logger.info("卸载 '%s' 扩展完成", custom_node_name)
    except Exception as e:
        logger.info("卸载 '%s' 扩展时发生错误: %s", custom_node_name, e)
        raise RuntimeError(f"卸载 '{custom_node_name}' 扩展时发生错误:{e}") from e
