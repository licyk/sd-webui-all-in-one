"""内置控制命令 (control_version 1)。

每个处理函数只做参数整理、信任边界检查和报告到 envelope 的映射, 实际工作交给 ``control`` 的其他模块。
``services`` 模块在调用时按属性解析 (``services`` 在导入时依赖 ``control.features``, 顶层导入会形成循环),
因此测试对 ``services.apply_config`` 等函数的替换立即生效。

报告到 envelope 的映射: 加载器与功能报告 ``ok`` 为 False 时一律返回错误 envelope, ``details`` 携带完整报告;
前置条件错误映射为对应的 envelope 错误码 (``busy`` / ``not_found`` / ``conflict`` / ``invalid_payload``),
其余失败 (导入失败、``setup`` 失败、回滚等) 为 ``request_failed``。
"""

from __future__ import annotations

import contextlib
import copy
import functools
import json
import sys
from collections.abc import Callable, Generator, Mapping
from typing import TYPE_CHECKING, Any

from ..runtime.protocol import PROTOCOL_VERSION
from .commands import CONTROL_VERSION, CommandContext, CommandError, CommandSpec, PayloadField
from .events import read_events
from .features import ConfigCall, NoArgCall, disable_feature, enable_feature, get_feature_registry, list_features, update_feature
from .handles import MAX_ERROR_MESSAGE_CHARS, PatchHandle, get_patch_handle, list_patch_handles
from .inspect import _client_status, _connection_settings, _legacy_connection_manager, explain, render_patched_source, status_snapshot, verify_source_patches
from .loader import RemoteLoadError, check_remote_load_allowed, get_loaded_patch, load_patch, reload_patch, unload_patch, update_patch
from .patchset import PatchSet, get_patch_set, list_patch_sets, register_patch_set, remove_patch_set
from .trace import get_trace, redact_mapping, set_trace

if TYPE_CHECKING:
    from ..state import HotpatcherState
    from .controller import HotpatchController

__all__ = [
    "DEFAULT_LIST_LIMIT",
    "FEATURE_LOCK_PREFIX",
    "LIST_MAX_BYTES",
    "MAX_LIST_LIMIT",
    "MODULE_RELOAD_SET_NAME",
    "SERVICES_COMMANDS",
    "SET_LOCK_PREFIX",
    "check_config_borne_load",
    "register_builtin_commands",
]

DEFAULT_LIST_LIMIT = 200
"""列表命令默认返回的条目数"""

MAX_LIST_LIMIT = 1000
"""列表命令允许的最大条目数"""

LIST_MAX_BYTES = 48 * 1024
"""列表命令结果条目的 JSON 字节预算, 超出时截断并设置 ``truncated``"""

MAX_PATCH_DETAIL_BYTES = 48 * 1024
"""``hotpatch.patches.get`` 的句柄详情字节预算"""

MODULE_RELOAD_SET_NAME = "hotpatch:modules"
"""``hotpatch.modules.reload`` 使用的补丁集名称"""

FEATURE_LOCK_PREFIX = "feature:"
"""功能操作锁的键前缀"""

SET_LOCK_PREFIX = "set:"
"""补丁集操作锁的键前缀"""

SERVICES_COMMANDS: tuple[str, ...] = (
    "services.catalog.get",
    "services.defaults.get",
    "services.config.current",
    "services.config.normalize",
    "services.config.load",
    "services.config.save",
    "services.config.apply",
)
"""services v1 请求类型, 作为命令注册"""

_LOADER_CODE_MAP = {
    "busy": "busy",
    "not_found": "not_found",
    "already_loaded": "conflict",
    "name_conflict": "conflict",
    "invalid_source": "invalid_payload",
    "invalid_name": "invalid_payload",
    "invalid_config": "invalid_payload",
    "invalid_origin": "invalid_payload",
}

_FEATURE_CODE_MAP = {
    "unknown_feature": "not_found",
    "not_applicable": "conflict",
    "invalid_config": "invalid_payload",
    "feature_not_enabled": "invalid_payload",
    "runtime_client_required": "conflict",
}

_CONTROL_KEY = "control"
_FEATURE_SET_PREFIX = "feature:"

Handler = Callable[["HotpatchController", CommandContext, dict[str, Any]], dict[str, Any]]


# ---------------------------------------------------------------------------
# 信任边界
# ---------------------------------------------------------------------------


def check_config_borne_load(ctx: CommandContext, control_section: Any) -> None:
    """
    检查远程请求携带的 ``control`` 配置区段是否会绕过远程加载开关 (D6)。

    只对非进程内传输生效。触发条件 (相对请求之前生效的配置 ``state.current_config``):

    - ``allow_remote_load`` 为 True 而之前不是 True;
    - ``patch_sets`` 中存在会被加载 (``enabled`` 不为 False 的对象) 且不在之前配置中的条目。

    空列表、未改变的 ``false``、与之前完全相同的条目 (例如 GUI 回传完整配置) 都不会触发。触发时按请求之前的
    配置执行 ``check_remote_load_allowed``, 因此远程请求永远不能在同一个请求中开启并使用远程加载。

    Args:
        ctx (CommandContext):
            命令上下文。
        control_section (Any):
            请求中的 ``control`` 区段, 不是 dict 时忽略。

    Raises:
        CommandError:
            开关关闭时错误码为 ``remote_load_disabled``; 旧版传输缺少 token 时为 ``forbidden``。
    """

    if not ctx.remote or not isinstance(control_section, Mapping):
        return
    previous = _current_control_section(ctx.state)
    reasons: list[str] = []
    if control_section.get("allow_remote_load") is True and previous.get("allow_remote_load") is not True:
        reasons.append("enabling control.allow_remote_load")
    new_entries = _new_patch_set_entries(control_section, previous)
    if new_entries:
        reasons.append(f"{len(new_entries)} new control.patch_sets entr{'y' if len(new_entries) == 1 else 'ies'}")
    if not reasons:
        return
    try:
        check_remote_load_allowed(state=ctx.state, transport=ctx.transport, token=ctx.token)
    except RemoteLoadError as exc:
        raise CommandError(exc.code, f"config-borne remote patch loading refused ({', '.join(reasons)}): {exc}") from exc


def _new_patch_set_entries(control_section: Any, previous: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    # 会被加载 (enabled 不为 False) 且不在请求前配置中的 patch_sets 条目。
    if not isinstance(control_section, Mapping):
        return []
    entries = control_section.get("patch_sets")
    if not isinstance(entries, list):
        return []
    known = previous.get("patch_sets")
    known = known if isinstance(known, list) else []
    return [entry for entry in entries if isinstance(entry, Mapping) and entry.get("enabled", True) is not False and entry not in known]


def reject_desktop_config_borne_load(ctx: CommandContext, control_section: Any) -> None:
    """
    桌面传输上拒绝会加载新补丁集的配置应用。

    加载补丁集会导入模块并执行 ``setup``, 在桌面 broker 唯一的工作线程上运行会阻塞心跳和事件上传,
    因此即使 ``allow_remote_load`` 已开启, 桌面 ``config.apply`` 也不能携带新的 ``control.patch_sets`` 条目。
    与请求前配置完全相同的条目不会触发。

    Args:
        ctx (CommandContext):
            命令上下文。
        control_section (Any):
            请求中的 ``control`` 区段, 不是 dict 时忽略。

    Raises:
        CommandError:
            桌面传输且存在新的补丁集条目时错误码为 ``unsupported_transport``。
    """

    if ctx.transport != "desktop":
        return
    new_entries = _new_patch_set_entries(control_section, _current_control_section(ctx.state))
    if new_entries:
        raise CommandError(
            "unsupported_transport",
            f"loading {len(new_entries)} new control.patch_sets entr{'y' if len(new_entries) == 1 else 'ies'} blocks the desktop broker worker; load patch sets in-process or over the legacy transport",
        )


def _current_control_section(state: HotpatcherState) -> dict[str, Any]:
    with state.current_config_lock:
        current = state.current_config
        section = current.get(_CONTROL_KEY) if isinstance(current, dict) else None
        return copy.deepcopy(section) if isinstance(section, dict) else {}


# ---------------------------------------------------------------------------
# 报告映射与通用工具
# ---------------------------------------------------------------------------


def _loader_result(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("ok"):
        return report
    raw_error = report.get("error")
    error: dict[str, Any] = raw_error if isinstance(raw_error, dict) else {}
    code = str(error.get("code") or "")
    message = str(error.get("message") or f"{report.get('action')} failed")
    if report.get("status") == "rolled_back":
        message = f"reload failed and was rolled back: {message}"
    raise CommandError(_LOADER_CODE_MAP.get(code, "request_failed"), message, details=report)


def _feature_result(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("ok"):
        return report
    errors = report.get("errors") or []
    first = errors[0] if errors and isinstance(errors[0], dict) else {}
    code = str(first.get("code") or "")
    message = str(first.get("message") or f"feature {report.get('action')} failed")
    raise CommandError(_FEATURE_CODE_MAP.get(code, "request_failed"), message, details=report)


def _json_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))


def _bounded_items(items: list[dict[str, Any]], limit: int, max_bytes: int = LIST_MAX_BYTES) -> tuple[list[dict[str, Any]], bool]:
    result: list[dict[str, Any]] = []
    used = 2
    for item in items[:limit]:
        size = _json_size(item) + 1
        if result and used + size > max_bytes:
            return result, True
        result.append(item)
        used += size
    return result, len(items) > len(result)


def _limit(payload: Mapping[str, Any]) -> int:
    limit = payload.get("limit", DEFAULT_LIST_LIMIT)
    if limit < 1 or limit > MAX_LIST_LIMIT:
        raise CommandError("invalid_payload", f"payload.limit must be between 1 and {MAX_LIST_LIMIT}")
    return limit


def _handle_brief(handle: PatchHandle) -> dict[str, Any]:
    outcome = handle.last_outcome
    last: dict[str, Any] | None = None
    if outcome is not None:
        last = {"kind": outcome.kind.value, "reason": outcome.reason, "error_type": outcome.error_type, "error_message": outcome.error_message, "timestamp": outcome.timestamp}
    return {
        "id": handle.id,
        "kind": handle.kind,
        "target": handle.target,
        "owner": handle.owner,
        "stage": handle.stage,
        "status": handle.status.value,
        "outcome_counts": dict(handle.outcome_counts),
        "last_outcome": last,
        "created": handle.created,
    }


def _handle_detail(handle: PatchHandle) -> dict[str, Any]:
    detail = handle.to_dict()
    outcomes = detail["outcomes"]
    # 只有最近一次结果保留 traceback, 再从最旧的结果开始丢弃直到满足字节预算。
    for outcome in outcomes[:-1]:
        outcome["traceback"] = None
    detail["outcomes_truncated"] = False
    while len(outcomes) > 1 and _json_size(detail) > MAX_PATCH_DETAIL_BYTES:
        outcomes.pop(0)
        detail["outcomes_truncated"] = True
    return detail


def _all_handles(state: HotpatcherState) -> list[PatchHandle]:
    handles: dict[str, PatchHandle] = {}
    zoo = state.monkey_zoo
    if zoo is not None:
        # 列出补丁计划会为直接追加到计划列表的条目惰性创建句柄。并发注册导致字典迭代失败时退回状态表。
        try:
            for handle in zoo.handles():
                handles[handle.id] = handle
        except RuntimeError:
            pass
    for handle in list_patch_handles(state=state):
        handles.setdefault(handle.id, handle)
    return sorted(handles.values(), key=lambda item: (item.created, item.id))


def _unwrap_reference(reference: Any) -> Any:
    while isinstance(reference, (ConfigCall, NoArgCall)):
        reference = reference.reference
    return reference


def _reference_unresolved(reference: Any) -> bool:
    reference = _unwrap_reference(reference)
    if not isinstance(reference, str):
        return False
    module_name = reference.partition(":")[0]
    return bool(module_name) and module_name not in sys.modules


def _loads_patch_sets(section: Any) -> bool:
    if not isinstance(section, Mapping):
        return False
    entries = section.get("patch_sets")
    return isinstance(entries, list) and any(isinstance(entry, Mapping) and entry.get("enabled", True) is not False for entry in entries)


def _reject_blocking_feature(ctx: CommandContext, key: str, config: dict[str, Any] | None, *, update: bool) -> None:
    # 条件阻塞: 首次解析惰性入口 (导入扩展模块) 或加载补丁集时, 桌面传输拒绝执行。
    if ctx.transport != "desktop":
        return
    spec = get_feature_registry(ctx.state).get(key)
    if spec is None:
        return
    references = [spec.apply, spec.is_active, spec.is_registered]
    if update:
        references.append(spec.update)
    reasons: list[str] = []
    if any(_reference_unresolved(reference) for reference in references if reference is not None):
        reasons.append("its entry point has not been imported yet")
    if key == _CONTROL_KEY:
        section = config if config is not None and "patch_sets" in config else _current_control_section(ctx.state)
        if _loads_patch_sets(section):
            reasons.append("it would load control.patch_sets")
    if reasons:
        raise CommandError("unsupported_transport", f"feature {key!r} cannot be changed on the desktop transport because {' and '.join(reasons)}")


@contextlib.contextmanager
def _feature_lock(controller: HotpatchController, ctx: CommandContext, key: str) -> Generator[None, None, None]:
    # 只为已注册的功能创建操作锁, 避免调用方用任意键撑大锁表; 未知键由功能函数报告 unknown_feature (not_found)。
    if get_feature_registry(ctx.state).get(key) is None:
        yield
        return
    with controller.operation_lock(FEATURE_LOCK_PREFIX + key):
        yield


def _optional_dict(payload: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    value = payload.get(key)
    return copy.deepcopy(value) if isinstance(value, dict) else None


# ---------------------------------------------------------------------------
# 元信息
# ---------------------------------------------------------------------------


def _capabilities(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del payload
    specs = controller.registry.specs()
    usable = [spec for spec in specs if spec.allows_transport(ctx.transport)]
    dispatchable = [spec for spec in usable if not (ctx.transport == "desktop" and spec.blocking)]
    dispatchable_names = {spec.name for spec in dispatchable}
    groups: set[str] = set()
    for spec in dispatchable:
        parts = spec.name.split(".")
        if parts[0] != "hotpatch":
            groups.add(parts[0])
        else:
            groups.add(parts[1] if len(parts) > 2 else "meta")
    if ctx.remote:
        # 远程传输上 hotpatch.sets.load 能否通过 D6 门禁; 进程内加载总是允许, 不报告该标记。
        try:
            check_remote_load_allowed(state=ctx.state, transport=ctx.transport, token=ctx.token)
        except RemoteLoadError:
            pass
        else:
            groups.add("remote_load")
    return {
        "control_version": CONTROL_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "transport": ctx.transport,
        "commands": sorted(dispatchable_names),
        "aliases": {alias: name for alias, name in controller.registry.aliases().items() if name in dispatchable_names},
        "features": sorted(groups),
        "blocking_commands": sorted(spec.name for spec in usable if spec.blocking),
        "conditional_blocking_commands": sorted(spec.name for spec in usable if spec.conditional_blocking),
        "mutating_commands": sorted(spec.name for spec in usable if spec.mutating),
        "token_required_commands": sorted(spec.name for spec in usable if spec.requires_token),
    }


def _status(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller, payload
    return status_snapshot(state=ctx.state)


# ---------------------------------------------------------------------------
# 补丁句柄
# ---------------------------------------------------------------------------


def _patches_list(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    limit = _limit(payload)
    owner = payload.get("owner")
    handles = [handle for handle in _all_handles(ctx.state) if owner is None or handle.owner == owner]
    items, truncated = _bounded_items([_handle_brief(handle) for handle in handles], limit)
    return {"patches": items, "count": len(handles), "truncated": truncated}


def _patches_get(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    handle_id = payload["id"]
    handle = get_patch_handle(handle_id, state=ctx.state)
    if handle is None:
        handle = next((item for item in _all_handles(ctx.state) if item.id == handle_id), None)
    if handle is None:
        raise CommandError("not_found", f"no patch handle {handle_id!r}")
    return {"patch": _handle_detail(handle)}


def _patches_unload(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    handle_id = payload["id"]
    zoo = ctx.state.monkey_zoo
    status = zoo.remove(handle_id) if zoo is not None else None
    if status is not None:
        return {"id": handle_id, "status": status.value}
    handle = get_patch_handle(handle_id, state=ctx.state)
    if handle is None:
        raise CommandError("not_found", f"no patch handle {handle_id!r}")
    raise CommandError("conflict", f"patch handle {handle_id!r} is a live operation of patch set {handle.owner!r}; unload the set instead")


# ---------------------------------------------------------------------------
# 补丁集
# ---------------------------------------------------------------------------


def _set_item(patch_set: PatchSet, state: HotpatcherState) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": patch_set.id,
        "name": patch_set.name,
        "status": patch_set.status.value,
        "handle_count": len(patch_set.handles),
        "created": patch_set.created,
        "kind": "manual",
        "feature": None,
        "loaded": None,
    }
    if patch_set.name.startswith(_FEATURE_SET_PREFIX):
        item["kind"] = "feature"
        item["feature"] = patch_set.name[len(_FEATURE_SET_PREFIX) :]
        return item
    record = get_loaded_patch(patch_set.id, state=state)
    if record is not None and record.patch_set is patch_set:
        item["kind"] = "loaded"
        item["loaded"] = {
            "name": record.name,
            "source": record.source,
            "kind": record.kind,
            "origin": record.origin,
            "generation": record.generation,
            "status": record.status,
            "loaded_at": record.loaded_at,
        }
    return item


def _sets_list(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    limit = _limit(payload)
    patch_sets = list_patch_sets(state=ctx.state)
    items, truncated = _bounded_items([_set_item(patch_set, ctx.state) for patch_set in patch_sets], limit)
    return {"sets": items, "count": len(patch_sets), "truncated": truncated}


def _sets_load(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    if ctx.remote:
        try:
            check_remote_load_allowed(state=ctx.state, transport=ctx.transport, token=ctx.token)
        except RemoteLoadError as exc:
            raise CommandError(exc.code, str(exc)) from exc
    source = payload["source"]
    name = payload.get("name")
    with controller.operation_lock(SET_LOCK_PREFIX + (name or source)):
        report = load_patch(source, name=name, config=_optional_dict(payload, "config"), state=ctx.state)
    return _loader_result(report)


def _sets_unload(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    key = payload["key"]
    record = get_loaded_patch(key, state=ctx.state)
    if record is not None:
        with controller.operation_lock(SET_LOCK_PREFIX + record.name):
            return _loader_result(unload_patch(key, state=ctx.state))
    patch_set = get_patch_set(key, state=ctx.state)
    if patch_set is None:
        raise CommandError("not_found", f"no patch set named {key!r}")
    if patch_set.name.startswith(_FEATURE_SET_PREFIX):
        raise CommandError("conflict", f"patch set {patch_set.name!r} belongs to a feature; use hotpatch.features.disable")
    with controller.operation_lock(SET_LOCK_PREFIX + patch_set.name):
        report = patch_set.close()
        remove_patch_set(patch_set, state=ctx.state)
    result = report.to_dict()
    result["action"] = "unload"
    if not report.ok:
        first = report.errors[0]
        raise CommandError("request_failed", f"{first.get('label')}: {first.get('error_type')}: {first.get('error_message')}", details=result)
    return result


def _existing_record_name(ctx: CommandContext, key: str) -> str:
    record = get_loaded_patch(key, state=ctx.state)
    if record is None:
        raise CommandError("not_found", f"no loaded patch named {key!r}")
    return record.name


def _sets_reload(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    key = payload["key"]
    with controller.operation_lock(SET_LOCK_PREFIX + _existing_record_name(ctx, key)):
        report = reload_patch(key, config=_optional_dict(payload, "config"), state=ctx.state)
    return _loader_result(report)


def _sets_update(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    key = payload["key"]
    with controller.operation_lock(SET_LOCK_PREFIX + _existing_record_name(ctx, key)):
        report = update_patch(key, copy.deepcopy(payload["config"]), state=ctx.state)
    return _loader_result(report)


# ---------------------------------------------------------------------------
# 功能
# ---------------------------------------------------------------------------


def _features_list(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller, payload
    return list_features(state=ctx.state)


def _features_enable(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    key = payload["key"]
    config = _optional_dict(payload, "config")
    if key == _CONTROL_KEY:
        check_config_borne_load(ctx, config)
    _reject_blocking_feature(ctx, key, config, update=False)
    with _feature_lock(controller, ctx, key):
        report = enable_feature(key, config, runtime_client=ctx.runtime_client, state=ctx.state)
    return _feature_result(report)


def _features_disable(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    key = payload["key"]
    with _feature_lock(controller, ctx, key):
        report = disable_feature(key, state=ctx.state)
    return _feature_result(report)


def _features_update(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    key = payload["key"]
    config = copy.deepcopy(payload["config"])
    if key == _CONTROL_KEY:
        check_config_borne_load(ctx, config)
    _reject_blocking_feature(ctx, key, config, update=True)
    with _feature_lock(controller, ctx, key):
        report = update_feature(key, config, runtime_client=ctx.runtime_client, state=ctx.state)
    return _feature_result(report)


# ---------------------------------------------------------------------------
# 模块
# ---------------------------------------------------------------------------


def _module_reload_set(state: HotpatcherState) -> PatchSet:
    while True:
        existing = get_patch_set(MODULE_RELOAD_SET_NAME, state=state)
        if existing is not None and not existing.closed:
            return existing
        if existing is not None:
            remove_patch_set(existing, state=state)
        try:
            return register_patch_set(PatchSet(MODULE_RELOAD_SET_NAME, transactional=False, state=state), state=state)
        except ValueError:
            continue


def _modules_reload(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    module_name = payload["module"]
    if module_name not in sys.modules:
        raise CommandError("not_found", f"module {module_name!r} is not imported")
    with controller.operation_lock("module:" + module_name):
        handle = _module_reload_set(ctx.state).context.reload_module(module_name)
    result = {"module": module_name, "status": handle.status.value, "handle": _handle_detail(handle)}
    if handle.status.value == "failed":
        outcome = handle.last_outcome
        message = outcome.error_message if outcome is not None and outcome.error_message else f"reloading {module_name!r} failed"
        raise CommandError("request_failed", str(message)[:MAX_ERROR_MESSAGE_CHARS], details=result)
    return result


# ---------------------------------------------------------------------------
# 诊断
# ---------------------------------------------------------------------------


def _inspect_call(function: Callable[..., dict[str, Any]], *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        return function(*args, **kwargs)
    except (TypeError, ValueError) as exc:
        raise CommandError("invalid_payload", str(exc)) from exc


def _inspect_explain(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    return _inspect_call(explain, payload["module"], state=ctx.state)


def _inspect_source(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    kwargs: dict[str, Any] = {"state": ctx.state}
    if payload.get("max_bytes") is not None:
        kwargs["max_bytes"] = payload["max_bytes"]
    return _inspect_call(render_patched_source, payload["module"], **kwargs)


def _inspect_verify(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    return _inspect_call(verify_source_patches, payload.get("module"), state=ctx.state)


def _trace_get(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller, payload
    return get_trace(state=ctx.state)


def _trace_set(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    file = payload.get("file")
    if file is not None and ctx.remote:
        raise CommandError("forbidden", "payload.file is only accepted in-process; remote callers cannot redirect trace output to a file")
    tags = payload.get("tags")
    if tags is not None and not isinstance(tags, (str, list)):
        raise CommandError("invalid_payload", f"payload.tags must be a string, a list of strings or null, got {type(tags).__name__}")
    try:
        if file is None:
            return set_trace(tags, state=ctx.state)
        return set_trace(tags, file=file, state=ctx.state)
    except (TypeError, ValueError) as exc:
        raise CommandError("invalid_payload", str(exc)) from exc


def _strict_set(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    from ..hook import is_strict_mode, set_strict_mode

    previous = is_strict_mode(state=ctx.state)
    set_strict_mode(payload["enabled"], state=ctx.state)
    return {"strict": is_strict_mode(state=ctx.state), "previous": previous}


def _events_read(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    since_cursor = payload["since_cursor"]
    if since_cursor < 0:
        raise CommandError("invalid_payload", "payload.since_cursor must be a non-negative integer")
    limit = payload["limit"]
    if limit < 1 or limit > MAX_LIST_LIMIT:
        raise CommandError("invalid_payload", f"payload.limit must be between 1 and {MAX_LIST_LIMIT}")
    try:
        return read_events(since_cursor, limit, max_bytes=LIST_MAX_BYTES, state=ctx.state)
    except (TypeError, ValueError) as exc:
        raise CommandError("invalid_payload", str(exc)) from exc


# ---------------------------------------------------------------------------
# 连接
# ---------------------------------------------------------------------------


def _connection_get(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller, payload
    client = ctx.state.bootstrap_runtime_client
    manager = None if ctx.transport == "desktop" else _legacy_connection_manager(ctx.state)
    if manager is None:
        result: dict[str, Any] = {
            "mode": ctx.state.bootstrap_transport_mode,
            "connected": client is not None,
            "settings": _connection_settings(client),
            "status": _client_status(client),
        }
        return redact_mapping(result)
    snapshot = manager.get()
    result = {
        "mode": ctx.state.bootstrap_transport_mode,
        "connected": snapshot.pop("connected"),
        "settings": snapshot.pop("settings"),
        "status": _client_status(client),
        "manager": snapshot,
    }
    return redact_mapping(result)


def _connection_changes(ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    # 桌面传输或桌面模式进程的连接参数归 Rust 所有, 只读。
    if ctx.transport == "desktop" or ctx.state.bootstrap_transport_mode == "desktop_broker":
        raise CommandError("unsupported_transport", "connection parameters of the desktop broker transport are owned by the desktop host and are read-only")
    unknown = sorted(key for key in payload if key not in _CONNECTION_PAYLOAD)
    if unknown:
        raise CommandError("invalid_payload", f"unknown connection fields: {', '.join(unknown)}")
    if ctx.remote and payload.get("allow_non_loopback") is True:
        raise CommandError("forbidden", "allow_non_loopback can only be enabled in-process")
    return {key: payload[key] for key in _CONNECTION_PAYLOAD if key in payload}


def _connection_manager_for(ctx: CommandContext) -> Any:
    manager = _legacy_connection_manager(ctx.state)
    if manager is None:
        raise CommandError("conflict", "no legacy runtime connection is available")
    return manager


def _connection_test(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    from ..runtime.connection import ConnectionFailedError

    changes = _connection_changes(ctx, payload)
    manager = _connection_manager_for(ctx)
    try:
        return manager.test(changes)
    except ValueError as exc:
        raise CommandError("invalid_payload", str(exc)) from exc
    except ConnectionFailedError as exc:
        raise CommandError("connection_failed", str(exc)) from exc


def _connection_update(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del controller
    from ..runtime.connection import ConnectionBusyError, ConnectionFailedError

    changes = _connection_changes(ctx, payload)
    if not changes:
        raise CommandError("invalid_payload", "no connection parameters to change")
    manager = _connection_manager_for(ctx)
    # 远程命令在响应写出之后切换 (旧版通道的 after_send); 进程内调用立即切换并报告最终结果。
    defer = None if ctx.transport == "inprocess" else ctx.after_send.append
    try:
        report = manager.update(changes, defer=defer)
    except ValueError as exc:
        raise CommandError("invalid_payload", str(exc)) from exc
    except ConnectionBusyError as exc:
        raise CommandError("busy", str(exc)) from exc
    except ConnectionFailedError as exc:
        raise CommandError("connection_failed", str(exc)) from exc
    if report.get("status") == "rolled_back":
        raise CommandError("connection_failed", f"connection switch rolled back at stage {report.get('stage')}: {report.get('error')}", details=report)
    return report


# ---------------------------------------------------------------------------
# services v1
# ---------------------------------------------------------------------------


def _services_module() -> Any:
    from .. import services

    return services


def _services_handler(function: Callable[[Any, CommandContext, dict[str, Any]], dict[str, Any]]) -> Handler:
    # 与 services v1 的异常映射一致: JSON 解码错误为 invalid_json, 其余异常由 dispatch 映射为 request_failed。
    @functools.wraps(function)
    def wrapper(controller: HotpatchController, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
        del controller
        try:
            return function(_services_module(), ctx, payload)
        except json.JSONDecodeError as exc:
            raise CommandError("invalid_json", str(exc)) from exc

    return wrapper


@_services_handler
def _services_catalog_get(services: Any, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del payload
    return {"catalog": services.get_catalog(state=ctx.state)}


@_services_handler
def _services_defaults_get(services: Any, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del payload
    return {"config": services.get_default_config(state=ctx.state)}


@_services_handler
def _services_config_current(services: Any, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del payload
    return {"config": services.get_current_config(state=ctx.state)}


@_services_handler
def _services_config_normalize(services: Any, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {"config": services.normalize_config(services._payload_config(payload), state=ctx.state)}


@_services_handler
def _services_config_load(services: Any, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    del ctx
    config = services.load_config_file(services._payload_path(payload), write_back=bool(payload.get("write_back", True)))
    return {"config": config}


@_services_handler
def _services_config_save(services: Any, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    path = services._payload_path(payload)
    raw_config = services._payload_config(payload)
    # 远程保存的配置会在下次启动时加载, 与远程应用使用同一道 D6 检查。
    check_config_borne_load(ctx, raw_config.get(_CONTROL_KEY))
    config = services.normalize_config(raw_config, state=ctx.state)
    services.save_config_file(path, config)
    return {"config": config}


@_services_handler
def _services_config_apply(services: Any, ctx: CommandContext, payload: dict[str, Any]) -> dict[str, Any]:
    config = services._payload_config(payload)
    # 必须在 apply_config 写入 current_config 之前按请求前的配置判定。
    check_config_borne_load(ctx, config.get(_CONTROL_KEY))
    reject_desktop_config_borne_load(ctx, config.get(_CONTROL_KEY))
    result = services.apply_config(config, runtime_client=ctx.runtime_client, state=ctx.state)
    return {"result": result}


# ---------------------------------------------------------------------------
# 注册
# ---------------------------------------------------------------------------

_STR_KEY = PayloadField("str", required=True, max_len=512)
_MODULE = PayloadField("str", required=True, max_len=512)
_LIMIT = PayloadField("int", default=DEFAULT_LIST_LIMIT)
_NO_DESKTOP = frozenset({"inprocess", "legacy"})
_TIMEOUT = PayloadField("float", nullable=True)
_CONNECTION_PAYLOAD: dict[str, PayloadField] = {
    "host": PayloadField("str", max_len=253, nullable=True),
    "port": PayloadField("int", nullable=True),
    "token": PayloadField("str", max_len=4096, nullable=True),
    "connect_timeout": _TIMEOUT,
    "request_timeout": _TIMEOUT,
    "event_write_timeout": _TIMEOUT,
    "reconnect": PayloadField("bool", nullable=True),
    "reconnect_initial": _TIMEOUT,
    "reconnect_max": _TIMEOUT,
    # 只能在进程内开启, 远程开启返回 forbidden。
    "allow_non_loopback": PayloadField("bool", nullable=True),
}


def _builtin_specs() -> list[tuple[str, Handler, dict[str, Any]]]:
    return [
        ("hotpatch.capabilities", _capabilities, {}),
        ("hotpatch.status", _status, {}),
        ("hotpatch.patches.list", _patches_list, {"payload": {"owner": PayloadField("str", max_len=512, nullable=True), "limit": _LIMIT}}),
        ("hotpatch.patches.get", _patches_get, {"payload": {"id": _STR_KEY}}),
        ("hotpatch.patches.unload", _patches_unload, {"payload": {"id": _STR_KEY}, "mutating": True}),
        ("hotpatch.sets.list", _sets_list, {"payload": {"limit": _LIMIT}}),
        (
            "hotpatch.sets.load",
            _sets_load,
            {
                "payload": {
                    "source": PayloadField("str", required=True, max_len=4096),
                    "name": PayloadField("str", max_len=512, nullable=True),
                    "config": PayloadField("dict", nullable=True),
                },
                "mutating": True,
                "blocking": True,
                "requires_token": True,
            },
        ),
        ("hotpatch.sets.unload", _sets_unload, {"payload": {"key": _STR_KEY}, "mutating": True}),
        ("hotpatch.sets.reload", _sets_reload, {"payload": {"key": _STR_KEY, "config": PayloadField("dict", nullable=True)}, "mutating": True, "blocking": True, "requires_token": True}),
        ("hotpatch.sets.update", _sets_update, {"payload": {"key": _STR_KEY, "config": PayloadField("dict", required=True)}, "mutating": True, "blocking": True, "requires_token": True}),
        ("hotpatch.features.list", _features_list, {}),
        ("hotpatch.features.enable", _features_enable, {"payload": {"key": _STR_KEY, "config": PayloadField("dict", nullable=True)}, "mutating": True, "conditional_blocking": True}),
        ("hotpatch.features.disable", _features_disable, {"payload": {"key": _STR_KEY}, "mutating": True}),
        ("hotpatch.features.update", _features_update, {"payload": {"key": _STR_KEY, "config": PayloadField("dict", required=True)}, "mutating": True, "conditional_blocking": True}),
        ("hotpatch.modules.reload", _modules_reload, {"payload": {"module": _MODULE}, "mutating": True, "blocking": True, "requires_token": True}),
        ("hotpatch.inspect.explain", _inspect_explain, {"payload": {"module": _MODULE}}),
        ("hotpatch.inspect.source", _inspect_source, {"payload": {"module": _MODULE, "max_bytes": PayloadField("int", nullable=True)}}),
        ("hotpatch.inspect.verify", _inspect_verify, {"payload": {"module": PayloadField("str", max_len=512, nullable=True)}}),
        ("hotpatch.debug.trace.get", _trace_get, {}),
        ("hotpatch.debug.trace.set", _trace_set, {"payload": {"tags": PayloadField("any"), "file": PayloadField("str", max_len=4096, nullable=True)}, "mutating": True}),
        ("hotpatch.debug.strict.set", _strict_set, {"payload": {"enabled": PayloadField("bool", required=True)}, "mutating": True}),
        ("hotpatch.debug.events.read", _events_read, {"payload": {"since_cursor": PayloadField("int", default=0), "limit": _LIMIT}}),
        ("hotpatch.connection.get", _connection_get, {}),
        ("hotpatch.connection.test", _connection_test, {"payload": _CONNECTION_PAYLOAD, "requires_token": True}),
        ("hotpatch.connection.update", _connection_update, {"payload": _CONNECTION_PAYLOAD, "mutating": True, "requires_token": True}),
        ("services.catalog.get", _services_catalog_get, {}),
        ("services.defaults.get", _services_defaults_get, {}),
        ("services.config.current", _services_config_current, {}),
        ("services.config.normalize", _services_config_normalize, {}),
        # 读写任意文件路径; 桌面传输此前从未开放, 只保留进程内与旧版通道。
        ("services.config.load", _services_config_load, {"mutating": True, "transports": _NO_DESKTOP}),
        ("services.config.save", _services_config_save, {"mutating": True, "transports": _NO_DESKTOP}),
        ("services.config.apply", _services_config_apply, {"mutating": True, "aliases": ("config.apply",)}),
    ]


def register_builtin_commands(controller: HotpatchController) -> None:
    """
    把内置命令注册到控制器的命令注册表, 处理函数绑定到该控制器。

    Args:
        controller (HotpatchController):
            目标控制器。
    """

    for name, handler, options in _builtin_specs():
        controller.registry.register(CommandSpec(name=name, handler=functools.partial(handler, controller), **options))
