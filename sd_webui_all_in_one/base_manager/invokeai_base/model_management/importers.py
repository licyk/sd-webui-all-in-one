"""Implementation grouped from the former ``model_management.py`` module."""

from __future__ import annotations

import os
from pathlib import Path
from sd_webui_all_in_one.base_manager.base import (
    install_webui_model_from_library,
)
from sd_webui_all_in_one.downloader import (
    DownloadToolType,
    download_file,
)
from sd_webui_all_in_one.model_downloader import ModelDownloadUrlType
from sd_webui_all_in_one.utils import print_divider
from sd_webui_all_in_one.base_manager.invokeai_base.components import _temporary_invokeai_root
from sd_webui_all_in_one.base_manager.invokeai_base.shared import logger


def import_model_to_invokeai(
    model_list: list[Path],
    install_model_to_local: bool = False,
    invokeai_path: Path | None = None,
) -> bool:
    """将模型列表导入到 InvokeAI 中

    Args:
        model_list (list[Path]):
            模型路径列表
        install_model_to_local (bool):
            是否将模型安装到 InvokeAI 路径中, 为 False 时就地安装, 为 True 时则将模型复制到 InvokeAI 目录中
        invokeai_path (Path | None):
            InvokeAI 根目录, 为 None 时使用当前环境配置

    Returns:
        bool:
            导入模型成功时
    """
    with _temporary_invokeai_root(invokeai_path):
        return _import_model_to_invokeai(
            model_list=model_list,
            install_model_to_local=install_model_to_local,
        )


def _import_model_to_invokeai(
    model_list: list[Path],
    install_model_to_local: bool = False,
) -> bool:
    """将模型列表导入到 InvokeAI 中

    Args:
        model_list (list[Path]):
            模型路径列表
        install_model_to_local (bool):
            是否将模型安装到 InvokeAI 路径中, 为 False 时就地安装, 为 True 时则将模型复制到 InvokeAI 目录中

    Returns:
        bool:
            导入模型成功时

    Raises:
        ImportError:
            导入 InvokeAI 模块发生错误时
        RuntimeError:
            InvokeAI 模型管理服务发生异常时
    """
    try:
        logger.info("导入 InvokeAI 模块中")
        from invokeai.app.services.model_manager.model_manager_default import ModelManagerService  # ty: ignore[unresolved-import]
        from invokeai.app.services.model_install.model_install_common import InstallStatus  # ty: ignore[unresolved-import]
        from invokeai.app.services.model_records.model_records_sql import ModelRecordServiceSQL  # ty: ignore[unresolved-import]
        from invokeai.app.services.download.download_default import DownloadQueueService  # ty: ignore[unresolved-import]
        from invokeai.app.services.events.events_base import EventServiceBase  # ty: ignore[unresolved-import]
        from invokeai.app.services.config.config_default import get_config  # ty: ignore[unresolved-import]
        from invokeai.app.services.shared.sqlite.sqlite_util import init_db  # ty: ignore[unresolved-import]
        from invokeai.app.services.image_files.image_files_disk import DiskImageFileStorage  # ty: ignore[unresolved-import]
        from invokeai.app.services.invoker import Invoker  # ty: ignore[unresolved-import]
    except ImportError as e:
        logger.error("导入 InvokeAI 模块失败, 无法自动导入模型: %s", e)
        raise ImportError(f"导入 InvokeAI 模块发生错误: {e}") from e

    def _get_invokeai_model_manager() -> ModelManagerService:
        logger.info("初始化 InvokeAI 模型管理服务中")
        configuration = get_config()
        output_folder = configuration.outputs_path
        configuration.models_path.mkdir(parents=True, exist_ok=True)
        image_files = DiskImageFileStorage(f"{output_folder}/images")
        db = init_db(config=configuration, logger=logger, image_files=image_files)
        events = EventServiceBase()

        model_manager = ModelManagerService.build_model_manager(
            app_config=configuration,
            model_record_service=ModelRecordServiceSQL(db=db, logger=logger),
            download_queue=DownloadQueueService(app_config=configuration, event_bus=events),
            events=events,
        )

        logger.info("初始化 InvokeAI 模型管理服务完成")
        return model_manager

    def _import_model(
        model_manager: ModelManagerService,
        inplace: bool,
        model_path: Path,
    ) -> bool:
        file_name = model_path.name
        try:
            logger.info("导入 %s 模型到 InvokeAI 中", file_name)
            job = model_manager.install.heuristic_import(source=model_path.as_posix(), inplace=inplace)
            result = model_manager.install.wait_for_job(job)
            if result.status == InstallStatus.COMPLETED:
                logger.info("导入 %s 模型到 InvokeAI 成功", file_name)
                return True
            else:
                logger.error("导入 %s 模型到 InvokeAI 时出现了错误: %s", file_name, result.error)
                return False
        except Exception as e:
            logger.error("导入 %s 模型到 InvokeAI 时出现了错误: %s", file_name, e)
            return False

    def _model_exists(
        model_manager: ModelManagerService,
        model_path: Path,
    ) -> bool:
        try:
            # 获取所有已注册的模型记录
            all_models = model_manager.store.all_models()

            # 将待检测路径转换为绝对路径并统一格式
            target_path = model_path.resolve()

            for model_config in all_models:
                # model_config.path 可能是相对于 InvokeAI 根目录的路径, 也可能是绝对路径
                # 需要将其转换为绝对路径进行比对
                config_path = Path(model_config.path)
                if not config_path.is_absolute():
                    config_path = Path(get_config().models_path) / config_path

                if config_path.resolve() == target_path:
                    return True

            return False
        except Exception as e:
            logger.error("检查模型是否存在时发生错误: %s", e)
            return False

    install_result: list[tuple[Path, bool]] = []
    count = 0
    task_sum = len(model_list)

    if task_sum == 0:
        logger.info("无需要导入的模型")
        return False

    logger.info("InvokeAI 根目录: %s", os.environ.get("INVOKEAI_ROOT"))

    try:
        model_manager = _get_invokeai_model_manager()
        logger.info("启动 InvokeAI 模型管理服务")
        model_manager.start(Invoker)
    except Exception as e:
        logger.error("启动 InvokeAI 模型管理服务失败, 无法导入模型: %s", e)
        raise RuntimeError(f"启动 InvokeAI 模型管理服务出现错误: {e}") from e

    logger.info("就地安装 (仅本地) 模式: %s", ("禁用" if install_model_to_local else "启用"))

    for model in model_list:
        count += 1
        if _model_exists(model_manager, model):
            logger.info("[%s/%s] 模型 %s 已经存在，跳过导入", count, task_sum, model.name)
            install_result.append((model, True))
            continue

        logger.info("[%s/%s] 添加模型: %s", count, task_sum, model.name)
        result = _import_model(
            model_manager=model_manager,
            inplace=not install_model_to_local,
            model_path=model,
        )
        install_result.append((model, result))

    logger.info("关闭 InvokeAI 模型管理服务")
    try:
        model_manager.stop(Invoker)
    except Exception as e:
        logger.error("关闭 InvokeAI 模型管理服务出现错误: %s", e)
        raise RuntimeError(f"关闭 InvokeAI 模型管理服务出现错误: {e}") from e

    logger.info("导入 InvokeAI 模型结果")
    print_divider("-")
    print(f"{'模型名称':<40} | {'状态':<10}")
    print_divider("-")

    failed_models: list[Path] = []
    for model, success in install_result:
        status_text = "导入成功" if success else "导入失败"
        print(f"- {model.name:<38} | {status_text}")
        if not success:
            failed_models.append(model)
    print_divider("-")

    if failed_models:
        logger.warning("以下模型导入失败：")
        for m in failed_models:
            print(f"- {m.name}: {m}")
        print_divider("-")
        logger.warning("导入失败的模型可尝试通过在 InvokeAI 的模型管理 -> 添加模型 -> 链接和本地路径, 手动输入模型路径并添加")
        return False

    logger.info("所有模型导入结束")
    return True


def install_invokeai_model_from_library(
    invokeai_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """为 InvokeAI 下载模型, 使用模型库进行下载

    Args:
        invokeai_path (Path):
            InvokeAI 根目录
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
    paths = install_webui_model_from_library(
        webui_path=invokeai_path,
        dtype="invokeai",
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )
    if paths is None:
        return
    import_model_to_invokeai(model_list=paths, invokeai_path=invokeai_path)


def install_invokeai_model_from_url(
    sd_webui_path: Path,
    model_url: str,
    model_type: str,
    downloader: DownloadToolType | None = None,
) -> None:
    """从链接下载模型到 InvokeAI

    Args:
        sd_webui_path (Path):
            InvokeAI 根目录
        model_url (str):
            模型下载地址
        model_type (str):
            模型的类型
        downloader (DownloadToolType | None):
            下载模型使用的工具
    """
    model_path = sd_webui_path / "models" / model_type
    path = download_file(
        url=model_url,
        path=model_path,
        tool=downloader,
    )
    import_model_to_invokeai(model_list=[path], invokeai_path=sd_webui_path)


def install_invokeai_model_from_source(
    invokeai_path: Path | None,
    source: str,
) -> bool:
    """通过 InvokeAI 模型管理器安装模型源

    Args:
        invokeai_path (Path | None):
            InvokeAI 根目录, 为 None 时使用当前环境配置
        source (str):
            模型源, 可以是 URL、HuggingFace repo id 或本地路径

    Returns:
        bool:
            安装成功时返回 True

    Raises:
        ImportError:
            导入 InvokeAI 相关模块失败时抛出。
    """
    try:
        logger.info("导入 InvokeAI 模块中")
        from invokeai.app.services.model_manager.model_manager_default import ModelManagerService  # ty: ignore[unresolved-import]
        from invokeai.app.services.model_install.model_install_common import InstallStatus  # ty: ignore[unresolved-import]
        from invokeai.app.services.model_records.model_records_sql import ModelRecordServiceSQL  # ty: ignore[unresolved-import]
        from invokeai.app.services.download.download_default import DownloadQueueService  # ty: ignore[unresolved-import]
        from invokeai.app.services.events.events_base import EventServiceBase  # ty: ignore[unresolved-import]
        from invokeai.app.services.config.config_default import get_config  # ty: ignore[unresolved-import]
        from invokeai.app.services.shared.sqlite.sqlite_util import init_db  # ty: ignore[unresolved-import]
        from invokeai.app.services.image_files.image_files_disk import DiskImageFileStorage  # ty: ignore[unresolved-import]
        from invokeai.app.services.invoker import Invoker  # ty: ignore[unresolved-import]
    except ImportError as e:
        logger.error("导入 InvokeAI 模块失败, 无法安装模型: %s", e)
        raise ImportError(f"导入 InvokeAI 模块发生错误: {e}") from e

    def _get_invokeai_model_manager() -> ModelManagerService:
        configuration = get_config()
        configuration.models_path.mkdir(parents=True, exist_ok=True)
        image_files = DiskImageFileStorage(f"{configuration.outputs_path}/images")
        db = init_db(config=configuration, logger=logger, image_files=image_files)
        events = EventServiceBase()
        return ModelManagerService.build_model_manager(
            app_config=configuration,
            model_record_service=ModelRecordServiceSQL(db=db, logger=logger),
            download_queue=DownloadQueueService(app_config=configuration, event_bus=events),
            events=events,
        )

    with _temporary_invokeai_root(invokeai_path):
        model_manager = _get_invokeai_model_manager()
        started = False
        try:
            model_manager.start(Invoker)
            started = True
            logger.info("通过 InvokeAI 模型管理器安装模型: %s", source)
            job = model_manager.install.heuristic_import(source=source)
            result = model_manager.install.wait_for_job(job)
            if result.status == InstallStatus.COMPLETED:
                logger.info("InvokeAI 模型安装完成: %s", source)
                return True
            logger.error("InvokeAI 模型安装失败: %s", result.error)
            return False
        finally:
            if started:
                model_manager.stop(Invoker)
