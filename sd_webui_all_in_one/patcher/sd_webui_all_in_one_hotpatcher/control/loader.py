"""运行时加载、卸载、重新加载与更新补丁模块。

补丁模块是定义了以下函数的 Python 模块或文件::

    def setup(ctx: PatchContext) -> None: ...                 # 必需
    def teardown(ctx: PatchContext) -> None: ...              # 可选, 卸载时在撤销日志之前调用
    def update(ctx: PatchContext, config: dict) -> bool: ...  # 可选, 原地修改参数

- ``source`` 为点分模块名时按常规方式导入 (已导入时直接复用)。以 ``.py`` 结尾或指向已存在路径时按文件加载,
  模块名为私有的 ``sd_webui_all_in_one_hotpatcher_dynamic.<set_id>`` (``set_id`` 为首次执行这份代码的补丁集 ID),
  不会出现在用户可见的模块名中, 卸载后也不会留在 ``sys.modules``。文件加载不使用字节码缓存, 执行的就是
  计算哈希时读取的同一份源码。
- 模块导入与 ``setup`` 都在新建的事务补丁集激活时执行, 两者登记的修改都归属该补丁集; 任一步失败时撤销全部修改,
  报告状态为 ``failed``。``teardown`` / ``update`` 用 ``context.activate()`` 执行, 抛出异常不会撤销补丁集。
- 补丁名称是稳定的键, 跨重新加载保持不变; 补丁集 ID 每次 (重新) 加载都会变化 (已关闭的补丁集不能重新打开)。
- 重新加载先卸载旧补丁集再执行新代码, 新代码失败时用旧模块对象 (点分模块恢复其 ``__dict__`` 快照) 在新的补丁集中
  重新执行旧 ``setup``, 状态为 ``rolled_back`` 并附带错误; 回滚也失败时状态为 ``failed`` 且同时包含两个错误。
- 按点分模块名加载的模块在补丁集生命周期内登记到 ``state.rebind_skip_modules``, ``rebind_references`` 扫描时跳过它,
  避免包装函数通过模块全局变量调用到自己。文件加载的私有模块名本身已被扫描跳过。

所有公开函数返回 JSON 安全的报告字典而不是抛出异常, 便于 ``apply_config``、文件监视器和远程命令直接使用。

锁约定: ``state.control_lock`` 只用于读写 ``loaded_patches`` / ``loading_patches`` / ``rebind_skip_modules`` /
``patch_file_watcher``; 导入、``setup`` / ``teardown`` / ``update`` 以及文件读取都在锁外执行。同名补丁的并发操作通过
``loading_patches`` 标记拒绝 (错误码 ``busy``), 而不是在执行用户代码时持有互斥锁。

信任边界: 加载补丁就是执行代码。进程内调用总是允许; 通过运行时通道发起的加载必须先经过
``check_remote_load_allowed`` (``control.allow_remote_load`` 为 True, 旧版传输还要求非空 token)。
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import importlib.machinery
import importlib.util
import logging
import math
import os
import sys
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

from ..state import HotpatcherState, get_default_state
from .handles import PatchOutcome, PatchStatus
from .patchset import PatchSet, register_patch_set, remove_patch_set

if TYPE_CHECKING:
    from .features import FeatureContext

__all__ = [
    "DEFAULT_WATCH_DEBOUNCE",
    "DEFAULT_WATCH_INTERVAL",
    "DYNAMIC_PACKAGE",
    "ORIGIN_API",
    "ORIGIN_CONFIG",
    "REMOTE_LOAD_DISABLED",
    "REMOTE_LOAD_FORBIDDEN",
    "WATCH_ENV",
    "LoadedPatch",
    "PatchFileWatcher",
    "PatchLoaderError",
    "RemoteLoadError",
    "check_remote_load_allowed",
    "get_loaded_patch",
    "list_loaded_patches",
    "load_patch",
    "reload_patch",
    "start_patch_watcher",
    "stop_patch_watcher",
    "unload_patch",
    "update_patch",
    "watch_enabled_from_env",
]

_LOGGER = logging.getLogger(__name__)

DYNAMIC_PACKAGE = "sd_webui_all_in_one_hotpatcher_dynamic"
"""文件加载的补丁模块所在的私有命名空间包"""

WATCH_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_WATCH"
"""值为 ``1`` 时 ``apply_config`` 启动补丁文件监视器的环境变量名"""

DEFAULT_WATCH_INTERVAL = 1.0
"""补丁文件监视器默认轮询间隔, 秒"""

DEFAULT_WATCH_DEBOUNCE = 0.5
"""补丁文件内容需要保持不变多久才会触发重新加载, 秒"""

ORIGIN_API = "api"
"""通过 Python API 或命令加载的补丁"""

ORIGIN_CONFIG = "config"
"""由 ``control.patch_sets`` 配置加载的补丁"""

REMOTE_LOAD_DISABLED = "remote_load_disabled"
"""远程加载未启用时的错误码"""

REMOTE_LOAD_FORBIDDEN = "forbidden"
"""远程加载缺少必需 token 时的错误码"""

_CONTROL_FEATURE_KEY = "control"
_EVENT_HANDLE_LIMIT = 32
_FEATURE_SET_PREFIX = "feature:"
_TOKEN_EXEMPT_TRANSPORTS = frozenset({"desktop"})
_STATUS_PRIORITY = {
    PatchStatus.DEREGISTERED.value: 1,
    PatchStatus.REVERTED.value: 2,
    PatchStatus.REQUIRES_RESTART.value: 3,
    PatchStatus.FAILED.value: 4,
}


class PatchLoaderError(Exception):
    """
    补丁加载参数或流程错误。

    Attributes:
        code (str):
            机器可读的错误码, 例如 ``invalid_source``、``not_found``、``busy``、``missing_setup``。
    """

    def __init__(self, code: str, message: str) -> None:
        """
        创建错误。

        Args:
            code (str):
                错误码。
            message (str):
                错误描述。
        """

        super().__init__(message)
        self.code = code


class RemoteLoadError(PermissionError):
    """
    远程加载补丁被信任边界拒绝。

    Attributes:
        code (str):
            ``remote_load_disabled`` 或 ``forbidden``。
    """

    def __init__(self, code: str, message: str) -> None:
        """
        创建错误。

        Args:
            code (str):
                错误码。
            message (str):
                错误描述。
        """

        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class _Source:
    kind: str
    key: str
    path: str | None


@dataclass
class LoadedPatch:
    """
    一个已加载的补丁模块。

    Attributes:
        name (str):
            补丁名称, 跨重新加载保持不变。
        source (str):
            规范化后的来源: 点分模块名, 或文件的绝对路径。
        kind (str):
            ``module`` 或 ``file``。
        module_name (str):
            模块名; 文件加载时为私有模块名。
        path (str | None):
            源文件路径, 无法确定时为 None。
        sha256 (str | None):
            加载时源文件内容的 SHA-256, 无法读取时为 None。
        loaded_at (float):
            最近一次 (重新) 加载完成的时间, ``time.time()`` 秒。
        config (dict[str, Any]):
            当前补丁配置。
        origin (str):
            ``api`` 或 ``config``。
        patch_set (PatchSet):
            当前补丁集。
        module (ModuleType):
            当前模块对象。
        generation (int):
            成功执行新代码的次数, 首次加载为 1。
        status (str):
            ``loaded``, 或最近一次重新加载失败后回滚的 ``rolled_back``。
        last_error (dict[str, Any] | None):
            最近一次失败的重新加载错误。
        failed_sha256 (str | None):
            最近一次重新加载失败时的源文件哈希, 内容未再变化时不会自动重试。
    """

    name: str
    source: str
    kind: str
    module_name: str
    path: str | None
    sha256: str | None
    loaded_at: float
    config: dict[str, Any]
    origin: str
    patch_set: PatchSet
    module: ModuleType = field(repr=False)
    generation: int = 1
    status: str = "loaded"
    last_error: dict[str, Any] | None = None
    failed_sha256: str | None = None

    @property
    def set_id(self) -> str:
        """
        当前补丁集 ID。

        Returns:
            str:
                补丁集 ID, 每次 (重新) 加载都会变化。
        """

        return self.patch_set.id

    def to_dict(self) -> dict[str, Any]:
        """
        生成可序列化的描述。

        Returns:
            dict[str, Any]:
                不含模块对象的字段字典, ``set`` 为补丁集摘要。
        """

        return {
            "name": self.name,
            "source": self.source,
            "kind": self.kind,
            "module": self.module_name,
            "path": self.path,
            "sha256": self.sha256,
            "loaded_at": self.loaded_at,
            "config": copy.deepcopy(self.config),
            "origin": self.origin,
            "set_id": self.set_id,
            "generation": self.generation,
            "status": self.status,
            "last_error": copy.deepcopy(self.last_error),
            "set": _set_summary(self.patch_set),
        }


@dataclass
class _Attempt:
    patch_set: PatchSet
    module_name: str
    module: ModuleType | None = None
    path: str | None = None
    sha256: str | None = None
    error: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class _FreshSourceLoader(importlib.machinery.SourceFileLoader):
    """执行给定源码字节的文件 loader, 不读写字节码缓存。"""

    def __init__(self, fullname: str, path: str, source: bytes) -> None:
        super().__init__(fullname, path)
        self._source = source

    def get_data(self, path: str) -> bytes:
        if path == self.path:
            return self._source
        return super().get_data(path)

    def get_code(self, fullname: str) -> Any:
        del fullname
        return self.source_to_code(self._source, self.path)


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def load_patch(
    source: str | os.PathLike[str],
    *,
    name: str | None = None,
    config: dict[str, Any] | None = None,
    state: HotpatcherState | None = None,
    origin: str = ORIGIN_API,
) -> dict[str, Any]:
    """
    加载补丁模块并在新的事务补丁集中执行 ``setup(ctx)``。

    Args:
        source (str | os.PathLike[str]):
            点分模块名, 或补丁文件路径 (以 ``.py`` 结尾或指向已存在的文件)。
        name (str | None):
            补丁名称。为 None 时使用规范化后的来源 (模块名或绝对路径)。不能以 ``feature:`` 开头。
        config (dict[str, Any] | None):
            补丁配置, 通过 ``ctx.config`` 读取。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
        origin (str):
            加载来源标记, ``api`` 或 ``config``; reconcile 只会卸载 ``config`` 来源的补丁。

    Returns:
        dict[str, Any]:
            JSON 安全的报告: ``status`` 为 ``loaded`` / ``failed``, 失败时 ``error`` 含 ``code``、``stage``、
            ``error_type``、``message``、``traceback``, ``set`` 含逐句柄状态。
    """

    active_state = state or get_default_state()
    report = _new_report("load", name)
    try:
        resolved = _resolve_source(source)
        patch_name = _validate_name(name, resolved)
        patch_config = _validate_config(config)
        _validate_origin(origin)
    except PatchLoaderError as exc:
        return _fail(report, exc.code, str(exc))
    report.update(name=patch_name, source=resolved.key, kind=resolved.kind)
    try:
        _reserve_new(active_state, patch_name)
    except PatchLoaderError as exc:
        return _fail(report, exc.code, str(exc))
    try:
        attempt = _attempt_new_code(resolved, patch_name, patch_config, active_state)
        if not attempt.ok:
            report.update(ok=False, status="failed", error=attempt.error, set_id=attempt.patch_set.id, set=_set_summary(attempt.patch_set))
            _emit(active_state, "set.failed", {"action": "load", "name": patch_name, "source": resolved.key, "set_id": attempt.patch_set.id, "error": _error_brief(attempt.error)})
            return report
        record = LoadedPatch(
            name=patch_name,
            source=resolved.key,
            kind=resolved.kind,
            module_name=attempt.module_name,
            path=attempt.path,
            sha256=attempt.sha256,
            loaded_at=time.time(),
            config=copy.deepcopy(patch_config),
            origin=origin,
            patch_set=attempt.patch_set,
            module=_require_module(attempt),
        )
        commit_error = _commit(record, active_state)
        if commit_error is not None:
            _discard_record_module(record, active_state)
            report.update(ok=False, status="failed", error=commit_error, set_id=attempt.patch_set.id, set=_set_summary(attempt.patch_set))
            _emit(active_state, "set.failed", {"action": "load", "name": patch_name, "source": resolved.key, "set_id": attempt.patch_set.id, "error": _error_brief(commit_error)})
            return report
        report.update(status="loaded", **_record_fields(record))
        _emit(
            active_state,
            "set.loaded",
            {
                "name": patch_name,
                "set_id": record.set_id,
                "source": record.source,
                "kind": record.kind,
                "origin": origin,
                "generation": record.generation,
                "handle_count": len(record.patch_set.handles),
            },
        )
        return report
    finally:
        _release(active_state, patch_name)


def unload_patch(key: str, *, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    卸载补丁: 调用可选的 ``teardown(ctx)``, 关闭补丁集, 再移除私有模块和 rebind 跳过登记。

    Args:
        key (str):
            补丁集 ID 或补丁名称, ID 优先。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            JSON 安全的报告: ``handles`` 为逐句柄状态 (``reverted`` / ``deregistered`` / ``requires_restart`` /
            ``failed``), ``status`` 为其中最严重的状态 (没有句柄时为 ``reverted``, 有错误时为 ``failed``),
            ``teardown`` 为 ``ok`` / ``failed`` / None (未定义)。
    """

    active_state = state or get_default_state()
    report = _new_report("unload", key)
    try:
        record = _reserve_existing(active_state, key)
    except PatchLoaderError as exc:
        return _fail(report, exc.code, str(exc))
    try:
        return _unload_reserved(record, active_state)
    finally:
        _release(active_state, record.name)


def reload_patch(key: str, *, config: dict[str, Any] | None = None, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    重新加载补丁: 卸载旧补丁集, 执行新代码; 新代码失败时用旧模块回滚。

    点分模块通过 ``importlib.reload`` 重新执行 (之前保存 ``__dict__`` 快照, 失败时恢复);
    文件重新读取并在新的私有模块名下执行。补丁名称不变, 补丁集 ID 变化。

    Args:
        key (str):
            补丁集 ID 或补丁名称。
        config (dict[str, Any] | None):
            新配置。为 None 时沿用当前配置; 回滚时总是使用旧配置。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            JSON 安全的报告: ``status`` 为 ``reloaded`` / ``rolled_back`` / ``failed``; ``unload`` 为旧补丁集的卸载报告,
            ``error`` 为新代码的错误, ``rollback_error`` 为回滚失败的错误, ``previous_set_id`` 为旧补丁集 ID。
    """

    active_state = state or get_default_state()
    report = _new_report("reload", key)
    try:
        new_config = None if config is None else _validate_config(config)
        record = _reserve_existing(active_state, key)
    except PatchLoaderError as exc:
        return _fail(report, exc.code, str(exc))
    try:
        _reload_reserved(record, record.config if new_config is None else new_config, report, active_state)
        return report
    finally:
        _release(active_state, record.name)


def update_patch(key: str, config: dict[str, Any], *, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    修改补丁配置。

    模块定义了 ``update(ctx, config)`` 且返回真值时原地修改 (``mode`` 为 ``in_place``), 否则以新配置重新加载
    (``mode`` 为 ``reload``, ``reload`` 字段含重新加载报告)。``update`` 抛出异常时补丁集保持原样,
    状态为 ``failed``。

    Args:
        key (str):
            补丁集 ID 或补丁名称。
        config (dict[str, Any]):
            新配置, 整体替换旧配置。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            JSON 安全的报告, ``status`` 为 ``updated`` / ``reloaded`` / ``rolled_back`` / ``failed``。
    """

    active_state = state or get_default_state()
    report = _new_report("update", key)
    report["mode"] = None
    try:
        new_config = _validate_config(config)
        record = _reserve_existing(active_state, key)
    except PatchLoaderError as exc:
        return _fail(report, exc.code, str(exc))
    try:
        report.update(name=record.name, set_id=record.set_id)
        updater = getattr(record.module, "update", None)
        if callable(updater):
            context = record.patch_set.context
            report["mode"] = "in_place"
            try:
                with context.activate():
                    updated = updater(context, copy.deepcopy(new_config))
            except Exception as exc:
                report.update(ok=False, status="failed", error=_error_info("update_failed", "update", exc), set=_set_summary(record.patch_set))
                _emit(active_state, "set.failed", {"action": "update", "name": record.name, "set_id": record.set_id, "mode": "in_place", "error": _error_brief(report["error"])})
                return report
            if updated:
                with active_state.control_lock:
                    context.config = copy.deepcopy(new_config)
                    record.config = copy.deepcopy(new_config)
                report.update(status="updated", set=_set_summary(record.patch_set))
                _emit(active_state, "set.updated", {"name": record.name, "set_id": record.set_id, "mode": "in_place"})
                return report
        report["mode"] = "reload"
        reload_report = _new_report("reload", record.name)
        _reload_reserved(record, new_config, reload_report, active_state)
        report["reload"] = reload_report
        report.update(ok=reload_report["ok"], status=reload_report["status"], error=reload_report["error"], set_id=reload_report["set_id"], set=reload_report.get("set"))
        if reload_report["status"] == "reloaded":
            _emit(active_state, "set.updated", {"name": record.name, "set_id": reload_report["set_id"], "previous_set_id": record.set_id, "mode": "reload"})
        return report
    finally:
        _release(active_state, record.name)


def get_loaded_patch(key: str, *, state: HotpatcherState | None = None) -> LoadedPatch | None:
    """
    按补丁集 ID 或补丁名称查询已加载补丁, ID 优先。

    Args:
        key (str):
            补丁集 ID 或补丁名称。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        LoadedPatch | None:
            已加载补丁, 不存在时为 None。
    """

    active_state = state or get_default_state()
    with active_state.control_lock:
        return _lookup(active_state, key)


def list_loaded_patches(*, state: HotpatcherState | None = None) -> list[dict[str, Any]]:
    """
    列出已加载补丁。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        list[dict[str, Any]]:
            ``LoadedPatch.to_dict()`` 列表, 按加载顺序排列。
    """

    active_state = state or get_default_state()
    with active_state.control_lock:
        records = list(active_state.loaded_patches.values())
    return [record.to_dict() for record in records]


def check_remote_load_allowed(*, state: HotpatcherState | None = None, transport: str, token: str | None) -> None:
    """
    检查通过运行时通道加载补丁代码是否被允许 (D6 信任边界)。

    规则: 当前生效配置的 ``control.allow_remote_load`` 必须严格为 True; 除桌面传输外 (旧版传输以及任何
    未知传输) 还要求 ``token`` 非空。进程内 Python API 调用不经过本检查。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。读取其当前配置, 尚未应用配置时视为未启用。
        transport (str):
            请求来源传输, 例如 ``legacy`` / ``desktop``。
        token (str | None):
            该连接使用的 token。

    Raises:
        RemoteLoadError:
            未启用远程加载时 ``code`` 为 ``remote_load_disabled``; 缺少 token 时为 ``forbidden``。
    """

    active_state = state or get_default_state()
    with active_state.current_config_lock:
        current = copy.deepcopy(active_state.current_config) if active_state.current_config is not None else {}
    control = current.get(_CONTROL_FEATURE_KEY) if isinstance(current, dict) else None
    allowed = isinstance(control, dict) and control.get("allow_remote_load") is True
    if not allowed:
        raise RemoteLoadError(REMOTE_LOAD_DISABLED, "remote patch loading is disabled; set control.allow_remote_load to true to enable it")
    if transport in _TOKEN_EXEMPT_TRANSPORTS:
        return
    if not isinstance(token, str) or not token.strip():
        raise RemoteLoadError(REMOTE_LOAD_FORBIDDEN, f"remote patch loading over {transport!r} transport requires a non-empty runtime token")


def watch_enabled_from_env() -> bool:
    """
    读取补丁文件监视环境变量。

    Returns:
        bool:
            ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_WATCH=1`` 时返回 True。
    """

    return os.getenv(WATCH_ENV) == "1"


def start_patch_watcher(*, interval: float | None = None, state: HotpatcherState | None = None) -> PatchFileWatcher:
    """
    启动 (或复用) 状态对象的补丁文件监视器。

    Args:
        interval (float | None):
            轮询间隔秒数。为 None 时保持当前值。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        PatchFileWatcher:
            正在运行的监视器。

    Raises:
        ValueError:
            ``interval`` 不是正有限数时抛出。
    """

    active_state = state or get_default_state()
    parsed = None if interval is None else _coerce_interval(interval)
    with active_state.control_lock:
        watcher = active_state.patch_file_watcher
        if watcher is None:
            watcher = PatchFileWatcher(state=active_state, interval=parsed if parsed is not None else DEFAULT_WATCH_INTERVAL)
            active_state.patch_file_watcher = watcher
        elif parsed is not None:
            watcher.interval = parsed
    watcher.start()
    return watcher


def stop_patch_watcher(*, state: HotpatcherState | None = None, timeout: float | None = 5.0) -> bool:
    """
    停止并移除状态对象的补丁文件监视器。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
        timeout (float | None):
            等待监视线程退出的秒数。

    Returns:
        bool:
            存在监视器时返回 True。
    """

    active_state = state or get_default_state()
    with active_state.control_lock:
        watcher = active_state.patch_file_watcher
        active_state.patch_file_watcher = None
    if watcher is None:
        return False
    watcher.stop(timeout=timeout)
    return True


class PatchFileWatcher:
    """
    轮询已加载补丁源文件的监视器 (仅标准库, 默认关闭)。

    每次轮询比较源文件的 mtime / size, 变化时重新计算 SHA-256; 哈希与已加载版本不同且在 ``debounce``
    秒内保持不变时调用 ``reload_patch``。重新加载失败 (含回滚) 的内容会被记住, 直到文件再次变化才重试。
    重新加载在不持有任何 hotpatcher 锁的情况下执行。

    Attributes:
        state (HotpatcherState):
            所属状态对象。
        interval (float):
            轮询间隔秒数。
        debounce (float):
            内容保持不变多久后才重新加载, 秒。
        failures (dict[str, dict[str, Any]]):
            每个补丁最近一次失败的重新加载报告。
        reload_count (int):
            已触发的重新加载次数。
    """

    def __init__(
        self,
        *,
        state: HotpatcherState | None = None,
        interval: float = DEFAULT_WATCH_INTERVAL,
        debounce: float = DEFAULT_WATCH_DEBOUNCE,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Any] | None = None,
        reload: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        """
        创建监视器, 不会自动启动。

        Args:
            state (HotpatcherState | None):
                可选状态对象。为 None 时使用默认状态。
            interval (float):
                轮询间隔秒数。
            debounce (float):
                防抖秒数, 0 表示检测到变化立即重新加载。
            clock (Callable[[], float]):
                单调时钟, 便于测试注入。
            sleep (Callable[[float], Any] | None):
                轮询之间的等待函数。为 None 时使用可被 ``stop()`` 立即唤醒的等待。
            reload (Callable[..., dict[str, Any]] | None):
                重新加载函数 ``reload(name, *, state)``。为 None 时使用 ``reload_patch``。

        Raises:
            ValueError:
                ``interval`` 不是正有限数, 或 ``debounce`` 为负数时抛出。
        """

        self.state = state or get_default_state()
        self.interval = _coerce_interval(interval)
        if isinstance(debounce, bool) or not isinstance(debounce, (int, float)) or not math.isfinite(debounce) or debounce < 0:
            raise ValueError(f"debounce must be a non-negative finite number, got {debounce!r}")
        self.debounce = float(debounce)
        self.failures: dict[str, dict[str, Any]] = {}
        self.reload_count = 0
        self._clock = clock
        self._sleep = sleep
        self._reload = reload or reload_patch
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._polling = False
        self._stats: dict[str, tuple[str, int, int, str]] = {}
        self._pending: dict[str, tuple[str, float]] = {}
        self._failed_hashes: dict[str, str] = {}

    @property
    def running(self) -> bool:
        """
        监视线程是否在运行。

        Returns:
            bool:
                线程存活时返回 True。
        """

        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self) -> PatchFileWatcher:
        """
        启动守护线程, 已在运行时不做任何事。

        Returns:
            PatchFileWatcher:
                当前监视器。
        """

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, name="sd_webui_all_in_one_hotpatcher-patch-watcher", daemon=True)
            thread = self._thread
        thread.start()
        return self

    def stop(self, timeout: float | None = 5.0) -> None:
        """
        停止守护线程。

        Args:
            timeout (float | None):
                等待线程退出的秒数。
        """

        self._stop_event.set()
        with self._lock:
            thread = self._thread
            self._thread = None
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)

    def poll_once(self) -> list[dict[str, Any]]:
        """
        执行一次轮询, 返回本次触发的重新加载报告。

        与后台线程并发调用时, 后到的调用直接返回空列表。

        Returns:
            list[dict[str, Any]]:
                重新加载报告列表。
        """

        with self._lock:
            if self._polling:
                return []
            self._polling = True
        try:
            return self._poll()
        finally:
            with self._lock:
                self._polling = False

    def _poll(self) -> list[dict[str, Any]]:
        with self.state.control_lock:
            targets = [(record.name, record.path, record.sha256) for record in self.state.loaded_patches.values() if record.path is not None and record.name not in self.state.loading_patches]
            known = set(self.state.loaded_patches)
        for cache in (self._stats, self._pending, self._failed_hashes, self.failures):
            for name in [name for name in cache if name not in known]:
                del cache[name]
        reports: list[dict[str, Any]] = []
        for name, path, loaded_hash in targets:
            current = self._fingerprint(name, path)
            if current is None:
                continue
            if current == loaded_hash:
                self._pending.pop(name, None)
                self._failed_hashes.pop(name, None)
                continue
            if current == self._failed_hashes.get(name):
                continue
            now = self._clock()
            pending = self._pending.get(name)
            if pending is None or pending[0] != current:
                self._pending[name] = (current, now)
                if self.debounce > 0:
                    continue
            elif now - pending[1] < self.debounce:
                continue
            self._pending.pop(name, None)
            _emit(self.state, "set.watch_reload", {"name": name, "path": path, "sha256": current})
            report = self._reload(name, state=self.state)
            self.reload_count += 1
            reports.append(report)
            error = report.get("error") or {}
            if report.get("status") == "reloaded":
                self._failed_hashes.pop(name, None)
                self.failures.pop(name, None)
            elif error.get("code") in {"busy", "not_found"}:
                # 其他操作正在进行或补丁已卸载: 不记为内容失败, 下次轮询重新判断。
                continue
            else:
                self._failed_hashes[name] = current
                self.failures[name] = report
                _emit(self.state, "set.watch_failed", {"name": name, "path": path, "status": report.get("status"), "error": _error_brief(error)})
                _LOGGER.warning("Hotpatcher patch %r reload after file change %s: %s", name, report.get("status"), error.get("message"))
        return reports

    def _fingerprint(self, name: str, path: str) -> str | None:
        try:
            stat = os.stat(path)
        except OSError:
            return None
        cached = self._stats.get(name)
        if cached is not None and cached[:3] == (path, stat.st_mtime_ns, stat.st_size):
            return cached[3]
        try:
            digest = _sha256_file(path)
        except OSError:
            return None
        self._stats[name] = (path, stat.st_mtime_ns, stat.st_size, digest)
        return digest

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception as exc:
                _LOGGER.warning("Hotpatcher patch watcher poll failed: %s: %s", type(exc).__name__, exc)
            if self._stop_event.is_set():
                break
            if self._sleep is not None:
                self._sleep(self.interval)
            else:
                self._stop_event.wait(self.interval)


# ---------------------------------------------------------------------------
# 加载流程
# ---------------------------------------------------------------------------


def _resolve_source(source: Any) -> _Source:
    if isinstance(source, os.PathLike):
        text = os.fspath(source)
        if not isinstance(text, str):
            raise PatchLoaderError("invalid_source", "patch source path must be a text path")
        path_like = True
    elif isinstance(source, str):
        text = source.strip()
        path_like = False
    else:
        raise PatchLoaderError("invalid_source", f"patch source must be a module name or a file path, got {type(source).__name__}")
    if not text:
        raise PatchLoaderError("invalid_source", "patch source must be a non-empty string")
    candidate = Path(text).expanduser()
    if path_like or text.endswith(".py") or candidate.exists():
        resolved = candidate.resolve()
        if resolved.is_dir():
            raise PatchLoaderError("invalid_source", f"patch source {text!r} is a directory; pass a .py file or a dotted module name")
        if not resolved.is_file():
            raise PatchLoaderError("not_found", f"patch file not found: {resolved}")
        return _Source("file", str(resolved), str(resolved))
    if not all(part.isidentifier() for part in text.split(".")):
        raise PatchLoaderError("invalid_source", f"patch source {text!r} is neither a dotted module name nor an existing file")
    return _Source("module", text, None)


def _validate_name(name: Any, source: _Source) -> str:
    if name is None:
        return source.key
    if not isinstance(name, str) or not name.strip():
        raise PatchLoaderError("invalid_name", f"patch name must be a non-empty string, got {name!r}")
    if name.startswith(_FEATURE_SET_PREFIX):
        raise PatchLoaderError("invalid_name", f"patch name must not start with {_FEATURE_SET_PREFIX!r}: {name!r}")
    return name


def _validate_origin(origin: Any) -> None:
    if origin not in (ORIGIN_API, ORIGIN_CONFIG):
        raise PatchLoaderError("invalid_origin", f"unknown patch origin {origin!r}")


def _validate_config(config: Any) -> dict[str, Any]:
    if config is None:
        return {}
    if not isinstance(config, Mapping):
        raise PatchLoaderError("invalid_config", f"patch config must be an object, got {type(config).__name__}")
    return copy.deepcopy(dict(config))


def _attempt_new_code(source: _Source, name: str, config: dict[str, Any], state: HotpatcherState, *, reload_from: ModuleType | None = None) -> _Attempt:
    patch_set = PatchSet(name, transactional=True, config=config, state=state)
    if source.kind == "file":
        module_name = f"{DYNAMIC_PACKAGE}.{patch_set.id}"
        path = source.key

        def execute_file() -> tuple[ModuleType, str | None, str | None]:
            data = Path(path).read_bytes()
            return _exec_file_module(module_name, path, data), path, hashlib.sha256(data).hexdigest()

        return _run_attempt(patch_set, module_name, execute_file, private=True)

    module_name = source.key

    def execute_module() -> tuple[ModuleType, str | None, str | None]:
        if reload_from is not None:
            importlib.invalidate_caches()
            module = importlib.reload(reload_from)
        else:
            module = importlib.import_module(module_name)
        module_path, digest = _module_file_hash(module)
        return module, module_path, digest

    _add_rebind_skip(state, module_name, patch_set.id)
    attempt = _run_attempt(patch_set, module_name, execute_module, private=False)
    if not attempt.ok:
        _remove_rebind_skip(state, module_name, patch_set.id)
    return attempt


def _attempt_old_code(record: LoadedPatch, state: HotpatcherState) -> _Attempt:
    patch_set = PatchSet(record.name, transactional=True, config=record.config, state=state)
    module = record.module

    def execute() -> tuple[ModuleType, str | None, str | None]:
        # 文件补丁: 旧私有模块在卸载时已移除, 重新放回原名称; 点分模块: 确保 sys.modules 指向旧模块对象。
        sys.modules[record.module_name] = module
        return module, record.path, record.sha256

    private = record.kind == "file"
    if not private:
        _add_rebind_skip(state, record.module_name, patch_set.id)
    attempt = _run_attempt(patch_set, record.module_name, execute, private=private)
    if not attempt.ok and not private:
        _remove_rebind_skip(state, record.module_name, patch_set.id)
    return attempt


def _run_attempt(
    patch_set: PatchSet,
    module_name: str,
    execute: Callable[[], tuple[ModuleType, str | None, str | None]],
    *,
    private: bool,
) -> _Attempt:
    attempt = _Attempt(patch_set=patch_set, module_name=module_name)
    stage = "import"
    try:
        # 事务模式: 导入或 setup 抛出异常时撤销本补丁集的全部修改并标记为 failed。
        with patch_set as context:
            attempt.module, attempt.path, attempt.sha256 = execute()
            stage = "setup"
            setup = getattr(attempt.module, "setup", None)
            if not callable(setup):
                raise PatchLoaderError("missing_setup", f"patch module {module_name!r} does not define setup(ctx)")
            setup(context)
    except BaseException as exc:
        if private:
            _drop_private_module(module_name, attempt.module)
        if not isinstance(exc, Exception):
            raise
        code = exc.code if isinstance(exc, PatchLoaderError) else f"{stage}_failed"
        attempt.error = _error_info(code, stage, exc)
    return attempt


def _exec_file_module(module_name: str, path: str, data: bytes) -> ModuleType:
    _ensure_dynamic_package()
    loader = _FreshSourceLoader(module_name, path, data)
    # Python 3.15 的 typeshed 中 LoaderProtocol 仍要求 load_module, 而 SourceFileLoader 已移除该方法。
    spec = importlib.util.spec_from_file_location(module_name, path, loader=cast(Any, loader))
    if spec is None or spec.loader is None:
        raise PatchLoaderError("import_failed", f"cannot create a module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        _drop_private_module(module_name, module)
        raise
    return module


def _ensure_dynamic_package() -> None:
    if DYNAMIC_PACKAGE in sys.modules:
        return
    spec = importlib.machinery.ModuleSpec(DYNAMIC_PACKAGE, None, is_package=True)
    package = importlib.util.module_from_spec(spec)
    package.__doc__ = "hotpatcher 运行时按文件加载的补丁模块所在的私有命名空间包。"
    sys.modules.setdefault(DYNAMIC_PACKAGE, package)


def _drop_private_module(module_name: str, module: ModuleType | None) -> None:
    current = sys.modules.get(module_name)
    if current is not None and (module is None or current is module):
        del sys.modules[module_name]


def _module_file_hash(module: ModuleType) -> tuple[str | None, str | None]:
    path = getattr(module, "__file__", None)
    if not isinstance(path, str) or not path.endswith(".py"):
        return None, None
    try:
        return path, _sha256_file(path)
    except OSError:
        return path, None


def _sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _restore_module(module_name: str, module: ModuleType, snapshot: dict[str, Any]) -> None:
    namespace = module.__dict__
    namespace.clear()
    namespace.update(snapshot)
    sys.modules[module_name] = module


def _reload_reserved(record: LoadedPatch, config: dict[str, Any], report: dict[str, Any], state: HotpatcherState) -> None:
    previous_set_id = record.set_id
    snapshot = dict(record.module.__dict__) if record.kind == "module" else None
    unload_report = _unload_reserved(record, state)
    report.update(name=record.name, source=record.source, kind=record.kind, previous_set_id=previous_set_id, unload=unload_report, failed_set=None, rollback_error=None)
    source = _Source(record.kind, record.source, record.path if record.kind == "file" else None)
    attempt = _attempt_new_code(source, record.name, config, state, reload_from=record.module if record.kind == "module" else None)
    if attempt.ok:
        new_record = LoadedPatch(
            name=record.name,
            source=record.source,
            kind=record.kind,
            module_name=attempt.module_name,
            path=attempt.path,
            sha256=attempt.sha256,
            loaded_at=time.time(),
            config=copy.deepcopy(config),
            origin=record.origin,
            patch_set=attempt.patch_set,
            module=_require_module(attempt),
            generation=record.generation + 1,
        )
        commit_error = _commit(new_record, state)
        if commit_error is None:
            report.update(status="reloaded", **_record_fields(new_record))
            _emit(state, "set.reloaded", {"name": record.name, "set_id": new_record.set_id, "previous_set_id": previous_set_id, "generation": new_record.generation})
            return
        error = commit_error
        _discard_record_module(new_record, state)
    else:
        error = attempt.error or {}
    if snapshot is not None:
        _restore_module(record.module_name, record.module, snapshot)
    report["error"] = error
    report["failed_set"] = _set_summary(attempt.patch_set)
    rollback = _attempt_old_code(record, state)
    rollback_error: dict[str, Any] | None = rollback.error
    if rollback.ok:
        restored = LoadedPatch(
            name=record.name,
            source=record.source,
            kind=record.kind,
            module_name=record.module_name,
            path=record.path,
            sha256=record.sha256,
            loaded_at=time.time(),
            config=copy.deepcopy(record.config),
            origin=record.origin,
            patch_set=rollback.patch_set,
            module=record.module,
            generation=record.generation,
            status="rolled_back",
            last_error=copy.deepcopy(error),
            failed_sha256=attempt.sha256 if attempt.sha256 is not None else _current_hash(record),
        )
        rollback_error = _commit(restored, state)
        if rollback_error is None:
            report.update(ok=False, status="rolled_back", **_record_fields(restored))
            _emit(state, "set.rolled_back", {"name": record.name, "set_id": restored.set_id, "previous_set_id": previous_set_id, "error": _error_brief(error)})
            return
        _discard_record_module(restored, state)
    report.update(ok=False, status="failed", rollback_error=rollback_error, set_id=rollback.patch_set.id, set=_set_summary(rollback.patch_set))
    _emit(
        state,
        "set.failed",
        {"action": "reload", "name": record.name, "set_id": rollback.patch_set.id, "previous_set_id": previous_set_id, "error": _error_brief(error), "rollback_error": _error_brief(rollback_error)},
    )


def _unload_reserved(record: LoadedPatch, state: HotpatcherState) -> dict[str, Any]:
    report = _new_report("unload", record.name)
    report.update(source=record.source, kind=record.kind, set_id=record.set_id, teardown=None, handles=[], errors=[])
    teardown = getattr(record.module, "teardown", None)
    if callable(teardown):
        context = record.patch_set.context
        try:
            with context.activate():
                teardown(context)
        except Exception as exc:
            report["teardown"] = "failed"
            report["errors"].append(_error_info("teardown_failed", "teardown", exc))
        else:
            report["teardown"] = "ok"
    set_report = record.patch_set.close()
    remove_patch_set(record.patch_set, state=state)
    if record.kind == "file":
        _drop_private_module(record.module_name, record.module)
    else:
        _remove_rebind_skip(state, record.module_name, record.set_id)
    with state.control_lock:
        if state.loaded_patches.get(record.name) is record:
            del state.loaded_patches[record.name]
    report["handles"] = [dict(item) for item in set_report.handles]
    for item in set_report.errors:
        report["errors"].append({"code": "undo_failed", "stage": "unload", "error_type": item["error_type"], "message": f"{item['label']}: {item['error_message']}", "traceback": None})
    statuses = [item["status"] for item in report["handles"] if item["status"] in _STATUS_PRIORITY]
    status = max(statuses, key=lambda item: _STATUS_PRIORITY[item]) if statuses else PatchStatus.REVERTED.value
    if report["errors"]:
        status = PatchStatus.FAILED.value
        report["ok"] = False
        report["error"] = report["errors"][0]
    report["status"] = status
    report["set"] = _set_summary(record.patch_set)
    handles = report["handles"]
    _emit(
        state,
        "set.unloaded",
        {
            "name": record.name,
            "set_id": record.set_id,
            "status": status,
            "teardown": report["teardown"],
            "handle_count": len(handles),
            "handles": [{"id": item.get("id"), "status": item.get("status")} for item in handles[:_EVENT_HANDLE_LIMIT]],
            "error": _error_brief(report["error"]),
        },
    )
    return report


def _discard_record_module(record: LoadedPatch, state: HotpatcherState) -> None:
    # 补丁集未能注册时撤销模块侧的登记: 文件补丁移除私有模块, 点分模块移除 rebind 跳过登记。
    if record.kind == "file":
        _drop_private_module(record.module_name, record.module)
    else:
        _remove_rebind_skip(state, record.module_name, record.set_id)


def _commit(record: LoadedPatch, state: HotpatcherState) -> dict[str, Any] | None:
    try:
        register_patch_set(record.patch_set, state=state)
    except ValueError as exc:
        record.patch_set.close()
        return _error_info("name_conflict", "register", exc)
    with state.control_lock:
        state.loaded_patches[record.name] = record
    return None


def _reserve_new(state: HotpatcherState, name: str) -> None:
    with state.control_lock:
        if name in state.loading_patches:
            raise PatchLoaderError("busy", f"patch {name!r} is being loaded, unloaded or reloaded")
        if name in state.loaded_patches:
            raise PatchLoaderError("already_loaded", f"patch {name!r} is already loaded as {state.loaded_patches[name].set_id!r}")
        for patch_set in state.patch_sets.values():
            if patch_set.name == name:
                raise PatchLoaderError("name_conflict", f"patch set name {name!r} is already registered as {patch_set.id!r}")
        state.loading_patches.add(name)


def _reserve_existing(state: HotpatcherState, key: str) -> LoadedPatch:
    if not isinstance(key, str) or not key:
        raise PatchLoaderError("invalid_name", f"patch key must be a non-empty string, got {key!r}")
    with state.control_lock:
        record = _lookup(state, key)
        if record is None:
            raise PatchLoaderError("not_found", f"no loaded patch named {key!r}")
        if record.name in state.loading_patches:
            raise PatchLoaderError("busy", f"patch {record.name!r} is being loaded, unloaded or reloaded")
        state.loading_patches.add(record.name)
        return record


def _release(state: HotpatcherState, name: str) -> None:
    with state.control_lock:
        state.loading_patches.discard(name)


def _lookup(state: HotpatcherState, key: str) -> LoadedPatch | None:
    for record in state.loaded_patches.values():
        if record.set_id == key:
            return record
    return state.loaded_patches.get(key)


def _add_rebind_skip(state: HotpatcherState, module_name: str, set_id: str) -> None:
    with state.control_lock:
        state.rebind_skip_modules.setdefault(module_name, set()).add(set_id)


def _remove_rebind_skip(state: HotpatcherState, module_name: str, set_id: str) -> None:
    with state.control_lock:
        owners = state.rebind_skip_modules.get(module_name)
        if owners is None:
            return
        owners.discard(set_id)
        if not owners:
            del state.rebind_skip_modules[module_name]


def _current_hash(record: LoadedPatch) -> str | None:
    if record.path is None:
        return None
    try:
        return _sha256_file(record.path)
    except OSError:
        return None


def _require_module(attempt: _Attempt) -> ModuleType:
    if attempt.module is None:
        raise RuntimeError(f"patch attempt for {attempt.module_name!r} succeeded without a module")
    return attempt.module


def _coerce_interval(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError(f"watch interval must be a positive number, got {value!r}")
    try:
        interval = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"watch interval must be a positive number, got {value!r}") from exc
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError(f"watch interval must be a positive finite number, got {value!r}")
    return interval


def _emit(state: HotpatcherState, event_type: str, payload: dict[str, Any]) -> None:
    from .events import record_event

    try:
        record_event(event_type, payload, state=state)
    except Exception:
        return


def _error_brief(error: Mapping[str, Any] | None) -> dict[str, Any] | None:
    # 事件中的错误摘要: 不含 traceback。
    if not error:
        return None
    return {"code": error.get("code"), "stage": error.get("stage"), "error_type": error.get("error_type"), "message": error.get("message")}


def _new_report(action: str, name: str | None) -> dict[str, Any]:
    return {"action": action, "name": name, "ok": True, "status": None, "set_id": None, "error": None}


def _fail(report: dict[str, Any], code: str, message: str) -> dict[str, Any]:
    report.update(ok=False, status="failed", error={"code": code, "stage": "validate", "error_type": None, "message": message, "traceback": None})
    return report


def _error_info(code: str, stage: str, error: BaseException) -> dict[str, Any]:
    outcome = PatchOutcome.failed(error, reason=code)
    return {"code": code, "stage": stage, "error_type": outcome.error_type, "message": outcome.error_message, "traceback": outcome.traceback}


def _record_fields(record: LoadedPatch) -> dict[str, Any]:
    return {
        "set_id": record.set_id,
        "source": record.source,
        "kind": record.kind,
        "module": record.module_name,
        "path": record.path,
        "sha256": record.sha256,
        "loaded_at": record.loaded_at,
        "generation": record.generation,
        "set": _set_summary(record.patch_set),
    }


def _set_summary(patch_set: PatchSet) -> dict[str, Any]:
    handles = []
    for handle in patch_set.handles:
        item: dict[str, Any] = {"id": handle.id, "kind": handle.kind, "target": handle.target, "stage": handle.stage, "status": handle.status.value}
        if handle.status is PatchStatus.FAILED:
            outcome = handle.last_outcome
            item["reason"] = outcome.reason if outcome is not None else None
            item["error_type"] = outcome.error_type if outcome is not None else None
            item["error_message"] = outcome.error_message if outcome is not None else None
        handles.append(item)
    error = patch_set.error
    return {
        "id": patch_set.id,
        "name": patch_set.name,
        "status": patch_set.status.value,
        "error": error.to_dict() if error is not None else None,
        "handles": handles,
    }


# ---------------------------------------------------------------------------
# control 功能: 配置声明的补丁集与文件监视器
# ---------------------------------------------------------------------------


def _feature_apply_control(ctx: FeatureContext, section: dict[str, Any]) -> bool:
    configured = _sync_config_patch_sets(ctx, section, reconcile=ctx.reconcile)
    watching = _sync_watcher(ctx, section, reconcile=ctx.reconcile)
    forwarding = _sync_forwarding(ctx, section)
    return configured or watching or forwarding


def _feature_update_control(ctx: FeatureContext, old_section: dict[str, Any], new_section: dict[str, Any]) -> bool:
    del old_section
    _sync_config_patch_sets(ctx, new_section, reconcile=True)
    _sync_watcher(ctx, new_section, reconcile=True)
    _sync_forwarding(ctx, new_section)
    return True


def _feature_revert_control(ctx: FeatureContext) -> str:
    state = ctx.state
    statuses: list[str] = []
    with state.control_lock:
        names = [record.name for record in state.loaded_patches.values() if record.origin == ORIGIN_CONFIG]
    for name in names:
        report = unload_patch(name, state=state)
        statuses.append(report["status"] or PatchStatus.FAILED.value)
        if not report["ok"]:
            _control_error(ctx.result, name, report["error"] or {})
    if not watch_enabled_from_env():
        stop_patch_watcher(state=state)
    _sync_forwarding(ctx, {})
    known = [status for status in statuses if status in _STATUS_PRIORITY]
    return max(known, key=lambda item: _STATUS_PRIORITY[item]) if known else PatchStatus.REVERTED.value


def _feature_control_active(ctx: FeatureContext) -> bool:
    # 只统计本功能拥有的效果: 配置声明的补丁集和监视器; 通过 API 加载的补丁不属于 control 功能。
    state = ctx.state
    with state.control_lock:
        watcher = state.patch_file_watcher
        configured = any(record.origin == ORIGIN_CONFIG for record in state.loaded_patches.values())
    event_log = state.event_log
    forwarding = event_log is not None and event_log.forward_enabled
    return configured or (watcher is not None and watcher.running) or forwarding


def _sync_config_patch_sets(ctx: FeatureContext, section: Mapping[str, Any], *, reconcile: bool) -> bool:
    state = ctx.state
    entries = section.get("patch_sets", [])
    if not isinstance(entries, list):
        _control_error(ctx.result, None, {"code": "invalid_config", "message": "control.patch_sets must be a list"})
        entries = []
    desired: set[str] = set()
    disabled: set[str] = set()
    # 仍在列表中但本次处理出错的条目: reconcile 不卸载其已加载的版本。
    protected: set[str] = set()
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        label = _entry_name(entry)
        if label is not None and label in seen:
            protected.add(label)
            _control_error(ctx.result, label, {"code": "duplicate_name", "message": f"control.patch_sets[{index}]: duplicate patch set name; entry ignored"})
            continue
        if label is not None:
            seen.add(label)
        try:
            name, enabled = _apply_patch_set_entry(ctx, entry, state)
        except Exception as exc:
            # 单个条目的错误不影响其他条目。
            if label is not None:
                protected.add(label)
            code = exc.code if isinstance(exc, PatchLoaderError) else type(exc).__name__
            _control_error(ctx.result, label, {"code": code, "message": f"control.patch_sets[{index}]: {exc}"})
            continue
        (desired if enabled else disabled).add(name)
    with state.control_lock:
        stale = [record.name for record in state.loaded_patches.values() if record.origin == ORIGIN_CONFIG and record.name not in desired | protected]
    for name in stale:
        if reconcile:
            report = unload_patch(name, state=state)
            report["feature"] = _CONTROL_FEATURE_KEY
            ctx.result.setdefault("reconciled", []).append(report)
            if not report["ok"]:
                _control_error(ctx.result, name, report["error"] or {})
        else:
            reason = "is disabled" if name in disabled else "is no longer configured"
            ctx.warn(f"patch set {name!r} {reason} but remains loaded; enable services.reconcile_disabled or unload it to remove it")
    return bool(desired)


def _entry_name(entry: Any) -> str | None:
    # 尽力得到条目的补丁名称, 即使来源无效 (例如文件暂时缺失) 也能识别对应的已加载补丁。
    if not isinstance(entry, dict):
        return None
    name = entry.get("name")
    if isinstance(name, str) and name.strip():
        return name
    source = entry.get("source")
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        return _resolve_source(source).key
    except PatchLoaderError:
        text = source.strip()
        if text.endswith(".py") or os.sep in text or (os.altsep is not None and os.altsep in text):
            return str(Path(text).expanduser().resolve())
        return text


def _apply_patch_set_entry(ctx: FeatureContext, entry: Any, state: HotpatcherState) -> tuple[str, bool]:
    if not isinstance(entry, dict):
        raise PatchLoaderError("invalid_config", f"entry must be an object, got {type(entry).__name__}")
    source = entry.get("source")
    if not isinstance(source, str) or not source.strip():
        raise PatchLoaderError("invalid_config", "entry.source must be a non-empty string")
    config = _validate_config(entry.get("config"))
    resolved = _resolve_source(source)
    name = _validate_name(entry.get("name"), resolved)
    if entry.get("enabled", True) is False:
        return name, False
    record = get_loaded_patch(name, state=state)
    report: dict[str, Any] | None = None
    if record is None:
        report = load_patch(source, name=name, config=config, state=state, origin=ORIGIN_CONFIG)
    elif record.source != resolved.key:
        unload_report = unload_patch(name, state=state)
        if not unload_report["ok"]:
            _control_error(ctx.result, name, unload_report["error"] or {})
        report = load_patch(source, name=name, config=config, state=state, origin=ORIGIN_CONFIG)
    else:
        current = _current_hash(record)
        changed = current is not None and current != record.sha256
        if changed and current == record.failed_sha256:
            ctx.warn(f"patch set {name!r} source still matches a version that failed to load; keeping the rolled-back version")
            changed = False
        if changed:
            report = reload_patch(name, config=config, state=state)
        elif record.config != config:
            report = update_patch(name, config, state=state)
    if report is not None and not report["ok"]:
        error = dict(report.get("error") or {})
        if report.get("status") == "rolled_back":
            error["message"] = f"reload failed and was rolled back: {error.get('message')}"
        _control_error(ctx.result, name, error)
    return name, True


def _sync_watcher(ctx: FeatureContext, section: Mapping[str, Any], *, reconcile: bool) -> bool:
    state = ctx.state
    watch = section.get("watch", {})
    if not isinstance(watch, Mapping):
        watch = {}
    try:
        interval = _coerce_interval(watch.get("interval", DEFAULT_WATCH_INTERVAL))
    except ValueError as exc:
        ctx.warn(f"{exc}; using {DEFAULT_WATCH_INTERVAL}")
        interval = DEFAULT_WATCH_INTERVAL
    if watch_enabled_from_env() or watch.get("enabled") is True:
        start_patch_watcher(interval=interval, state=state)
        return True
    if reconcile:
        stop_patch_watcher(state=state)
    with state.control_lock:
        watcher = state.patch_file_watcher
    return watcher is not None and watcher.running


def _sync_forwarding(ctx: FeatureContext, section: Mapping[str, Any]) -> bool:
    # control.forward_events: 只有启用或事件缓冲区已存在时才触碰它, 默认配置不会创建事件缓冲区。
    enabled = section.get("forward_events") is True
    if not enabled and ctx.state.event_log is None:
        return False
    from .events import set_event_forwarding

    set_event_forwarding(enabled, state=ctx.state)
    return enabled


def _control_error(result: dict[str, Any], name: str | None, error: Mapping[str, Any]) -> None:
    message = str(error.get("message") or "failed")
    if name is not None:
        message = f"patch set {name!r}: {message}"
    item: dict[str, Any] = {"feature": _CONTROL_FEATURE_KEY, "code": str(error.get("code") or "failed"), "message": message}
    if name is not None:
        item["patch_set"] = name
    result.setdefault("errors", []).append(item)
    if "ok" in result:
        result["ok"] = False
