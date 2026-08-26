"""Implementation grouped from the former ``extensions.py`` module."""

from __future__ import annotations

import os
import json
import uuid
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from typing import (
    Any,
    TypedDict,
)
from pathlib import Path
from sd_webui_all_in_one.base_manager.base import (
    apply_github_raw_file_mirror,
    apply_git_base_config_and_github_mirror,
    apply_git_config_global_to_process,
    clone_repo,
    get_repo_name_from_url,
)
from sd_webui_all_in_one.base_manager.repository_inspector import inspect_repository
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.file_manager import (
    move_files,
    remove_files,
)
from sd_webui_all_in_one.base_manager.sd_webui_base.shared import logger


def set_sd_webui_extension_download_list_mirror(
    custom_github_mirror: str | list[str] | None = None,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """配置 Stable Diffusion WebUI 扩展下载列表镜像源

    Args:
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源列表
        origin_env (dict[str, str] | None):
            原始的环境变量字典

    Returns:
        dict[str, str]:
            包含 `WEBUI_EXTENSIONS_INDEX` 的环境变量字典
    """
    env = origin_env.copy() if origin_env is not None else os.environ.copy()
    extension_index = apply_github_raw_file_mirror(
        raw_file_path="AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json",
        custom_github_mirror=custom_github_mirror,
    )
    if extension_index is not None:
        env["WEBUI_EXTENSIONS_INDEX"] = extension_index
    return env


def install_sd_webui_extension(
    sd_webui_path: Path,
    extension_url: str | list[str],
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """安装 Stable Diffusion WebUI 扩展

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        extension_url (str | list[str]):
            Stable Diffusion WebUI 扩展下载链接
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            安装 Stable Diffusion WebUI 扩展发生错误时
    """
    urls = [extension_url] if isinstance(extension_url, str) else extension_url

    # 获取已安装扩展列表
    extension_list = list_sd_webui_extensions(sd_webui_path)
    installed_names = {x["name"] for x in extension_list}
    err: list[Exception] = []

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    for url in urls:
        extension_name = get_repo_name_from_url(url)
        extension_path = sd_webui_path / "extensions" / extension_name

        if extension_name in installed_names or extension_path.exists():
            logger.info("'%s' 扩展已安装", extension_name)
            continue

        logger.info("安装 '%s' 扩展到 '%s' 中", extension_name, extension_path)
        try:
            clone_repo(
                repo=url,
                path=extension_path,
            )
            logger.info("'%s' 扩展安装成功", extension_name)
            installed_names.add(extension_name)
        except Exception as e:
            err.append(e)
            logger.error("'%s' 扩展安装失败: %s", extension_name, e)

    if err:
        raise AggregateError("安装 Stable Diffusion WebUI 扩展时发生错误", err)

    logger.info("安装 Stable Diffusion WebUI 扩展完成")


class SDWebUiLocalExtensionInfo(TypedDict, total=False):
    """Stable Diffusion WebUI 本地扩展信息"""

    name: str
    """Stable Diffusion WebUI 扩展名称"""

    status: bool
    """当前 Stable Diffusion WebUI 扩展是否已经启用"""

    path: Path
    """Stable Diffusion WebUI 本地路径"""

    url: str | None
    """Stable Diffusion WebUI 扩展远程地址"""

    commit: str | None
    """Stable Diffusion WebUI 扩展的提交信息"""

    branch: str | None
    """Stable Diffusion WebUI 扩展的当前分支"""


SDWebUiLocalExtensionInfoList = list[SDWebUiLocalExtensionInfo]


def set_sd_webui_extensions_status(
    sd_webui_path: Path,
    extension_name: str,
    status: bool,
) -> None:
    """设置 Stable Diffusion WebUI 启用状态

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        extension_name (str):
            Stable Diffusion WebUI 扩展名称
        status (bool):
            设置扩展的启用状态
            - `True`: 启用
            - `False`: 禁用

    Raises:
        FileNotFoundError:
            Stable Diffusion WebUI 扩展未找到时
    """

    def _save(
        data: dict[str, Any],
    ) -> None:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    config_path = sd_webui_path / "config.json"
    extension_path = sd_webui_path / "extensions"
    extension_list = [ext.name for ext in extension_path.iterdir() if ext.is_dir()]
    settings: dict[str, Any] = {}

    if extension_name not in extension_list:
        raise FileNotFoundError(f"'{extension_name}' 扩展未找到, 请检查该扩展是否已安装")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        logger.error("加载 '%s' 配置文件发生错误: %s", config_path, e)
        logger.warning("尝试重置 Stable Diffusion WebUI 配置文件")
        move_files(config_path, config_path.with_name(f"config_{uuid.uuid4()}.json"))

    disabled_extensions = settings.get("disabled_extensions")
    if not isinstance(disabled_extensions, list):
        disabled_extensions = []
        settings["disabled_extensions"] = disabled_extensions

    if status:
        if extension_name in disabled_extensions:
            disabled_extensions.remove(extension_name)
            _save(settings)
        logger.info("启用 '%s' 扩展成功", extension_name)
    else:
        if extension_name not in disabled_extensions:
            disabled_extensions.append(extension_name)
            _save(settings)
        logger.info("禁用 '%s' 扩展成功", extension_name)


def list_sd_webui_extensions(
    sd_webui_path: Path,
) -> SDWebUiLocalExtensionInfoList:
    """获取 Stable Diffusion WebUI 本地扩展列表

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录

    Returns:
        SDWebUiLocalExtensionInfoList:
            Stable Diffusion WebUI 本地扩展列表
    """
    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    config_path = sd_webui_path / "config.json"
    extension_path = sd_webui_path / "extensions"
    info_list: SDWebUiLocalExtensionInfoList = []

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
    except Exception as e:
        logger.debug("加载 '%s' 配置文件发生错误: %s", config_path, e)
        settings = {}

    disabled_extensions = set(settings.get("disabled_extensions", []))
    disable_all_extensions = settings.get("disable_all_extensions", "none")

    if not extension_path.exists():
        return []
    ext_dirs = [ext for ext in extension_path.iterdir() if ext.is_dir() and ext.name != "__pycache__"]

    def _process_single_extension(ext: Path) -> SDWebUiLocalExtensionInfo:
        """内部函数：处理单个插件的信息提取"""
        name = ext.name
        path = ext

        # 计算状态 (Status 逻辑保持原样)
        if disable_all_extensions == "all":
            status = False
        elif disable_all_extensions != "extra":
            status = name not in disabled_extensions
        else:
            status = True

        repo_state = inspect_repository(ext)
        return {
            "name": name,
            "status": status,
            "path": path,
            "url": repo_state.url,
            "commit": repo_state.commit,
            "branch": repo_state.branch,
        }

    logger.info("获取 Stable Diffusion WebUI 扩展列表中")
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_ext = {executor.submit(_process_single_extension, ext): ext for ext in ext_dirs}
        for future in tqdm(as_completed(future_to_ext), total=len(ext_dirs), desc="获取 Stable Diffusion WebUI 扩展数据"):
            try:
                result = future.result(timeout=15)
                if result:
                    info_list.append(result)
            except Exception as e:
                ext_name = future_to_ext[future].name
                logger.error("处理扩展 '%s' 时发生异常: %s", ext_name, e)

    logger.info("获取 Stable Diffusion WebUI 扩展列表中完成")
    return info_list


def update_sd_webui_extensions(
    sd_webui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 Stable Diffusion WebUI 扩展

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            检查 Stable Diffusion WebUI 环境发生错误时
        FileNotFoundError:
            未找到 Stable Diffusion WebUI 扩展目录时
    """
    extension_path = sd_webui_path / "extensions"
    err: list[Exception] = []
    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    apply_git_config_global_to_process(custom_env)

    if not extension_path.is_dir():
        raise FileNotFoundError("未找到 Stable Diffusion WebUI 扩展目录")

    update_targets = [ext for ext in extension_path.iterdir() if ext.is_dir() and (ext / ".git").exists()]
    count = 0
    task_sum = len(update_targets)

    for ext in update_targets:
        count += 1
        logger.info("[%s/%s] 更新 '%s' 扩展中", count, task_sum, ext.name)
        try:
            git_warpper.update(ext)
        except Exception as e:
            err.append(e)
            logger.error("[%s/%s] 更新 '%s' 扩展时发生错误: %s", count, task_sum, ext.name, e)

    if err:
        raise AggregateError("更新 Stable Diffusion WebUI 扩展时发生错误", err)

    logger.info("更新 Stable Diffusion WebUI 扩展完成")


def uninstall_sd_webui_extension(
    sd_webui_path: Path,
    extension_name: str,
) -> None:
    """卸载 Stable Diffusion WebUI 扩展

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        extension_name (str):
            Stable Diffusion WebUI 扩展名称

    Raises:
        FileNotFoundError:
            要卸载的扩展未找到时
        RuntimeError:
            卸载扩展发生错误时
    """
    extension_path = sd_webui_path / "extensions"
    extension_list = [ext.name for ext in extension_path.iterdir() if ext.is_dir()]
    if extension_name not in extension_list:
        raise FileNotFoundError(f"'{extension_name}' 扩展未安装")

    try:
        logger.info("卸载 '%s' 扩展中", extension_name)
        remove_files(extension_path / extension_name)
        logger.info("卸载 '%s' 扩展完成", extension_name)
    except Exception as e:
        logger.info("卸载 '%s' 扩展时发生错误: %s", extension_name, e)
        raise RuntimeError(f"卸载 '{extension_name}' 扩展时发生错误:{e}") from e
