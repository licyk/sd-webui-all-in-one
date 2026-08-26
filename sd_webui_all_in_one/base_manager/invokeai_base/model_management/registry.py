"""Implementation grouped from the former ``model_management.py`` module."""

from __future__ import annotations

import os
from typing import (
    Any,
    TypedDict,
)
from pathlib import Path
from ..components import _temporary_invokeai_root
from ..shared import logger


class InvokeAILocalModelInfo(TypedDict, total=False):
    """InvokeAI 本地已安装的模型信息"""

    id: str
    """模型的 ID"""

    name: str
    """模型的名称"""

    type: Any
    """模型的类型"""

    base: Any
    """模型的基底"""

    path: str
    """模型的安装路径"""

    description: str | None
    """模型的描述信息"""


InvokeAILocalModelInfoList = list[InvokeAILocalModelInfo]


def get_invokeai_model_list(
    invokeai_path: Path | None = None,
) -> InvokeAILocalModelInfoList:
    """获取 InvokeAI 中所有已导入的模型列表

    Args:
        invokeai_path (Path | None):
            InvokeAI 根目录, 为 None 时使用当前环境配置

    Returns:
        InvokeAILocalModelInfoList:
            包含模型信息的字典列表
    """
    with _temporary_invokeai_root(invokeai_path):
        return _get_invokeai_model_list()


def _get_invokeai_model_list() -> InvokeAILocalModelInfoList:
    """获取 InvokeAI 中所有已导入的模型列表

    Returns:
        InvokeAILocalModelInfoList:
            包含模型信息的字典列表

    Raises:
        ImportError:
            导入 InvokeAI 相关模块失败时抛出。
    """
    try:
        logger.info("导入 InvokeAI 模块中")
        from invokeai.app.services.model_manager.model_manager_default import ModelManagerService  # ty: ignore[unresolved-import]
        from invokeai.app.services.model_records.model_records_sql import ModelRecordServiceSQL  # ty: ignore[unresolved-import]
        from invokeai.app.services.download.download_default import DownloadQueueService  # ty: ignore[unresolved-import]
        from invokeai.app.services.events.events_base import EventServiceBase  # ty: ignore[unresolved-import]
        from invokeai.app.services.config.config_default import get_config  # ty: ignore[unresolved-import]
        from invokeai.app.services.shared.sqlite.sqlite_util import init_db  # ty: ignore[unresolved-import]
        from invokeai.app.services.image_files.image_files_disk import DiskImageFileStorage  # ty: ignore[unresolved-import]
        from invokeai.app.services.invoker import Invoker  # ty: ignore[unresolved-import]
    except ImportError as e:
        logger.error("导入 InvokeAI 模块失败: %s", e)
        raise ImportError(f"导入 InvokeAI 模块发生错误: {e}") from e

    def _get_invokeai_model_manager() -> ModelManagerService:
        configuration = get_config()
        image_files = DiskImageFileStorage(f"{configuration.outputs_path}/images")
        db = init_db(config=configuration, logger=logger, image_files=image_files)
        events = EventServiceBase()
        return ModelManagerService.build_model_manager(
            app_config=configuration,
            model_record_service=ModelRecordServiceSQL(db=db, logger=logger),
            download_queue=DownloadQueueService(app_config=configuration, event_bus=events),
            events=events,
        )

    try:
        model_manager = _get_invokeai_model_manager()
        model_manager.start(Invoker)

        # 获取所有模型记录
        all_models = model_manager.store.all_models()

        model_list: InvokeAILocalModelInfoList = []
        for m in all_models:
            model_list.append(
                {
                    "id": m.key,
                    "name": m.name,
                    "type": m.type,
                    "base": m.base,
                    "path": m.path,
                    "description": m.description,
                }
            )

        model_manager.stop(Invoker)
        return model_list
    except Exception as e:
        logger.error("获取模型列表失败: %s", e)
        return []


def list_invokeai_models(
    invokeai_path: Path | None = None,
) -> None:
    """列出 InvokeAI 的模型目录

    Args:
        invokeai_path (Path | None):
            InvokeAI 根目录, 为 None 时使用当前环境配置。
    """
    logger.info("InvokeAI 模型列表")
    model_list = get_invokeai_model_list(invokeai_path=invokeai_path)
    for m in model_list:
        print(f"- {m['name']}")
        print(f"模型 ID: {m['id']}")
        print(f"安装路径: {m['path']}")
        print("\n")


def uninstall_model_from_invokeai(
    model_identifiers: list[str | Path],
    delete_files: bool = False,
    invokeai_path: Path | None = None,
) -> bool:
    """从 InvokeAI 中卸载模型

    Args:
        model_identifiers (list[str | Path]):
            模型 ID (Key) 列表或模型物理路径列表
        delete_files (bool):
            是否同时删除磁盘上的模型文件
        invokeai_path (Path | None):
            InvokeAI 根目录, 为 None 时使用当前环境配置

    Returns:
        bool:
            所有模型卸载成功时返回 True
    """
    with _temporary_invokeai_root(invokeai_path):
        return _uninstall_model_from_invokeai(
            model_identifiers=model_identifiers,
            delete_files=delete_files,
        )


def _uninstall_model_from_invokeai(
    model_identifiers: list[str | Path],
    delete_files: bool = False,
) -> bool:
    """从 InvokeAI 中卸载模型

    Args:
        model_identifiers (list[str | Path]):
            模型 ID (Key) 列表或模型物理路径列表
        delete_files (bool):
            是否同时删除磁盘上的模型文件. 注意: 仅当文件位于 InvokeAI 管理的 models 目录下时才会执行物理删除

    Returns:
        bool:
            所有模型卸载成功时返回 True

    Raises:
        ImportError:
            导入 InvokeAI 相关模块失败时抛出。
    """
    try:
        logger.info("导入 InvokeAI 模块中")
        from invokeai.app.services.model_manager.model_manager_default import ModelManagerService  # ty: ignore[unresolved-import]
        from invokeai.app.services.model_records.model_records_sql import ModelRecordServiceSQL  # ty: ignore[unresolved-import]
        from invokeai.app.services.download.download_default import DownloadQueueService  # ty: ignore[unresolved-import]
        from invokeai.app.services.events.events_base import EventServiceBase  # ty: ignore[unresolved-import]
        from invokeai.app.services.config.config_default import get_config  # ty: ignore[unresolved-import]
        from invokeai.app.services.shared.sqlite.sqlite_util import init_db  # ty: ignore[unresolved-import]
        from invokeai.app.services.image_files.image_files_disk import DiskImageFileStorage  # ty: ignore[unresolved-import]
        from invokeai.app.services.invoker import Invoker  # ty: ignore[unresolved-import]
    except ImportError as e:
        logger.error("导入 InvokeAI 模块失败: %s", e)
        raise ImportError(f"导入 InvokeAI 模块发生错误: {e}") from e

    def _get_invokeai_model_manager() -> ModelManagerService:
        configuration = get_config()
        image_files = DiskImageFileStorage(f"{configuration.outputs_path}/images")
        db = init_db(config=configuration, logger=logger, image_files=image_files)
        events = EventServiceBase()
        return ModelManagerService.build_model_manager(
            app_config=configuration,
            model_record_service=ModelRecordServiceSQL(db=db, logger=logger),
            download_queue=DownloadQueueService(app_config=configuration, event_bus=events),
            events=events,
        )

    def _resolve_to_key(model_manager: ModelManagerService, identifier: str | Path) -> str | None:
        """将路径或 ID 统一解析为模型 Key"""
        if isinstance(identifier, Path) or (isinstance(identifier, str) and os.path.exists(identifier)):
            target_path = Path(identifier).resolve()
            for m in model_manager.store.all_models():
                config_path = Path(m.path)
                if not config_path.is_absolute():
                    config_path = Path(get_config().models_path) / config_path
                if config_path.resolve() == target_path:
                    return m.key
            return None
        return str(identifier)  # 假设已经是 Key

    try:
        model_manager = _get_invokeai_model_manager()
        model_manager.start(Invoker)

        results = []
        for identifier in model_identifiers:
            key = _resolve_to_key(model_manager, identifier)
            if not key:
                logger.warning("未找到模型: %s", identifier)
                results.append(False)
                continue

            try:
                if delete_files:
                    # 删除记录并尝试删除物理文件
                    model_manager.install.delete(key)
                else:
                    # 仅注销记录，保留物理文件
                    model_manager.install.unregister(key)
                logger.info("成功卸载模型: %s", identifier)
                results.append(True)
            except Exception as e:
                logger.error("卸载模型 %s 失败: %s", identifier, e)
                results.append(False)

        model_manager.stop(Invoker)
        return all(results) if results else True
    except Exception as e:
        logger.error("卸载服务失败: %s", e)
        return False


def uninstall_invokeai_model(
    model_name: str,
    interactive_mode: bool = False,
    invokeai_path: Path | None = None,
) -> None:
    """卸载 InvokeAI 中的模型

    Args:
        model_name (str):
            模型名称
        interactive_mode (bool):
            是否启用交互模式
        invokeai_path (Path | None):
            InvokeAI 根目录, 为 None 时使用当前环境配置

    Raises:
        FileNotFoundError:
            未找到要删除的模型时
    """

    model_list = get_invokeai_model_list(invokeai_path=invokeai_path)
    delete_list = [x for x in model_list if model_name.lower() in x["name"].lower()]

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

    delete_names = {x["name"].lower() for x in delete_list}
    logger.info("删除模型: %s", ", ".join(x["name"] for x in delete_list))
    uninstall_model_from_invokeai(
        model_identifiers=[x["id"] for x in model_list if x["name"].lower() in delete_names],
        delete_files=True,
        invokeai_path=invokeai_path,
    )

    logger.info("模型删除完成")
