"""模型管理 API adapter。"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from collections.abc import Iterable
from typing import Any, cast

from sd_webui_all_in_one.base_manager.model_manager import (
    FILE_MODEL_ROOT_DIRS,
    FileModelManager,
    FileWebUiModelType,
    InvokeAIModelManager,
)
from sd_webui_all_in_one.base_manager.snapshot import json_safe
from sd_webui_all_in_one.downloader import DownloadToolType


def _json_dict(value: object) -> dict[str, Any]:
    data = json_safe(value)
    if not isinstance(data, dict):
        raise TypeError(f"Expected JSON object, got {type(data).__name__}")
    return data


def _json_list(values: Iterable[Any]) -> list[Any]:
    data = json_safe(values)
    if not isinstance(data, list):
        raise TypeError(f"Expected JSON list, got {type(data).__name__}")
    return data


def _path_result(path: Path) -> dict[str, Any]:
    return {"path": path.as_posix()}


class ModelApiAdapter:
    """模型管理 API adapter。"""

    def file_manager(self, webui_type: str, webui_path: Path) -> FileModelManager:
        """获取文件型模型管理器。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。

        Returns:
            FileModelManager: 文件型模型管理器。

        Raises:
            NotImplementedError: 当前 WebUI 类型不是文件型模型管理。
        """
        if webui_type not in FILE_MODEL_ROOT_DIRS:
            raise NotImplementedError(f"{webui_type} does not support file model management")
        return FileModelManager(webui_type=cast(FileWebUiModelType, webui_type), webui_path=webui_path)

    def invokeai_manager(self, webui_path: Path) -> InvokeAIModelManager:
        """获取 InvokeAI 模型管理器。

        Args:
            webui_path (Path): InvokeAI 根目录。

        Returns:
            InvokeAIModelManager: InvokeAI 模型管理器。
        """
        return InvokeAIModelManager(invokeai_path=webui_path)

    def root(self, webui_type: str, webui_path: Path) -> dict[str, Any]:
        """读取模型根目录信息。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。

        Returns:
            dict[str, Any]: 模型根目录信息。
        """
        manager = self.file_manager(webui_type, webui_path)
        return {"root": _json_dict(asdict(manager.root))}

    def list_directories(self, webui_type: str, webui_path: Path) -> dict[str, Any]:
        """列出模型目录。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。

        Returns:
            dict[str, Any]: 模型目录相对路径列表。
        """
        return {"directories": self.file_manager(webui_type, webui_path).list_directories()}

    def list_entries(self, webui_type: str, webui_path: Path, relative_path: str | None = None) -> dict[str, Any]:
        """列出模型目录条目。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。
            relative_path (str | None): 模型目录相对路径。

        Returns:
            dict[str, Any]: 模型目录条目列表。
        """
        entries = [asdict(entry) for entry in self.file_manager(webui_type, webui_path).list_entries(relative_path)]
        return {"entries": _json_list(entries)}

    def create_folder(self, webui_type: str, webui_path: Path, parent: str | None, name: str) -> dict[str, Any]:
        """创建模型文件夹。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。
            parent (str | None): 父级模型目录相对路径。
            name (str): 新文件夹名称。

        Returns:
            dict[str, Any]: 创建结果。
        """
        return _path_result(self.file_manager(webui_type, webui_path).create_folder(parent, name))

    def copy_entry(self, webui_type: str, webui_path: Path, source: str, target_dir: str | None, new_name: str | None = None, overwrite: bool = False) -> dict[str, Any]:
        """复制模型条目。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。
            source (str): 源条目相对路径。
            target_dir (str | None): 目标目录相对路径。
            new_name (str | None): 可选的新名称。
            overwrite (bool): 是否覆盖已存在目标。

        Returns:
            dict[str, Any]: 复制结果。
        """
        return _path_result(self.file_manager(webui_type, webui_path).copy_entry(source, target_dir, new_name=new_name, overwrite=overwrite))

    def move_entry(self, webui_type: str, webui_path: Path, source: str, target_dir: str | None, new_name: str | None = None, overwrite: bool = False) -> dict[str, Any]:
        """移动模型条目。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。
            source (str): 源条目相对路径。
            target_dir (str | None): 目标目录相对路径。
            new_name (str | None): 可选的新名称。
            overwrite (bool): 是否覆盖已存在目标。

        Returns:
            dict[str, Any]: 移动结果。
        """
        return _path_result(self.file_manager(webui_type, webui_path).move_entry(source, target_dir, new_name=new_name, overwrite=overwrite))

    def delete_entry(self, webui_type: str, webui_path: Path, relative_path: str) -> dict[str, Any]:
        """删除模型条目。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。
            relative_path (str): 要删除的条目相对路径。

        Returns:
            dict[str, Any]: 删除结果。
        """
        self.file_manager(webui_type, webui_path).delete_entry(relative_path)
        return {"deleted": True}

    def import_paths(self, webui_type: str, webui_path: Path, source_paths: list[str], target_dir: str | None, overwrite: bool = False) -> dict[str, Any]:
        """导入本地模型文件或文件夹。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。
            source_paths (list[str]): 源文件或文件夹路径列表。
            target_dir (str | None): 目标目录相对路径。
            overwrite (bool): 是否覆盖已存在目标。

        Returns:
            dict[str, Any]: 导入结果。
        """
        paths = self.file_manager(webui_type, webui_path).import_paths([Path(item) for item in source_paths], target_dir, overwrite=overwrite)
        return {"paths": [path.as_posix() for path in paths]}

    def download_url(self, webui_type: str, webui_path: Path, url: str, target_dir: str | None, save_name: str | None = None, downloader: DownloadToolType | None = None) -> dict[str, Any]:
        """下载模型到模型目录。

        Args:
            webui_type (str): WebUI 类型。
            webui_path (Path): WebUI 根目录。
            url (str): 模型下载链接。
            target_dir (str | None): 目标目录相对路径。
            save_name (str | None): 可选保存文件名。
            downloader (DownloadToolType | None): 下载器名称。

        Returns:
            dict[str, Any]: 下载结果。
        """
        return _path_result(self.file_manager(webui_type, webui_path).download_url(url, target_dir, save_name=save_name, downloader=downloader))

    def list_invokeai_models(self, webui_path: Path) -> dict[str, Any]:
        """列出 InvokeAI 已注册模型。

        Args:
            webui_path (Path): InvokeAI 根目录。

        Returns:
            dict[str, Any]: InvokeAI 模型列表。
        """
        return {"models": self.invokeai_manager(webui_path).list_models()}

    def invokeai_install_url(self, webui_path: Path, url: str) -> dict[str, Any]:
        """通过 InvokeAI 从 URL 安装模型。

        Args:
            webui_path (Path): InvokeAI 根目录。
            url (str): 模型 URL 或 InvokeAI 支持的模型源。

        Returns:
            dict[str, Any]: 安装结果。
        """
        return {"installed": self.invokeai_manager(webui_path).install_from_url(url)}

    def invokeai_import_paths(self, webui_path: Path, source_paths: list[str]) -> dict[str, Any]:
        """导入本地模型到 InvokeAI。

        Args:
            webui_path (Path): InvokeAI 根目录。
            source_paths (list[str]): 源文件或文件夹路径列表。

        Returns:
            dict[str, Any]: 导入结果。
        """
        return {"imported": self.invokeai_manager(webui_path).import_local_paths([Path(item) for item in source_paths])}

    def invokeai_unregister(self, webui_path: Path, model_id: str) -> dict[str, Any]:
        """注销或删除 InvokeAI 模型。

        Args:
            webui_path (Path): InvokeAI 根目录。
            model_id (str): InvokeAI 模型 ID。

        Returns:
            dict[str, Any]: 注销结果。
        """
        return {"unregistered": self.invokeai_manager(webui_path).unregister(model_id)}

    def invokeai_delete(self, webui_path: Path, model_id: str) -> dict[str, Any]:
        """删除 InvokeAI 模型。

        Args:
            webui_path (Path): InvokeAI 根目录。
            model_id (str): InvokeAI 模型 ID。

        Returns:
            dict[str, Any]: 删除结果。
        """
        return {"deleted": self.invokeai_manager(webui_path).delete(model_id)}


MODEL_API_ADAPTER = ModelApiAdapter()
