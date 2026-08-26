"""Implementation grouped from the former ``model_manager.py`` module."""

from __future__ import annotations

from pathlib import Path
from sd_webui_all_in_one.file_manager import copy_files

from .models import logger


class InvokeAIModelManager:
    """InvokeAI 专用模型管理器"""

    def __init__(
        self,
        invokeai_path: Path,
    ) -> None:
        self.invokeai_path = Path(invokeai_path)
        logger.debug("初始化 InvokeAIModelManager, invokeai_path=%s", self.invokeai_path)

    @property
    def import_cache_path(self) -> Path:
        """复制导入本地模型时使用的安全暂存目录

        Returns:
            Path:
                InvokeAI 本地导入暂存目录。
        """
        return self.invokeai_path / "models" / "_imports"

    def list_models(self):
        """列出 InvokeAI 已注册模型

        Returns:
            list[dict[str, Any]]:
                InvokeAI 已注册模型信息列表。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import get_invokeai_model_list

        logger.debug("开始获取 InvokeAI 模型列表: %s", self.invokeai_path)
        model_list = get_invokeai_model_list(invokeai_path=self.invokeai_path)
        logger.info("获取 InvokeAI 模型列表完成, 共 %s 个模型", len(model_list))
        return model_list

    def install_from_url(
        self,
        url: str,
    ) -> bool:
        """通过 InvokeAI 模型管理器从 URL 安装模型

        Args:
            url (str):
                模型下载链接或 InvokeAI 支持的模型源。

        Returns:
            bool:
                安装成功时返回 True。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import install_invokeai_model_from_source

        logger.info("开始通过 InvokeAI 安装模型, invokeai_path=%s", self.invokeai_path)
        result = install_invokeai_model_from_source(invokeai_path=self.invokeai_path, source=url)
        logger.info("InvokeAI 模型安装完成, 成功=%s", result)
        return result

    def import_local_paths(
        self,
        source_paths: list[Path],
    ) -> bool:
        """复制本地模型后交给 InvokeAI 注册，保证源文件不被移动

        Args:
            source_paths (list[Path]):
                要导入的本地模型文件或文件夹路径。

        Returns:
            bool:
                InvokeAI 注册成功时返回 True。

        Raises:
            FileNotFoundError:
                任一源路径不存在时抛出。
            FileExistsError:
                导入暂存目录中已有同名目标时抛出。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import import_model_to_invokeai

        self.import_cache_path.mkdir(parents=True, exist_ok=True)
        logger.info("开始导入本地模型到 InvokeAI, 共 %s 个源路径", len(source_paths))
        copied_paths: list[Path] = []
        for source in source_paths:
            source_path = Path(source).expanduser().resolve()
            if not source_path.exists() and not source_path.is_symlink():
                logger.warning("源路径不存在: %s", source_path)
                raise FileNotFoundError(f"源路径不存在: {source_path}")
            target = self.import_cache_path / source_path.name
            if target.exists() or target.is_symlink():
                logger.warning("导入暂存路径已存在: %s", target)
                raise FileExistsError(f"InvokeAI 导入暂存路径已存在: {target}")
            copy_files(source_path, target)
            copied_paths.append(target)
            logger.debug("复制到导入暂存目录: %s -> %s", source_path, target)

        result = import_model_to_invokeai(
            model_list=copied_paths,
            install_model_to_local=False,
            invokeai_path=self.invokeai_path,
        )
        logger.info("InvokeAI 本地模型导入完成, 成功=%s", result)
        return result

    def unregister(
        self,
        model_id: str,
    ) -> bool:
        """注销 InvokeAI 模型记录并保留模型文件

        Args:
            model_id (str):
                InvokeAI 模型 ID。

        Returns:
            bool:
                移除成功时返回 True。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import uninstall_model_from_invokeai

        logger.debug("开始注销 InvokeAI 模型: %s", model_id)
        result = uninstall_model_from_invokeai(
            model_identifiers=[model_id],
            delete_files=False,
            invokeai_path=self.invokeai_path,
        )
        logger.info("InvokeAI 模型注销完成, model_id=%s, 成功=%s", model_id, result)
        return result

    def delete(
        self,
        model_id: str,
    ) -> bool:
        """删除模型记录，并让 InvokeAI 决定是否删除模型文件

        Args:
            model_id (str):
                InvokeAI 模型 ID。

        Returns:
            bool:
                删除成功时返回 True。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import uninstall_model_from_invokeai

        logger.debug("开始删除 InvokeAI 模型: %s", model_id)
        result = uninstall_model_from_invokeai(
            model_identifiers=[model_id],
            delete_files=True,
            invokeai_path=self.invokeai_path,
        )
        logger.info("InvokeAI 模型删除完成, model_id=%s, 成功=%s", model_id, result)
        return result
