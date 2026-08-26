"""Implementation grouped from the former ``comfyui_base.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.base_manager.base import (
    install_webui_model_from_library,
)
from sd_webui_all_in_one.downloader import (
    DownloadToolType,
    download_file,
)
from sd_webui_all_in_one.file_manager import (
    generate_dir_tree,
    get_file_list,
    remove_files,
)
from sd_webui_all_in_one.model_downloader import ModelDownloadUrlType

from sd_webui_all_in_one.base_manager.comfyui_base.shared import logger


def install_comfyui_model_from_library(
    comfyui_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """为 ComfyUI 下载模型, 使用模型库进行下载

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        download_resource_type (ModelDownloadUrlType | None):
            模型下载源类型
        model_name (str | None):
            下载的模型名称
        model_index (int | None):
            下载的模型在列表中的索引值, 索引值从 1 开始. 当同时提供 `model_name` 和 `model_index` 时, 优先使用 `model_index` 查找模型
        downloader (DownloadToolType | None):
            下载模型使用的工具
        interactive_mode (bool):
            是否启用交互模式
        list_only (bool):
            是否仅列出模型列表并退出
    """
    install_webui_model_from_library(
        webui_path=comfyui_path,
        dtype="comfyui",
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )


def install_comfyui_model_from_url(
    comfyui_path: Path,
    model_url: str,
    model_type: str,
    downloader: DownloadToolType | None = None,
) -> None:
    """从链接下载模型到 ComfyUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        model_url (str):
            模型下载地址
        model_type (str):
            模型的类型
        downloader (DownloadToolType | None):
            下载模型使用的工具
    """
    model_path = comfyui_path / "models" / model_type
    download_file(
        url=model_url,
        path=model_path,
        tool=downloader,
    )


def list_comfyui_models(
    comfyui_path: Path,
) -> None:
    """列出 ComfyUI 的模型目录

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
    """
    models_path = comfyui_path / "models"
    logger.info("ComfyUI 模型列表")
    for m in models_path.iterdir():
        logger.info("%s 的模型列表", m.name)
        generate_dir_tree(m)
        print("\n\n")


def uninstall_comfyui_model(
    comfyui_path: Path,
    model_name: str,
    model_type: str | None = None,
    interactive_mode: bool = False,
) -> None:
    """卸载 ComfyUI 中的模型

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        model_name (str):
            模型名称
        model_type (str | None):
            模型的类型
        interactive_mode (bool):
            是否启用交互模式

    Raises:
        FileNotFoundError:
            未找到要删除的模型时
    """
    if model_type is None:
        model_path = comfyui_path / "models"
    else:
        model_path = comfyui_path / "models" / model_type

    model_list = get_file_list(model_path)
    delete_list = [x for x in model_list if model_name.lower() in x.name.lower()]

    if not delete_list:
        raise FileNotFoundError(f"模型 '{model_name}' 不存在")

    logger.info("根据 '%s' 模型名找到的已有模型列表:\n", model_name)
    for d in delete_list:
        print(f"- `{d}`")

    print()
    if interactive_mode:
        logger.info("是否删除以上模型?")
        if input("[y/N]").strip().lower() not in ["yes", "y"]:
            logger.info("取消模型删除操作")
            return

    for i in delete_list:
        logger.info("删除模型: %s", i)
        remove_files(i)

    logger.info("模型删除完成")
