"""补丁诊断工具: 解释、补丁后源码、预演校验与状态快照。

所有函数都返回 JSON 安全且有界的字典 (编码后低于 ``MAX_RESULT_BYTES``, 满足桌面代理单个命令结果
64 KiB 的上限), 列表超出上限时截断并设置 ``<键>_truncated``。

``render_patched_source`` 与 ``verify_source_patches`` 以 ``record_outcomes=False`` 预演源码、AST
(以及校验时的字节码) 补丁链: 只读取源文件, 从不执行目标模块, 也不会把句柄标记为已应用。
``explain`` 不会导入目标模块或写入 finder 缓存: 它绕过 hotpatcher 自己的 finder, 直接询问
``sys.meta_path`` 上的其他 finder。
"""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
import os
import sys
from typing import TYPE_CHECKING, Any

from ..state import get_default_state
from .events import get_event_log, json_safe
from .trace import REDACTED, get_trace, redact_mapping, redact_url

if TYPE_CHECKING:
    from importlib.machinery import ModuleSpec

    from ..hook import Monkey
    from ..state import HotpatcherState
    from .handles import PatchHandle, PatchOutcome

__all__ = [
    "DEFAULT_SOURCE_MAX_BYTES",
    "MAX_LIST_ITEMS",
    "MAX_RESULT_BYTES",
    "MAX_SOURCE_BYTES",
    "PACKAGE_DISTRIBUTION",
    "explain",
    "render_patched_source",
    "status_snapshot",
    "verify_source_patches",
]

MAX_RESULT_BYTES = 60 * 1024
"""诊断结果 JSON 编码后的字节上限, 低于桌面代理 64 KiB 命令结果上限"""

DEFAULT_SOURCE_MAX_BYTES = 48 * 1024
"""``render_patched_source`` 默认的源码字节上限"""

MAX_SOURCE_BYTES = 56 * 1024
"""``render_patched_source`` 允许的最大源码字节数, 调用方传入更大的值会被收紧到此值"""

MAX_LIST_ITEMS = 64
"""诊断结果中单个列表的最大条目数"""

PACKAGE_DISTRIBUTION = "sd-webui-all-in-one"
"""``status_snapshot`` 报告版本时查询的发行包名"""

_CODE_STAGES = ("source", "ast", "bytecode")
_MAX_MESSAGE_CHARS = 500


# ---------------------------------------------------------------------------
# explain
# ---------------------------------------------------------------------------


def explain(module_name: str, *, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    解释模块为什么 (没有) 被打补丁。

    检查补丁计划、别名、``sys.modules``、loader 类型与适用的补丁阶段、finder 是否安装及其相对栈隐藏器的位置、
    finder 缓存, 以及每个句柄的最近结果。不会导入模块, 也不会写入 finder 缓存。

    ``reasons`` 中的 ``code``: ``not_registered``、``alias_fallback``、``already_imported``、``imported_with_hook``、
    ``finder_not_installed``、``finder_after_stack_shadow``、``stack_shadow_conflict``、``module_not_found``、
    ``unsupported_loader``、``code_stages_unsupported``、``cached_spec``、``no_cached_spec``、``handle_failed``、
    ``handle_noop``、``handle_skipped``; ``severity`` 为 ``info`` / ``warning`` / ``error``。

    Args:
        module_name (str):
            完整模块名。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            ``module``、``registered``、``alias``、``loaded``、``loaded_via_hook``、``patched``、``loader``、``finder``、
            ``cache``、``handles`` (最多 ``MAX_LIST_ITEMS`` 个)、``reasons``。

    Raises:
        ValueError:
            模块名为空或不是字符串时抛出。
    """

    from ..hook import MonkeySourceFileLoader, PostExecLoader
    from .handles import PatchOutcomeKind, PatchStatus

    name = _validate_module_name(module_name)
    active_state = state or get_default_state()
    monkey = _monkey(active_state, name)
    zoo = active_state.monkey_zoo
    alias = zoo.aliases_fallback.get(name.casefold()) if zoo is not None else None
    registered = monkey is not None and monkey.active

    finder = active_state.import_hook_finder
    # 先读取缓存状态, 再解析 spec, 保证解释过程不改变它要报告的状态。
    cached = finder is not None and any(key.casefold() == name.casefold() for key in list(finder.cache))
    position = _finder_position(active_state, name)

    loaded = sys.modules.get(name)
    live_spec = getattr(loaded, "__spec__", None) if loaded is not None else None
    loaded_via_hook = isinstance(getattr(live_spec, "loader", None), (MonkeySourceFileLoader, PostExecLoader))
    spec, spec_error = _resolve_spec(name)
    loader = _describe_loader(spec, spec_error)
    if position["stack_shadow_matches"] and position["finder_first"] and loader["kind"] == "source" and not loaded_via_hook:
        # import hook 位于栈隐藏器之前: 它查询 spec 时拿到的是栈隐藏器的 loader, 只能按执行后阶段处理。
        loader["effective_kind"] = "post_exec"
    else:
        loader["effective_kind"] = loader["kind"]

    handles = monkey.handles() if monkey is not None else []
    reasons: list[dict[str, Any]] = []

    def add(code: str, severity: str, message: str, **extra: Any) -> None:
        item: dict[str, Any] = {"code": code, "severity": severity, "message": message}
        item.update(extra)
        reasons.append(item)

    if monkey is None and alias is None:
        add("not_registered", "error", f"no patch plan is registered for {name!r}")
    elif monkey is not None and not registered:
        add("not_registered", "error", f"the patch plan for {name!r} has no active entries")
    if alias is not None:
        add("alias_fallback", "info", f"{name!r} falls back to {alias!r} when it cannot be found")

    if loaded is not None and registered:
        pending = [handle for handle in handles if handle.status is PatchStatus.REGISTERED and not handle.outcome_counts]
        if pending:
            restart = [handle.id for handle in pending if handle.stage in (*_CODE_STAGES, "premodule")]
            add(
                "already_imported",
                "warning",
                f"{name!r} was imported before {len(pending)} patch(es) were registered; register them with apply_if_loaded=True "
                "(function, module, import-injection and output stages) or restart the process (source, ast, bytecode and premodule stages)",
                handle_ids=[handle.id for handle in pending][:MAX_LIST_ITEMS],
                restart_required=restart[:MAX_LIST_ITEMS],
            )
        if loaded_via_hook:
            add("imported_with_hook", "info", f"{name!r} was imported through the hotpatcher loader")

    if registered or alias is not None:
        if not position["installed"]:
            add("finder_not_installed", "error", "the import hook is not on sys.meta_path; call install_import_hook() or set SD_WEBUI_ALL_IN_ONE_HOTPATCHER_IMPORT_HOOK=1")
        elif position["stack_shadow_matches"] and not position["finder_first"]:
            add(
                "finder_after_stack_shadow",
                "info",
                "the stack shadower precedes the import hook on sys.meta_path and matches this module; patches still apply, but the module keeps its real filenames",
            )
        elif position["stack_shadow_matches"] and position["finder_first"] and not loaded_via_hook:
            add(
                "stack_shadow_conflict",
                "warning",
                "the import hook precedes the stack shadower and this module matches its prefixes; the hook receives the shadower's loader, "
                "so source, ast and bytecode patches are skipped (unsupported_loader); exclude the module from the shadow prefixes",
            )
        add(
            "cached_spec" if cached else "no_cached_spec",
            "info",
            "the import hook has a cached wrapped spec for this module" if cached else "the import hook has no cached spec; the next import resolves it again",
        )

    if registered:
        code_stage_handles = [handle for handle in handles if handle.stage in _CODE_STAGES]
        if loader["kind"] == "not_found":
            add("module_not_found", "error", f"no finder can locate {name!r}" + (f" ({spec_error})" if spec_error else ""))
        elif loader["kind"] == "unsupported":
            add("unsupported_loader", "error", f"loader {loader['type']} supports neither source patching nor post-exec patching")
        elif loader["effective_kind"] == "post_exec" and code_stage_handles:
            add(
                "code_stages_unsupported",
                "warning",
                f"loader {loader['type']} exposes no patchable source; {len(code_stage_handles)} source/ast/bytecode patch(es) are skipped",
                handle_ids=[handle.id for handle in code_stage_handles][:MAX_LIST_ITEMS],
            )

    for handle in handles:
        last = handle.last_outcome
        if last is None:
            continue
        if last.kind is PatchOutcomeKind.FAILED:
            add("handle_failed", "warning", f"{handle.stage} patch {handle.target} failed: {last.error_type}: {_bounded(last.error_message)}", handle_id=handle.id)
        elif last.kind is PatchOutcomeKind.NOOP:
            add("handle_noop", "warning", f"{handle.stage} patch {handle.target} changed nothing", handle_id=handle.id)
        elif last.kind is PatchOutcomeKind.SKIPPED:
            add("handle_skipped", "info", f"{handle.stage} patch {handle.target} was skipped: {last.reason}", handle_id=handle.id, reason=last.reason)

    result: dict[str, Any] = {
        "module": name,
        "registered": registered,
        "alias": alias,
        "loaded": loaded is not None,
        "loaded_via_hook": loaded_via_hook,
        "patched": any(handle.status is PatchStatus.APPLIED for handle in handles),
        "loader": loader,
        "finder": position,
        "cache": {"cached": cached},
        "handles": [_handle_summary(handle) for handle in handles[:MAX_LIST_ITEMS]],
        "handles_truncated": len(handles) > MAX_LIST_ITEMS,
        "reasons": reasons[:MAX_LIST_ITEMS],
        "reasons_truncated": len(reasons) > MAX_LIST_ITEMS,
    }
    return _fit(result, ("handles", "reasons"))


# ---------------------------------------------------------------------------
# 补丁后源码与预演校验
# ---------------------------------------------------------------------------


def render_patched_source(module_name: str, *, max_bytes: int = DEFAULT_SOURCE_MAX_BYTES, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    预演源码与 AST 补丁并用 ``ast.unparse`` 输出补丁后的源码, 不执行模块。

    字节码补丁无法以源码形式呈现, 不会执行。补丁函数的结果只出现在返回值的 ``handles`` 中,
    不会写入句柄, 也不会把句柄标记为已应用。

    Args:
        module_name (str):
            完整模块名。没有补丁计划时输出原始源码的 ``ast.unparse`` 结果。
        max_bytes (int):
            ``source`` 字段 JSON 编码后的字节上限, 收紧到 1 至 ``MAX_SOURCE_BYTES`` 之间; 超出时在行边界截断
            (单行超出时在字符边界截断)。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            ``module``、``registered``、``filename``、``source`` (失败时为 None)、``truncated``、``bytes`` (返回源码的
            JSON 编码字节数)、``total_bytes``、``max_bytes``、``handles`` (预演结果)、``error``。

    Raises:
        ValueError:
            模块名为空或不是字符串时抛出。
    """

    name = _validate_module_name(module_name)
    active_state = state or get_default_state()
    limit = max(1, min(int(max_bytes), MAX_SOURCE_BYTES))
    monkey = _monkey(active_state, name)
    result: dict[str, Any] = {
        "module": name,
        "registered": monkey is not None and monkey.active,
        "filename": None,
        "source": None,
        "truncated": False,
        "bytes": 0,
        "total_bytes": 0,
        "max_bytes": limit,
        "handles": [],
        "handles_truncated": False,
        "error": None,
    }
    run = _dry_run(name, monkey, bytecode=False)
    result["filename"] = run["filename"]
    result["handles"] = run["outcomes"][:MAX_LIST_ITEMS]
    result["handles_truncated"] = len(run["outcomes"]) > MAX_LIST_ITEMS
    if run["error"] is not None:
        result["error"] = run["error"]
        return _fit(result, ("handles",))
    try:
        rendered = ast.unparse(run["tree"])
    except Exception as exc:
        result["error"] = _error("unparse_failed", "unparse", exc)
        return _fit(result, ("handles",))
    text, truncated, used, total = _truncate_json_text(rendered, limit)
    result.update(source=text, truncated=truncated, bytes=used, total_bytes=total)
    return _fit(result, ("handles",))


def verify_source_patches(module_name: str | None = None, *, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    预演源码、AST 和字节码补丁链, 报告每个句柄的结果和不起作用 (``noop``) 的补丁。

    用于在目标库升级后发现失效的 ``str.replace`` 之类补丁。只读取源文件, 不执行模块, 不修改句柄状态。

    Args:
        module_name (str | None):
            只校验该模块。为 None 时校验所有包含源码、AST 或字节码补丁的计划 (最多 ``MAX_LIST_ITEMS`` 个)。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            ``modules`` (每项含 ``module``、``ok``、``error``、``handles``、``noop``、``failed``)、``checked``、``ok``、
            ``noop_count``、``failed_count``、``modules_truncated``。

    Raises:
        ValueError:
            模块名为空或不是字符串时抛出。
    """

    active_state = state or get_default_state()
    if module_name is not None:
        names = [_validate_module_name(module_name)]
    else:
        zoo = active_state.monkey_zoo
        monkeys = list(zoo.monkeys.values()) if zoo is not None else []
        names = sorted(monkey.name for monkey in monkeys if monkey.name is not None and (monkey.source_patches or monkey.ast_patches or monkey.bytecode_patches))
    modules: list[dict[str, Any]] = []
    for name in names[:MAX_LIST_ITEMS]:
        modules.append(_verify_module(name, _monkey(active_state, name)))
    result: dict[str, Any] = {
        "modules": modules,
        "checked": len(modules),
        "ok": all(item["ok"] for item in modules),
        "noop_count": sum(len(item["noop"]) for item in modules),
        "failed_count": sum(len(item["failed"]) for item in modules),
        "modules_truncated": len(names) > MAX_LIST_ITEMS,
    }
    return _fit(result, ("modules",))


def _verify_module(name: str, monkey: Monkey | None) -> dict[str, Any]:
    item: dict[str, Any] = {"module": name, "ok": False, "error": None, "handles": [], "handles_truncated": False, "noop": [], "failed": []}
    if monkey is None:
        item["error"] = {"code": "not_registered", "stage": "verify", "error_type": None, "message": f"no patch plan is registered for {name!r}"}
        return item
    run = _dry_run(name, monkey, bytecode=True)
    by_handle = {entry["id"]: entry for entry in run["outcomes"]}
    handles: list[dict[str, Any]] = []
    for handle in [handle for stage in _CODE_STAGES for handle in monkey.handles(stage)]:
        entry = by_handle.get(handle.id)
        if entry is None:
            entry = {"id": handle.id, "stage": handle.stage, "target": handle.target, "outcome": "not_run", "reason": "dry_run_stopped" if run["error"] else None}
        handles.append(entry)
    item["handles"] = handles[:MAX_LIST_ITEMS]
    item["handles_truncated"] = len(handles) > MAX_LIST_ITEMS
    item["noop"] = [entry["id"] for entry in handles if entry["outcome"] == "noop"][:MAX_LIST_ITEMS]
    item["failed"] = [entry["id"] for entry in handles if entry["outcome"] == "failed"][:MAX_LIST_ITEMS]
    item["error"] = run["error"]
    item["ok"] = run["error"] is None and not item["noop"] and not item["failed"]
    return item


def _dry_run(name: str, monkey: Monkey | None, *, bytecode: bool) -> dict[str, Any]:
    from ..hook import collect_dry_run_outcomes

    result: dict[str, Any] = {"filename": None, "tree": None, "outcomes": [], "error": None}
    spec, spec_error = _resolve_spec(name)
    loader = _describe_loader(spec, spec_error)
    if spec is None or loader["kind"] != "source":
        code = "module_not_found" if loader["kind"] == "not_found" else "unsupported_loader"
        message = spec_error or f"{name!r} has no patchable source (loader {loader['type']})"
        result["error"] = {"code": code, "stage": "resolve", "error_type": None, "message": message}
        return result
    filename = os.fspath(getattr(spec.loader, "path"))
    result["filename"] = filename
    try:
        with open(filename, "rb") as file:
            source = importlib.util.decode_source(file.read())
    except Exception as exc:
        result["error"] = _error("source_unavailable", "read", exc)
        return result
    stage = "source"
    with collect_dry_run_outcomes() as collected:
        try:
            tree: Any
            if monkey is not None:
                source, filename = monkey.eval_source(source, filename, record_outcomes=False)
            stage = "parse"
            tree = ast.parse(source, filename, "exec")
            if monkey is not None:
                stage = "ast"
                tree = monkey.eval_ast(tree, record_outcomes=False)
            ast.fix_missing_locations(tree)
            if bytecode and monkey is not None:
                stage = "compile"
                if not isinstance(tree, ast.Module):
                    raise TypeError(f"AST patches must return an ast.Module, got {type(tree).__name__}")
                code_object = compile(tree, filename, "exec")
                stage = "bytecode"
                monkey.eval_bytecode(code_object, record_outcomes=False)
            result["tree"] = tree
        except Exception as exc:
            result["error"] = _error("dry_run_failed", stage, exc)
    result["filename"] = filename
    result["outcomes"] = [_dry_run_entry(handle, outcome) for handle, outcome in collected]
    return result


def _dry_run_entry(handle: PatchHandle, outcome: PatchOutcome) -> dict[str, Any]:
    entry: dict[str, Any] = {"id": handle.id, "stage": handle.stage, "target": handle.target, "outcome": outcome.kind.value, "reason": outcome.reason}
    if outcome.error_type is not None:
        entry["error_type"] = outcome.error_type
        entry["error_message"] = _bounded(outcome.error_message)
    return entry


# ---------------------------------------------------------------------------
# 状态快照
# ---------------------------------------------------------------------------


def status_snapshot(*, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    生成 hotpatcher 状态快照。

    包含版本、传输状态、已安装的 hook、补丁集、已加载补丁、功能摘要、严格模式与跟踪状态、事件缓冲区统计,
    以及脱敏后的连接参数 (token 和 session 标识替换为 ``***``)。不会探测功能是否生效, 因此不会导入扩展模块。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            ``version``、``pid``、``transport``、``hooks``、``sets``、``loaded_patches``、``features``、``debug``、
            ``connection``、``watcher``; 列表截断时带 ``<键>_truncated``。
    """

    import platform

    from ..hook import is_import_hook_installed
    from ..stack_shadow import is_stack_shadower_installed
    from .features import FEATURE_SET_PREFIX, get_feature_registry

    active_state = state or get_default_state()
    zoo = active_state.monkey_zoo
    finder = active_state.import_hook_finder
    client = active_state.bootstrap_runtime_client
    with active_state.control_lock:
        patch_sets = list(active_state.patch_sets.values())
        loaded_patches = list(active_state.loaded_patches.values())
        handle_count = len(active_state.patch_handles)
        watcher = active_state.patch_file_watcher
    registry = get_feature_registry(active_state)
    applied_features = sorted(patch_set.name[len(FEATURE_SET_PREFIX) :] for patch_set in patch_sets if patch_set.name.startswith(FEATURE_SET_PREFIX) and not patch_set.closed)

    result: dict[str, Any] = {
        "version": {
            "package": _package_version(),
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "pid": os.getpid(),
        "transport": {
            "mode": active_state.bootstrap_transport_mode,
            "status": _client_status(client),
            "diagnostics": json_safe(list(active_state.bootstrap_transport_diagnostics[-10:]), max_string=_MAX_MESSAGE_CHARS),
        },
        "hooks": {
            "import_hook": is_import_hook_installed(state=active_state),
            "stack_shadow": is_stack_shadower_installed(state=active_state),
            "finder_index": _meta_path_index(finder),
            "stack_shadow_index": _meta_path_index(active_state.stack_shadow_finder),
            "plans": len(zoo.monkeys) if zoo is not None else 0,
            "aliases": len(zoo.aliases_fallback) if zoo is not None else 0,
            "cached_specs": len(finder.cache) if finder is not None else 0,
            "handles": handle_count,
        },
        "sets": [
            {"id": patch_set.id, "name": patch_set.name, "status": patch_set.status.value, "handle_count": len(patch_set.handles), "created": patch_set.created}
            for patch_set in patch_sets[:MAX_LIST_ITEMS]
        ],
        "sets_truncated": len(patch_sets) > MAX_LIST_ITEMS,
        "set_count": len(patch_sets),
        "loaded_patches": [
            {
                "name": record.name,
                "set_id": record.set_id,
                "source": record.source,
                "kind": record.kind,
                "origin": record.origin,
                "status": record.status,
                "generation": record.generation,
                "loaded_at": record.loaded_at,
            }
            for record in loaded_patches[:MAX_LIST_ITEMS]
        ],
        "loaded_patches_truncated": len(loaded_patches) > MAX_LIST_ITEMS,
        "features": {"registered": registry.keys()[:MAX_LIST_ITEMS], "applied": applied_features[:MAX_LIST_ITEMS]},
        "debug": {
            "strict": bool(active_state.strict_mode),
            "trace": get_trace(state=active_state),
            "events": get_event_log(state=active_state).stats(),
        },
        "connection": _connection_settings(client),
        "watcher": _watcher_summary(watcher),
    }
    return _fit(redact_mapping(result), ("sets", "loaded_patches"))


def _package_version() -> str | None:
    # 延迟导入: importlib.metadata 会加载 email / zipfile / csv, 不应计入 bootstrap 开销。
    import importlib.metadata

    try:
        return importlib.metadata.version(PACKAGE_DISTRIBUTION)
    except Exception:
        return None


def _client_status(client: Any) -> Any:
    if client is None:
        return None
    status = getattr(client, "status", None)
    if not callable(status):
        return None
    try:
        snapshot = status()
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {_bounded(str(exc))}"}
    return redact_mapping(json_safe(snapshot, max_string=_MAX_MESSAGE_CHARS, max_items=10, max_depth=3))


def _connection_settings(client: Any) -> dict[str, Any]:
    # 连接参数由 P8 的 ConnectionManager 接管; 目前只报告 bootstrap 运行时客户端的只读参数, 敏感值全部脱敏。
    if client is None:
        return {"transport": None, "editable": False}
    settings = getattr(client, "settings", None)
    if settings is not None and hasattr(settings, "broker_url"):
        return {
            "transport": "desktop_broker",
            "editable": False,
            "broker_url": redact_url(getattr(settings, "broker_url", None)),
            "runtime_identity": getattr(settings, "runtime_identity", None),
            "protocol_version": getattr(settings, "protocol_version", None),
            "session_id": REDACTED if getattr(settings, "session_id", None) else None,
            "session_token": REDACTED if getattr(settings, "session_token", None) else None,
        }
    if hasattr(client, "transport") and hasattr(client, "host"):
        try:
            token = client.token
            host, port = client.host, client.port
        except Exception:
            token, host, port = None, None, None
        return {"transport": "legacy", "editable": False, "host": json_safe(host), "port": json_safe(port), "token": REDACTED if token else "", "token_set": bool(token)}
    return {"transport": type(client).__name__, "editable": False}


def _watcher_summary(watcher: Any) -> dict[str, Any] | None:
    if watcher is None:
        return None
    return {
        "running": bool(watcher.running),
        "interval": watcher.interval,
        "debounce": watcher.debounce,
        "reload_count": watcher.reload_count,
        "failure_count": len(watcher.failures),
    }


# ---------------------------------------------------------------------------
# 公共工具
# ---------------------------------------------------------------------------


def _validate_module_name(module_name: Any) -> str:
    if not isinstance(module_name, str) or not module_name.strip():
        raise ValueError(f"module name must be a non-empty string, got {module_name!r}")
    return module_name.strip()


def _monkey(state: HotpatcherState, name: str) -> Monkey | None:
    zoo = state.monkey_zoo
    return zoo[name] if zoo is not None else None


def _meta_path_index(finder: Any) -> int | None:
    if finder is None:
        return None
    for index, item in enumerate(list(sys.meta_path)):
        if item is finder:
            return index
    return None


def _finder_position(state: HotpatcherState, name: str) -> dict[str, Any]:
    from ..stack_shadow import _matches_prefix

    finder_index = _meta_path_index(state.import_hook_finder)
    shadow = state.stack_shadow_finder
    shadow_index = _meta_path_index(shadow)
    # 栈隐藏器只在 include_source_loaders 为 True 时包装普通源码 loader, 否则不会与 import hook 冲突。
    matches = shadow is not None and shadow_index is not None and shadow.include_source_loaders and _matches_prefix(name, shadow.prefixes)
    return {
        "installed": finder_index is not None,
        "index": finder_index,
        "stack_shadow_index": shadow_index,
        "stack_shadow_matches": matches,
        "finder_first": finder_index is not None and (shadow_index is None or finder_index < shadow_index),
    }


def _resolve_spec(name: str) -> tuple[ModuleSpec | None, str | None]:
    # 返回已解包 loader 的 spec 副本; 已导入模块使用其 __spec__, 否则绕过 hotpatcher finder 查找, 不导入任何模块。
    from ..hook import _unwrap_loader

    loaded = sys.modules.get(name)
    spec: ModuleSpec | None = None
    if loaded is not None:
        spec = getattr(loaded, "__spec__", None)
    if spec is None:
        try:
            spec = _find_spec_without_import(name, 0)
        except Exception as exc:
            return None, f"{type(exc).__name__}: {_bounded(str(exc))}"
    if spec is None:
        return None, None
    spec = copy.copy(spec)
    spec.loader = _unwrap_loader(spec.loader)
    return spec, None


def _find_spec_without_import(name: str, depth: int) -> ModuleSpec | None:
    from ..hook import HookedMetaPathFinder
    from ..stack_shadow import StackShadowFinder

    if depth > 32:
        return None
    parent = name.rpartition(".")[0]
    path: Any = None
    if parent:
        parent_module = sys.modules.get(parent)
        if parent_module is not None:
            path = getattr(parent_module, "__path__", None)
        else:
            parent_spec = _find_spec_without_import(parent, depth + 1)
            path = parent_spec.submodule_search_locations if parent_spec is not None else None
        if path is None:
            return None
    for finder in list(sys.meta_path):
        if isinstance(finder, (HookedMetaPathFinder, StackShadowFinder)):
            continue
        find_spec = getattr(finder, "find_spec", None)
        if find_spec is None:
            continue
        try:
            spec = find_spec(name, path)
        except Exception:
            # 第三方 finder 的异常只说明它不负责该模块, 继续询问下一个 finder。
            spec = None
        if spec is not None:
            return spec
    return None


def _describe_loader(spec: ModuleSpec | None, spec_error: str | None) -> dict[str, Any]:
    from ..hook import _is_post_exec_spec, _is_source_file_spec

    if spec is None:
        return {"kind": "not_found", "type": None, "origin": None, "error": spec_error}
    if _is_source_file_spec(spec):
        kind = "source"
    elif _is_post_exec_spec(spec):
        kind = "post_exec"
    else:
        kind = "unsupported"
    return {"kind": kind, "type": type(spec.loader).__name__ if spec.loader is not None else None, "origin": spec.origin, "error": None}


def _handle_summary(handle: PatchHandle) -> dict[str, Any]:
    last = handle.last_outcome
    summary: dict[str, Any] = {
        "id": handle.id,
        "kind": handle.kind,
        "stage": handle.stage,
        "target": handle.target,
        "owner": handle.owner,
        "status": handle.status.value,
        "outcome_counts": dict(handle.outcome_counts),
        "last_outcome": None,
    }
    if last is not None:
        summary["last_outcome"] = {
            "kind": last.kind.value,
            "reason": last.reason,
            "error_type": last.error_type,
            "error_message": _bounded(last.error_message),
            "timestamp": last.timestamp,
        }
    return summary


def _bounded(text: str | None, limit: int = _MAX_MESSAGE_CHARS) -> str | None:
    if text is None or len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _error(code: str, stage: str, error: BaseException) -> dict[str, Any]:
    return {"code": code, "stage": stage, "error_type": type(error).__name__, "message": _bounded(str(error))}


def _json_text_bytes(text: str) -> int:
    return len(json.dumps(text, ensure_ascii=False).encode("utf-8")) - 2


def _truncate_json_text(text: str, limit: int) -> tuple[str, bool, int, int]:
    total = _json_text_bytes(text)
    if total <= limit:
        return text, False, total, total
    parts: list[str] = []
    used = 0
    for line in text.splitlines(keepends=True):
        cost = _json_text_bytes(line)
        if used + cost <= limit:
            parts.append(line)
            used += cost
            continue
        for char in line:
            cost = _json_text_bytes(char)
            if used + cost > limit:
                break
            parts.append(char)
            used += cost
        break
    return "".join(parts), True, used, total


def _encoded_size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _fit(result: dict[str, Any], list_keys: tuple[str, ...]) -> dict[str, Any]:
    # 编码后超过上限时, 反复把最长的可截断列表减半并设置 <键>_truncated。
    size = _encoded_size(result)
    while size > MAX_RESULT_BYTES:
        candidates = [key for key in list_keys if isinstance(result.get(key), list) and result[key]]
        if not candidates:
            break
        key = max(candidates, key=lambda item: len(result[item]))
        items = result[key]
        result[key] = items[: len(items) // 2]
        result[f"{key}_truncated"] = True
        size = _encoded_size(result)
    if size > MAX_RESULT_BYTES:
        return {key: value for key, value in result.items() if not isinstance(value, (dict, list))} | {
            "truncated": True,
            "error": {"code": "result_too_large", "message": "result exceeded the size bound"},
        }
    return result
