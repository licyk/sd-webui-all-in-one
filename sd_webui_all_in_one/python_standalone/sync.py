"""下载 python-build-standalone 构建的 Python, 重新打包并上传到 HuggingFace / ModelScope 仓库

流程:
1. 获取指定 Release 的构建文件, 按版本 / 平台 / 变体挑选
2. 读取目标仓库中已有的文件, 只为缺失的部分创建任务
3. 多线程执行任务: 下载 -> 解压 -> 重新打包 -> 上传到缺失该文件的仓库
4. 生成包含资源类型、名称、下载链接等信息的报告
"""

import contextlib
import contextvars
import hashlib
import logging
import os
import shutil
import tempfile
import threading
import time
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path

from sd_webui_all_in_one.archive_manager import create_archive, extract_archive
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.downloader import download_file
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.portable_manager import utc_update_time
from sd_webui_all_in_one.python_standalone.release import fetch_release_assets, select_assets
from sd_webui_all_in_one.python_standalone.resources import (
    build_download_url,
    build_repo_path,
    format_size,
    normalize_path_in_repo,
    render_download_links,
    render_table,
)
from sd_webui_all_in_one.python_standalone.types import (
    RESOURCE_TYPE,
    SOURCE_SHORT_NAME,
    PythonAsset,
    PythonStandaloneResource,
    RepoTarget,
    SyncAction,
    SyncConfig,
    SyncPlan,
    SyncReport,
    SyncReportResource,
    SyncStatus,
    SyncTask,
    SyncTaskResult,
)
from sd_webui_all_in_one.repo_manager import RepoManager

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

TAG_COLORS = ["\033[35m", "\033[36m", "\033[33m", "\033[34m", "\033[32m", "\033[95m", "\033[96m", "\033[93m", "\033[94m", "\033[92m"]
"""不同任务日志标签使用的颜色"""

_RESET = "\033[0m"

_log_tag: contextvars.ContextVar[tuple[str, str] | None] = contextvars.ContextVar("python_standalone_log_tag", default=None)
"""当前线程的日志标签和颜色"""


class TaskTagFormatter(logging.Formatter):
    """在原有日志格式前添加当前任务标签的格式化类, 不同任务的标签使用不同颜色

    Attributes:
        inner (logging.Formatter): 原有的格式化类
        color (bool): 是否为标签着色
        tag_width (int): 标签对齐宽度
    """

    def __init__(
        self,
        inner: logging.Formatter,
        color: bool = True,
        tag_width: int = 0,
    ) -> None:
        """初始化格式化类

        Args:
            inner (logging.Formatter): 原有的格式化类
            color (bool): 是否为标签着色
            tag_width (int): 标签对齐宽度
        """
        super().__init__()
        self.inner = inner
        self.color = color
        self.tag_width = tag_width

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        """格式化日志, 在有任务标签时为每行添加前缀

        Args:
            record (logging.LogRecord): 日志记录
        Returns:
            str: 格式化后的日志
        """
        text = self.inner.format(record)
        tag = _log_tag.get()
        if tag is None:
            return text
        name, color = tag
        name = name.ljust(self.tag_width)
        prefix = f"{color}{name}{_RESET} │ " if self.color else f"{name} │ "
        return "\n".join(prefix + line for line in text.splitlines())


@contextlib.contextmanager
def task_log_tags(
    color: bool = True,
    tag_width: int = 0,
) -> Iterator[None]:
    """在上下文中为 SD WebUI All In One 的日志添加任务标签

    所有任务的日志经过同一个 Handler 输出, 由 Handler 的锁保证多线程输出时每行不会交错

    Args:
        color (bool): 是否为标签着色
        tag_width (int): 标签对齐宽度
    Yields:
        None: 在上下文中生效
    """
    target = logging.getLogger(LOGGER_NAME)
    saved: list[tuple[logging.Handler, logging.Formatter | None]] = []
    for handler in target.handlers:
        saved.append((handler, handler.formatter))
        handler.setFormatter(TaskTagFormatter(handler.formatter or logging.Formatter(), color=color, tag_width=tag_width))
    try:
        yield
    finally:
        for handler, formatter in saved:
            handler.setFormatter(formatter)


def set_log_tag(
    name: str,
    index: int,
) -> contextvars.Token[tuple[str, str] | None]:
    """设置当前线程的日志标签

    Args:
        name (str): 标签名称
        index (int): 用于选择颜色的序号
    Returns:
        contextvars.Token[tuple[str, str] | None]: 用于恢复之前标签的 Token
    """
    return _log_tag.set((name, TAG_COLORS[index % len(TAG_COLORS)]))


def archive_name_for(
    asset: PythonAsset,
    archive_format: str,
) -> str:
    """获取重新打包后的文件名

    Args:
        asset (PythonAsset): 源构建文件
        archive_format (str): 压缩包格式, 如 .zip
    Returns:
        str: 文件名
    """
    return f"{asset.name.split('.tar')[0]}{archive_format}"


def plan_tasks(
    selected: list[tuple[str, PythonAsset]],
    remote_files: dict[RepoTarget, set[str]],
    config: SyncConfig,
) -> list[SyncTask]:
    """根据仓库中已有的文件决定每个构建需要执行的动作

    仓库中的文件按路径判断是否存在: 重新打包的压缩包每次 hash 都不同, 而文件名中已包含构建日期

    Args:
        selected (list[tuple[str, PythonAsset]]): (平台, 构建文件) 列表
        remote_files (dict[RepoTarget, set[str]]): 各上传目标仓库中已有的文件路径, 不上传时为空字典
        config (SyncConfig): 同步配置
    Returns:
        list[SyncTask]: 任务列表
    """
    tasks: list[SyncTask] = []
    output_dir = config.output_dir.resolve()
    for platform, asset in selected:
        triple = config.platforms[platform]
        archive_name = archive_name_for(asset, config.archive_format)
        repo_path = build_repo_path(config.path_in_repo, platform, archive_name)
        present = [t for t, files in remote_files.items() if repo_path in files]
        missing = [t for t in remote_files if config.force or t not in present]
        built = not config.temp_output and (output_dir / repo_path).is_file()
        if config.force:
            action: SyncAction = "build"
        elif remote_files:
            action = "skip" if not missing else ("upload-only" if built else "build")
        else:
            action = "skip" if built else "build"
        tasks.append(
            SyncTask(
                asset=asset,
                platform=platform,
                triple=triple,
                variant=config.variant,
                archive_format=config.archive_format,
                archive_name=archive_name,
                repo_path=repo_path,
                present_targets=present,
                missing_targets=missing,
                action=action,
            )
        )
    return tasks


def fetch_remote_files(
    manager: RepoManager,
    targets: list[RepoTarget],
    revision: str | None = None,
) -> dict[RepoTarget, set[str]]:
    """获取各仓库中已有的文件路径

    Args:
        manager (RepoManager): 仓库管理器
        targets (list[RepoTarget]): 仓库列表
        revision (str | None): 仓库分支
    Returns:
        dict[RepoTarget, set[str]]: 各仓库中已有的文件路径
    """
    result: dict[RepoTarget, set[str]] = {}
    for target in targets:
        metadata = manager.get_repo_files_metadata(
            api_type=target.source,
            repo_id=target.repo_id,
            repo_type=target.repo_type,
            revision=revision,
        )
        result[target] = {str(item.get("path")) for item in metadata}
        logger.info("%s 中已有 %s 个文件", target.display_name, len(result[target]))
    return result


def create_sync_plan(
    config: SyncConfig,
    manager: RepoManager | None = None,
) -> SyncPlan:
    """获取 Release 信息和仓库状态, 生成同步计划

    Args:
        config (SyncConfig): 同步配置
        manager (RepoManager | None): 仓库管理器, 有上传目标且为 None 时自动创建
    Returns:
        SyncPlan: 同步计划
    Raises:
        ValueError: 配置不合法时
    """
    validate_sync_config(config)
    release_tag, assets = fetch_release_assets(
        release_tag=config.release_tag,
        source_repo=config.source_repo,
        token=config.github_token,
        api_url=config.github_api_url,
    )
    selected = select_assets(assets, config.versions, config.platforms, config.variant)
    remote_files: dict[RepoTarget, set[str]] = {}
    if config.targets:
        remote_files = fetch_remote_files(manager or RepoManager(), config.targets, config.revision)
    return SyncPlan(
        release_tag=release_tag,
        source_repo=config.source_repo,
        targets=list(config.targets),
        tasks=plan_tasks(selected, remote_files, config),
    )


def validate_sync_config(
    config: SyncConfig,
) -> None:
    """检查同步配置

    Args:
        config (SyncConfig): 同步配置
    Raises:
        ValueError: 配置不合法时
    """
    if not config.versions:
        raise ValueError("至少需要指定一个 Python 版本")
    if not config.platforms:
        raise ValueError("至少需要指定一个平台")
    for platform in config.platforms:
        if len(platform.split("/")) != 2 or not all(platform.split("/")):
            raise ValueError(f"平台格式应为 <系统>/<架构>: {platform}")
    if config.workers < 1:
        raise ValueError("任务并发数必须大于 0")
    if config.upload_threads < 1:
        raise ValueError("上传线程数必须大于 0")
    if config.temp_output and not config.targets:
        raise ValueError("打包结果只保存在临时目录时需要至少一个上传目标, 否则打包结果会在任务结束后被删除")
    if len({(t.source, t.repo_id) for t in config.targets}) != len(config.targets):
        raise ValueError("上传目标仓库重复")
    normalize_path_in_repo(config.path_in_repo)


def check_cancelled(
    cancel_event: threading.Event,
) -> None:
    """任务被取消时抛出异常

    Args:
        cancel_event (threading.Event): 取消事件
    Raises:
        InterruptedError: 任务被取消时
    """
    if cancel_event.is_set():
        raise InterruptedError("任务已取消")


def archive_output_path(
    task: SyncTask,
    config: SyncConfig,
    task_dir: Path,
) -> Path:
    """获取打包结果的保存路径

    Args:
        task (SyncTask): 任务
        config (SyncConfig): 同步配置
        task_dir (Path): 任务的临时目录
    Returns:
        Path: 启用 temp_output 时为任务临时目录中的路径, 否则为输出目录中与仓库相同的路径
    """
    if config.temp_output:
        return task_dir / "output" / task.archive_name
    return config.output_dir.resolve() / task.repo_path


def archive_info(
    archive: Path | None,
) -> tuple[int | None, str | None]:
    """获取打包结果的大小和 SHA256

    Args:
        archive (Path | None): 打包结果路径
    Returns:
        tuple[int | None, str | None]: 文件大小和 SHA256, 文件不存在时均为 None
    """
    if archive is None or not archive.is_file():
        return None, None
    digest = hashlib.sha256()
    with archive.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return archive.stat().st_size, digest.hexdigest()


def build_archive(
    task: SyncTask,
    config: SyncConfig,
    task_dir: Path,
    cancel_event: threading.Event,
) -> Path:
    """下载构建文件并重新打包到输出目录

    Args:
        task (SyncTask): 任务
        config (SyncConfig): 同步配置
        task_dir (Path): 任务的临时目录
        cancel_event (threading.Event): 取消事件
    Returns:
        Path: 打包结果路径
    Raises:
        RuntimeError: 构建文件结构不符合预期时
    """
    asset = task.asset
    tarball = download_file(
        url=asset.url,
        path=task_dir,
        save_name=asset.name,
        tool=config.download_tool,
        progress=config.progress,
        hash_value=asset.sha256 if config.verify_hash else None,
        hash_algorithm="sha256",
        split=config.download_split,
        cancel_event=cancel_event,
    )
    check_cancelled(cancel_event)

    extract_dir = task_dir / "extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_archive(tarball, extract_dir, progress=config.progress)
    # install_only 构建的顶层目录为 python/, 打包该目录使压缩包根目录保持为 python/
    source = extract_dir / "python"
    if not source.is_dir():
        raise RuntimeError(f"构建文件中没有 python 目录: {asset.name}")
    check_cancelled(cancel_event)

    temp_archive = task_dir / task.archive_name
    temp_archive.unlink(missing_ok=True)
    create_archive(source, temp_archive, progress=config.progress)

    output = archive_output_path(task, config, task_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(temp_archive), str(output))
    shutil.rmtree(extract_dir, ignore_errors=True)
    tarball.unlink(missing_ok=True)
    logger.info("打包完成: %s", output)
    return output


def upload_archive(
    task: SyncTask,
    archive: Path,
    config: SyncConfig,
    manager: RepoManager,
    task_dir: Path,
    target_locks: dict[RepoTarget, threading.Lock],
    uploaded: list[RepoTarget],
) -> None:
    """把打包结果上传到缺少该文件的仓库

    每个目标准备一个只包含该文件的上传目录, 以复用 RepoManager 的目录上传;
    同一仓库的上传通过锁串行执行, 避免并发提交冲突; 一个目标上传失败时仍会继续上传其他目标

    Args:
        task (SyncTask): 任务
        archive (Path): 打包结果路径
        config (SyncConfig): 同步配置
        manager (RepoManager): 仓库管理器
        task_dir (Path): 任务的临时目录
        target_locks (dict[RepoTarget, threading.Lock]): 各上传目标的锁
        uploaded (list[RepoTarget]): 上传成功的目标会添加到该列表中
    Raises:
        RuntimeError: 有目标上传失败时
    """
    path_in_repo = normalize_path_in_repo(config.path_in_repo)
    relative = Path(task.repo_path).relative_to(path_in_repo) if path_in_repo else Path(task.repo_path)
    errors: list[str] = []
    for index, target in enumerate(task.missing_targets):
        staging = task_dir / "upload" / str(index)
        staged_file = staging / relative
        staged_file.parent.mkdir(parents=True, exist_ok=True)
        staged_file.unlink(missing_ok=True)
        try:
            os.link(archive, staged_file)
        except OSError:
            shutil.copy2(archive, staged_file)

        try:
            with target_locks[target]:
                logger.info("上传 %s 到 %s", task.repo_path, target.display_name)
                manager.upload_files_to_repo(
                    api_type=target.source,
                    repo_id=target.repo_id,
                    upload_path=staging,
                    repo_type=target.repo_type,
                    path_in_repo=path_in_repo or None,
                    visibility=config.public,
                    num_threads=config.upload_threads,
                    revision=config.revision,
                )
            uploaded.append(target)
        except Exception as e:
            logger.error("上传到 %s 失败: %s", target.display_name, e)
            errors.append(f"{target.display_name}: {e}")

    if errors:
        raise RuntimeError(f"上传失败 ({'; '.join(errors)})")


def run_task(
    index: int,
    task: SyncTask,
    config: SyncConfig,
    work_dir: Path,
    manager: RepoManager | None,
    target_locks: dict[RepoTarget, threading.Lock],
    cancel_event: threading.Event,
) -> SyncTaskResult:
    """执行一个任务: 下载 -> 解压 -> 重新打包 -> 上传

    Args:
        index (int): 任务序号, 用于选择日志颜色
        task (SyncTask): 任务
        config (SyncConfig): 同步配置
        work_dir (Path): 临时工作目录
        manager (RepoManager | None): 仓库管理器, 不上传时为 None
        target_locks (dict[RepoTarget, threading.Lock]): 各上传目标的锁
        cancel_event (threading.Event): 取消事件
    Returns:
        SyncTaskResult: 执行结果
    """
    tag_token = set_log_tag(task.label, index)
    start = time.monotonic()
    task_dir = work_dir / task.slug
    task_dir.mkdir(parents=True, exist_ok=True)
    uploaded: list[RepoTarget] = []
    archive: Path | None = None
    size: int | None = None
    sha256: str | None = None
    # 临时输出模式下打包结果随任务临时目录一起删除, 结果中不再记录其路径
    archive_removed = config.temp_output and not config.keep_temp

    def _result(status: SyncStatus, error: str | None = None) -> SyncTaskResult:
        return SyncTaskResult(
            task=task,
            status=status,
            uploaded=uploaded,
            archive=None if archive_removed else archive,
            size=size,
            sha256=sha256,
            error=error,
            duration=time.monotonic() - start,
        )

    try:
        check_cancelled(cancel_event)
        if task.action == "build":
            logger.info("开始处理 %s", task.asset.name)
            archive = build_archive(task, config, task_dir, cancel_event)
        else:
            archive = config.output_dir.resolve() / task.repo_path
            logger.info("使用已有的打包结果: %s", archive)
        size, sha256 = archive_info(archive)

        if manager is not None and task.missing_targets:
            check_cancelled(cancel_event)
            upload_archive(task, archive, config, manager, task_dir, target_locks, uploaded)
        logger.info("任务完成, 耗时 %.1f 秒", time.monotonic() - start)
        return _result("success")
    except InterruptedError as e:
        return _result("cancelled", str(e))
    except Exception as e:
        logger.error("任务失败: %s", e, exc_info=logger.isEnabledFor(logging.DEBUG))
        return _result("failed", str(e))
    finally:
        if not config.keep_temp:
            shutil.rmtree(task_dir, ignore_errors=True)
            if config.temp_output and archive is not None:
                logger.info("已删除临时打包结果: %s", archive.name)
        _log_tag.reset(tag_token)


def run_sync(
    plan: SyncPlan,
    config: SyncConfig,
    manager: RepoManager | None = None,
    color: bool = LOGGER_COLOR,
) -> list[SyncTaskResult]:
    """多线程执行同步计划中的任务

    收到中断信号时停止剩余任务, 未完成的任务标记为 cancelled

    Args:
        plan (SyncPlan): 同步计划
        config (SyncConfig): 同步配置
        manager (RepoManager | None): 仓库管理器, 有上传目标且为 None 时自动创建
        color (bool): 是否为日志标签着色
    Returns:
        list[SyncTaskResult]: 所有任务的执行结果, 顺序与计划中的任务一致
    """
    pending = [t for t in plan.tasks if t.action != "skip"]
    results: dict[int, SyncTaskResult] = {id(t): SyncTaskResult(task=t, status="skipped") for t in plan.tasks if t.action == "skip"}
    if not pending:
        logger.info("没有需要执行的任务")
        return [results[id(t)] for t in plan.tasks]

    if plan.targets and manager is None:
        manager = RepoManager()
    temp_dir = None
    if config.work_dir is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="python_standalone_")
        work_dir = Path(temp_dir.name)
    else:
        work_dir = config.work_dir.resolve()
    target_locks = {t: threading.Lock() for t in plan.targets}
    cancel_event = threading.Event()

    logger.info("开始执行 %s 个任务, 并发数: %s", len(pending), config.workers)
    executor = ThreadPoolExecutor(max_workers=config.workers, thread_name_prefix="python_standalone")
    try:
        with task_log_tags(color=color, tag_width=max(len(t.label) for t in pending)):
            futures: dict[Future[SyncTaskResult], SyncTask] = {
                executor.submit(run_task, i, t, config, work_dir, manager if plan.targets else None, target_locks, cancel_event): t for i, t in enumerate(pending)
            }
            try:
                for future in as_completed(futures):
                    result = future.result()
                    results[id(result.task)] = result
            except KeyboardInterrupt:
                logger.warning("收到中断信号, 正在停止任务")
                cancel_event.set()
                executor.shutdown(wait=True, cancel_futures=True)
                for future, task in futures.items():
                    if future.done() and not future.cancelled():
                        results[id(task)] = future.result()
    finally:
        executor.shutdown(wait=True)
        if temp_dir is not None and not config.keep_temp:
            temp_dir.cleanup()

    ordered = [results.get(id(t)) or SyncTaskResult(task=t, status="cancelled", error="任务已取消") for t in plan.tasks]
    counts = {status: sum(1 for r in ordered if r.status == status) for status in ("success", "failed", "skipped", "cancelled")}
    logger.info("同步完成: 成功 %s, 失败 %s, 跳过 %s, 取消 %s", counts["success"], counts["failed"], counts["skipped"], counts["cancelled"])
    return ordered


def task_resource(
    task: SyncTask,
    config: SyncConfig,
    available_targets: list[RepoTarget],
    size: int | None = None,
    sha256: str | None = None,
) -> PythonStandaloneResource:
    """把任务转换为资源信息

    Args:
        task (SyncTask): 任务
        config (SyncConfig): 同步配置
        available_targets (list[RepoTarget]): 已有该文件的仓库, 用于生成下载链接
        size (int | None): 打包结果大小
        sha256 (str | None): 打包结果 SHA256
    Returns:
        PythonStandaloneResource: 资源信息
    """
    system, arch = task.platform.split("/")
    return {
        "type": RESOURCE_TYPE,
        "name": task.archive_name,
        "implementation": task.asset.name.split("-")[0],
        "version": task.asset.version,
        "minor": task.asset.minor,
        "build_date": task.asset.build_date,
        "platform": system,
        "arch": arch,
        "triple": task.triple,
        "variant": task.variant,
        "archive_format": task.archive_format,
        "path": task.repo_path,
        "size": size,
        "sha256": sha256,
        "urls": {t.source: build_download_url(t, task.repo_path, config.revision) for t in available_targets},
    }


def build_sync_report(
    plan: SyncPlan,
    results: list[SyncTaskResult],
    config: SyncConfig,
) -> SyncReport:
    """生成同步报告, 包含每个资源的类型、名称、下载链接和执行结果

    Args:
        plan (SyncPlan): 同步计划
        results (list[SyncTaskResult]): 执行结果
        config (SyncConfig): 同步配置
    Returns:
        SyncReport: 同步报告
    """
    resources: list[SyncReportResource] = []
    for r in results:
        available = [t for t in plan.targets if t in r.task.present_targets or t in r.uploaded]
        size, sha256 = r.size, r.sha256
        if size is None and not config.temp_output:
            # 跳过的任务可能在输出目录中有之前的打包结果
            size, sha256 = archive_info(config.output_dir.resolve() / r.task.repo_path)
        resource = task_resource(r.task, config, available, size, sha256)
        resources.append(
            {
                **resource,
                "action": r.task.action,
                "status": r.status,
                "uploaded_to": [t.source for t in r.uploaded],
                "error": r.error,
                "duration": round(r.duration, 1),
            }
        )
    return {
        "type": RESOURCE_TYPE,
        "generated_at": utc_update_time(),
        "source_repo": plan.source_repo,
        "release_tag": plan.release_tag,
        "targets": [t.display_name for t in plan.targets],
        "summary": {
            "total": len(results),
            "success": sum(1 for r in results if r.status == "success"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "skipped": sum(1 for r in results if r.status == "skipped"),
            "cancelled": sum(1 for r in results if r.status == "cancelled"),
        },
        "resources": resources,
    }


def render_sync_plan(
    plan: SyncPlan,
) -> str:
    """把同步计划渲染为终端表格

    Args:
        plan (SyncPlan): 同步计划
    Returns:
        str: 表格文本
    """
    target_names = [SOURCE_SHORT_NAME[t.source] for t in plan.targets]
    rows = [
        [
            task.asset.version,
            task.platform,
            task.archive_name,
            *["✓" if t in task.present_targets else "✗" for t in plan.targets],
            task.action + (f" -> {','.join(SOURCE_SHORT_NAME[t.source] for t in task.missing_targets)}" if task.action != "skip" and task.missing_targets else ""),
        ]
        for task in plan.tasks
    ]
    counts = {action: sum(1 for t in plan.tasks if t.action == action) for action in ("build", "upload-only", "skip")}
    header = f"{plan.source_repo} {plan.release_tag}, 上传目标: {', '.join(t.display_name for t in plan.targets) or '无'}"
    table = render_table(["版本", "平台", "文件", *target_names, "动作"], rows)
    return f"{header}\n\n{table}\n\n共 {len(plan.tasks)} 个任务: 构建 {counts['build']}, 仅上传 {counts['upload-only']}, 跳过 {counts['skip']}"


_STATUS_TEXT = {
    "success": "✅ 成功",
    "failed": "❌ 失败",
    "skipped": "⏭️ 跳过",
    "cancelled": "⚠️ 取消",
}
"""报告中任务状态的展示文本"""


def render_sync_report_markdown(
    report: SyncReport,
) -> str:
    """把同步报告渲染为 Markdown

    Args:
        report (SyncReport): 同步报告
    Returns:
        str: Markdown 文本
    """
    summary = report["summary"]
    lines = [
        f"## Python Standalone 同步报告 ({report['release_tag']})",
        "",
        f"- 来源: [{report['source_repo']}](https://github.com/{report['source_repo']}/releases/tag/{report['release_tag']})",
        f"- 上传目标: {', '.join(report['targets']) or '无'}",
        f"- 生成时间: {report['generated_at']}",
        f"- 结果: 共 {summary['total']} 个, 成功 {summary['success']}, 失败 {summary['failed']}, 跳过 {summary['skipped']}, 取消 {summary['cancelled']}",
        "",
        "| 类型 | 名称 | 版本 | 平台 | 变体 | 大小 | 动作 | 结果 | 下载链接 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report["resources"]:
        status = _STATUS_TEXT.get(r["status"], r["status"])
        if r["error"]:
            status += f": {r['error']}"
        lines.append(
            f"| {r['type']} | `{r['name']}` | {r['version']} | {r['platform']}/{r['arch']} | {r['variant']} | {format_size(r['size'])} | {r['action']} | {status} | {render_download_links(r['urls'])} |"
        )
    return "\n".join(lines) + "\n"


def sync_exit_code(
    results: list[SyncTaskResult],
) -> int:
    """根据执行结果获取退出码

    Args:
        results (list[SyncTaskResult]): 执行结果
    Returns:
        int: 有任务取消时为 130, 有任务失败时为 1, 否则为 0
    """
    if any(r.status == "cancelled" for r in results):
        return 130
    if any(r.status == "failed" for r in results):
        return 1
    return 0
