"""Implementation grouped from the former ``model_manager.py`` module."""

from __future__ import annotations

from pathlib import Path

from sd_webui_all_in_one.base_manager.model_manager.models import WEBUI_MODEL_TITLES, WebUiModelType, logger


def launch_model_manager_gui(
    webui_type: WebUiModelType,
    webui_path: Path,
    title: str | None = None,
) -> None:
    """启动模型管理 GUI

    Args:
        webui_type (WebUiModelType):
            要管理模型的 WebUI 类型。
        webui_path (Path):
            WebUI 根目录路径。
        title (str | None):
            可选的窗口标题。

    Raises:
        RuntimeError:
            tkinter 不可用或 GUI 模块导入失败时抛出。
    """
    try:
        from sd_webui_all_in_one.base_manager.gui.model_manager_gui import launch_model_manager_gui as _launch_model_manager_gui
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            logger.error("当前 Python 环境未安装 tkinter, 无法启动模型管理 GUI")
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动模型管理 GUI") from e
        logger.error("导入 GUI 管理模块发生错误: %s", e)
        raise RuntimeError(f"导入 GUI 管理模块发生错误: {e}") from e

    logger.info("启动模型管理 GUI: %s, webui_path=%s", webui_type, webui_path)
    _launch_model_manager_gui(
        webui_type=webui_type,
        webui_path=webui_path,
        title=title or WEBUI_MODEL_TITLES[webui_type],
    )
    logger.info("模型管理 GUI 启动完成: %s", webui_type)


def launch_sd_webui_model_manager_gui(sd_webui_path: Path) -> None:
    """启动 Stable Diffusion WebUI 模型管理 GUI

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录路径。
    """
    launch_model_manager_gui("sd_webui", sd_webui_path)


def launch_comfyui_model_manager_gui(comfyui_path: Path) -> None:
    """启动 ComfyUI 模型管理 GUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录路径。
    """
    launch_model_manager_gui("comfyui", comfyui_path)


def launch_fooocus_model_manager_gui(fooocus_path: Path) -> None:
    """启动 Fooocus 模型管理 GUI

    Args:
        fooocus_path (Path):
            Fooocus 根目录路径。
    """
    launch_model_manager_gui("fooocus", fooocus_path)


def launch_sd_trainer_model_manager_gui(sd_trainer_path: Path) -> None:
    """启动 SD Trainer 模型管理 GUI

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录路径。
    """
    launch_model_manager_gui("sd_trainer", sd_trainer_path)


def launch_sd_scripts_model_manager_gui(sd_scripts_path: Path) -> None:
    """启动 SD Scripts 模型管理 GUI

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录路径。
    """
    launch_model_manager_gui("sd_scripts", sd_scripts_path)


def launch_invokeai_model_manager_gui(invokeai_path: Path) -> None:
    """启动 InvokeAI 模型管理 GUI

    Args:
        invokeai_path (Path):
            InvokeAI 根目录路径。
    """
    launch_model_manager_gui("invokeai", invokeai_path)
