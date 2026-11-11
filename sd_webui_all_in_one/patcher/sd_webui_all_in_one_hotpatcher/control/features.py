"""可扩展的功能注册表。

每个 services 功能 (core / runtime / extensions 以及第三方功能) 由一个 ``FeatureSpec`` 描述:
默认配置、设置 schema、标题、禁用告警等都是普通数据; ``apply``、``is_active``、``revert``、
``update`` 等行为既可以是可调用对象, 也可以是 ``"module:callable"`` 字符串引用。字符串引用
只在调用时解析且每次调用都重新解析, 因此内置功能的数据位于核心包内, 导入
``sd_webui_all_in_one_hotpatcher.services`` 不会加载任何 ``sd_webui_all_in_one_hotpatcher_ext`` 模块,
扩展仍然在 ``apply_config`` 安装栈隐藏器之后才首次导入。

调用约定:

- ``apply(ctx, section) -> bool | None``: ``section`` 为该功能的配置区段。``optional=True`` 时
  返回假值表示跳过 (不计入 ``applied``), 否则返回值被忽略。
- ``is_active(ctx) -> bool``、``is_registered(ctx) -> bool``: 状态探测, 异常视为 False。
- ``revert(ctx) -> PatchStatus | str | None``: 撤销补丁集之外的副作用, 返回 None 视为 ``reverted``。
- ``update(ctx, old_section, new_section) -> bool``: 原地修改参数, 返回 False 时退回为禁用后重新启用。
- ``on_disabled(ctx, section) -> None``: v1 ``apply_config`` 在功能禁用 (或缺少必需的
  runtime client) 时执行的处理, 例如浏览器切换到 passthrough、卸载错误捕获。
- ``enabled(section) -> bool``: 区段是否启用。

只接收区段配置或不接收参数的扩展入口 (例如 ``apply_from_config(config)``、
``is_uv_patch_installed()``) 通过 ``ConfigCall`` / ``NoArgCall`` 适配。

每个功能在自己的补丁集 ``feature:<key>`` 中应用, 补丁集注册在 ``state.patch_sets``。应用期间
补丁集处于激活状态, 普通 ``monkey_zoo(...)`` / ``register_hook(...)`` 注册经由
``current_patch_context()`` 归属到该补丁集, 因此未修改的扩展代码也能被 ``disable_feature`` 撤销。
"""

from __future__ import annotations

import copy
import importlib
import itertools
import logging
import re
import threading
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ..runtime.errors import DEFAULT_CAUGHT_EXCLUDE_MODULE_PREFIXES
from ..runtime.logs import (
    DEFAULT_FD_CAPTURE,
    DEFAULT_HOOK_CHECK_INTERVAL,
    DEFAULT_HOOK_POLICY,
    DEFAULT_LOGGER_EXCLUDE,
    DEFAULT_MAX_CHARS,
    DEFAULT_QUEUE_SIZE,
    DEFAULT_STREAMS,
)
from ..stack_shadow import DEFAULT_FILENAME_TEMPLATE
from ..state import HotpatcherState, get_default_state

if TYPE_CHECKING:
    from .handles import PatchHandle
    from .patchset import PatchSet

__all__ = [
    "BUILTIN_FEATURES",
    "DEFAULT_FEATURE_ORDER",
    "FEATURE_SET_PREFIX",
    "ConfigCall",
    "FeatureContext",
    "FeatureReferenceError",
    "FeatureRegistry",
    "FeatureSpec",
    "NoArgCall",
    "apply_feature_configs",
    "attach_feature_state",
    "build_default_config",
    "build_setting_schema",
    "disable_feature",
    "enable_feature",
    "feature_set_name",
    "get_feature_registry",
    "get_feature_set",
    "is_lingering",
    "list_features",
    "probe",
    "resolve_reference",
    "section_for",
    "update_feature",
    "warn_disabled_but_active",
]

_LOGGER = logging.getLogger(__name__)

FeatureReference = str | Callable[..., Any]
"""``"module:callable"`` 字符串引用或可调用对象"""

DEFAULT_FEATURE_ORDER = 100
"""第三方功能默认的应用顺序, 位于全部内置功能之后"""

FEATURE_SET_PREFIX = "feature:"
"""功能补丁集名称前缀"""

_CORE_PACKAGE = __name__.rsplit(".", 2)[0]
_SERVICES_MODULE = f"{_CORE_PACKAGE}.services"
_LOADER_MODULE = f"{_CORE_PACKAGE}.control.loader"
_EXT_PACKAGE = "sd_webui_all_in_one_hotpatcher_ext"
_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")
_STATUS_PRIORITY = {
    "not_applied": 0,
    "deregistered": 1,
    "reverted": 2,
    "requires_restart": 3,
    "failed": 4,
}


class FeatureReferenceError(LookupError):
    """``"module:callable"`` 引用无法解析时抛出。"""


def resolve_reference(reference: FeatureReference) -> Callable[..., Any]:
    """
    解析功能引用。

    可调用对象原样返回; 字符串必须为 ``"package.module:attr.path"`` 形式, 每次调用都会重新
    导入模块并查找属性, 不做缓存, 因此对模块属性的替换 (例如测试中的 monkeypatch) 立即生效。

    Args:
        reference (FeatureReference):
            字符串引用或可调用对象。

    Returns:
        Callable[..., Any]:
            解析得到的可调用对象。

    Raises:
        FeatureReferenceError:
            引用格式错误、模块无法导入、属性不存在或目标不可调用时抛出。
    """

    if callable(reference):
        return reference
    if not isinstance(reference, str):
        raise FeatureReferenceError(f"feature reference must be a 'module:callable' string or a callable, got {type(reference).__name__}")
    module_name, separator, attribute_path = reference.partition(":")
    if not separator or not module_name or not attribute_path:
        raise FeatureReferenceError(f"invalid feature reference {reference!r}: expected 'package.module:callable'")
    try:
        target: Any = importlib.import_module(module_name)
    except Exception as exc:
        raise FeatureReferenceError(f"cannot resolve feature reference {reference!r}: module {module_name!r} could not be imported: {type(exc).__name__}: {exc}") from exc
    for part in attribute_path.split("."):
        try:
            target = getattr(target, part)
        except AttributeError as exc:
            raise FeatureReferenceError(f"cannot resolve feature reference {reference!r}: attribute {part!r} not found") from exc
    if not callable(target):
        raise FeatureReferenceError(f"cannot resolve feature reference {reference!r}: {type(target).__name__} object is not callable")
    return target


@dataclass(frozen=True)
class ConfigCall:
    """
    把只接收区段配置的入口 (例如扩展的 ``apply_from_config(config)``) 适配为 ``apply(ctx, section)``。

    Attributes:
        reference (FeatureReference):
            入口的 ``"module:callable"`` 引用或可调用对象, 调用时才解析。
    """

    reference: FeatureReference

    def __call__(self, ctx: FeatureContext, section: dict[str, Any]) -> Any:
        """
        解析引用并以区段配置调用。

        Args:
            ctx (FeatureContext):
                功能上下文, 不传给目标。
            section (dict[str, Any]):
                功能配置区段。

        Returns:
            Any:
                目标返回值。
        """

        del ctx
        return resolve_reference(self.reference)(section)


@dataclass(frozen=True)
class NoArgCall:
    """
    把无参函数 (例如 ``is_uv_patch_installed()``、``unpatch_uv_to_subprocess()``) 适配为 ``fn(ctx)``。

    Attributes:
        reference (FeatureReference):
            函数的 ``"module:callable"`` 引用或可调用对象, 调用时才解析。
    """

    reference: FeatureReference

    def __call__(self, ctx: FeatureContext) -> Any:
        """
        解析引用并无参调用。

        Args:
            ctx (FeatureContext):
                功能上下文, 不传给目标。

        Returns:
            Any:
                目标返回值。
        """

        del ctx
        return resolve_reference(self.reference)()


def _enabled_flag(section: Mapping[str, Any]) -> bool:
    return bool(section.get("enabled"))


def _any_subsection_enabled(section: Mapping[str, Any]) -> bool:
    return any(isinstance(item, dict) and bool(item.get("enabled")) for item in section.values())


def _always_enabled(section: Mapping[str, Any]) -> bool:
    del section
    return True


@dataclass(frozen=True)
class FeatureSpec:
    """
    一个 services 功能的声明。

    Attributes:
        key (str):
            目录键, 例如 ``extensions.uv_pip``; 按 ``.`` 拆分得到配置路径。
        title (str):
            目录标题。
        description (str):
            目录描述。
        defaults (Mapping[str, Any]):
            默认配置, 写入默认配置的 ``key`` 路径。
        settings (Mapping[str, Any]):
            设置 schema, 对应目录中的 ``settings``。
        apply (FeatureReference | None):
            应用入口 ``apply(ctx, section)``。为 None 表示仅有配置区段 (例如 ``services``)。
        is_active (FeatureReference | None):
            目录 ``active`` 字段的探测 ``is_active(ctx)``; 为 None 时 ``active`` 恒为 False。
        is_registered (FeatureReference | None):
            目录 ``registered`` 字段的探测; 设置后目录多出 ``registered`` 字段, 且禁用告警改用它判断。
        revert (FeatureReference | None):
            禁用时在关闭补丁集之后调用的撤销函数 ``revert(ctx)``。
        update (FeatureReference | None):
            原地修改参数 ``update(ctx, old_section, new_section) -> bool``。
        on_disabled (FeatureReference | None):
            v1 ``apply_config`` 在功能禁用或缺少必需的 runtime client 时执行的处理。
        enabled (Callable[[Mapping[str, Any]], bool]):
            区段是否启用的判断, 默认读取 ``enabled`` 字段。
        requires_runtime_client (bool):
            是否需要 runtime client; 缺少时跳过应用并告警。
        optional (bool):
            ``apply`` 返回假值时视为跳过, 不计入 ``applied``。
        disabled_warning (str | None):
            功能被禁用但仍生效时追加的告警文本。
        order (int):
            应用顺序, 相同时按注册顺序。
        config_order (int | None):
            默认配置中的排列顺序; 为 None 时使用 ``order``。目录按注册顺序排列。
    """

    key: str
    title: str
    description: str
    defaults: Mapping[str, Any] = field(default_factory=dict)
    settings: Mapping[str, Any] = field(default_factory=dict)
    apply: FeatureReference | None = None
    is_active: FeatureReference | None = None
    is_registered: FeatureReference | None = None
    revert: FeatureReference | None = None
    update: FeatureReference | None = None
    on_disabled: FeatureReference | None = None
    enabled: Callable[[Mapping[str, Any]], bool] = _enabled_flag
    requires_runtime_client: bool = False
    optional: bool = False
    disabled_warning: str | None = None
    order: int = DEFAULT_FEATURE_ORDER
    config_order: int | None = None

    def __post_init__(self) -> None:
        """
        校验字段。

        Raises:
            ValueError:
                ``key`` 不是以 ``.`` 分隔的标识符, 或 ``defaults`` / ``settings`` 不是映射时抛出。
            TypeError:
                ``enabled`` 不可调用时抛出。
        """

        if not isinstance(self.key, str) or not _KEY_PATTERN.match(self.key):
            raise ValueError(f"feature key must be dot-separated identifiers, got {self.key!r}")
        if not isinstance(self.defaults, Mapping):
            raise ValueError(f"feature {self.key!r} defaults must be a mapping")
        if not isinstance(self.settings, Mapping):
            raise ValueError(f"feature {self.key!r} settings must be a mapping")
        if not callable(self.enabled):
            raise TypeError(f"feature {self.key!r} enabled must be callable")

    @property
    def path(self) -> tuple[str, ...]:
        """
        配置路径。

        Returns:
            tuple[str, ...]:
                ``key`` 按 ``.`` 拆分的路径。
        """

        return tuple(self.key.split("."))

    @property
    def name(self) -> str:
        """
        功能短名称。

        Returns:
            str:
                配置路径的最后一段。
        """

        return self.path[-1]

    @property
    def effective_config_order(self) -> int:
        """
        默认配置排列顺序。

        Returns:
            int:
                ``config_order``, 未设置时为 ``order``。
        """

        return self.order if self.config_order is None else self.config_order


@dataclass
class FeatureContext:
    """
    传给功能行为函数的上下文。

    Attributes:
        spec (FeatureSpec):
            功能声明。
        state (HotpatcherState):
            状态对象。
        runtime_client (Any):
            运行时客户端, 可能为 None。
        patch_set (PatchSet | None):
            功能补丁集; 仅做状态探测时可能为 None。
        result (dict[str, Any]):
            结果对象, 含 ``applied``、``warnings``、``errors`` 列表。
        config (dict[str, Any] | None):
            完整配置, 来自 ``apply_config`` 时可用。
        reconcile (bool):
            本次 ``apply_config`` 是否启用 reconcile (撤销不再需要的效果), 由功能自行决定如何使用。
    """

    spec: FeatureSpec
    state: HotpatcherState
    runtime_client: Any = None
    patch_set: PatchSet | None = None
    result: dict[str, Any] = field(default_factory=lambda: _new_result())
    config: dict[str, Any] | None = None
    reconcile: bool = False

    @property
    def key(self) -> str:
        """
        功能键。

        Returns:
            str:
                ``spec.key``。
        """

        return self.spec.key

    def warn(self, message: str) -> None:
        """
        追加一条属于本功能的告警。

        Args:
            message (str):
                告警文本。
        """

        self.result.setdefault("warnings", []).append({"feature": self.spec.key, "message": message})


class FeatureRegistry:
    """
    功能注册表。

    迭代顺序为 ``order`` 升序, 相同时按注册顺序; 目录使用注册顺序 (``catalog_specs``);
    默认配置使用 ``config_order`` (``config_specs``)。所有方法线程安全, 锁内不执行功能代码。
    """

    def __init__(self, specs: tuple[FeatureSpec, ...] | list[FeatureSpec] = ()) -> None:
        """
        创建注册表。

        Args:
            specs (tuple[FeatureSpec, ...] | list[FeatureSpec]):
                初始功能, 按给定顺序注册。
        """

        self._lock = threading.RLock()
        self._specs: dict[str, FeatureSpec] = {}
        self._sequence: dict[str, int] = {}
        self._counter = itertools.count()
        for spec in specs:
            self.register(spec)

    def register(self, spec: FeatureSpec, *, replace: bool = False) -> FeatureSpec:
        """
        注册功能。

        Args:
            spec (FeatureSpec):
                功能声明。
            replace (bool):
                为 True 时替换同键功能并保留其注册位置。

        Returns:
            FeatureSpec:
                同一个功能声明。

        Raises:
            TypeError:
                ``spec`` 不是 ``FeatureSpec`` 时抛出。
            ValueError:
                同键功能已存在且 ``replace`` 为 False, 或配置路径与其他功能互为前缀时抛出。
        """

        if not isinstance(spec, FeatureSpec):
            raise TypeError(f"expected FeatureSpec, got {type(spec).__name__}")
        with self._lock:
            if spec.key in self._specs:
                if not replace:
                    raise ValueError(f"feature {spec.key!r} is already registered")
            else:
                for existing in self._specs.values():
                    shorter, longer = sorted((existing.path, spec.path), key=len)
                    if longer[: len(shorter)] == shorter:
                        raise ValueError(f"feature {spec.key!r} conflicts with registered feature {existing.key!r}: config paths overlap")
                self._sequence[spec.key] = next(self._counter)
            self._specs[spec.key] = spec
        return spec

    def unregister(self, key: str) -> FeatureSpec | None:
        """
        注销功能。不会撤销已应用的补丁, 需要时先调用 ``disable_feature``。

        Args:
            key (str):
                功能键。

        Returns:
            FeatureSpec | None:
                被注销的功能, 不存在时为 None。
        """

        with self._lock:
            self._sequence.pop(key, None)
            return self._specs.pop(key, None)

    def get(self, key: str) -> FeatureSpec | None:
        """
        查询功能。

        Args:
            key (str):
                功能键。

        Returns:
            FeatureSpec | None:
                功能声明, 不存在时为 None。
        """

        with self._lock:
            return self._specs.get(key)

    def keys(self) -> list[str]:
        """
        按迭代顺序列出功能键。

        Returns:
            list[str]:
                功能键列表。
        """

        return [spec.key for spec in self]

    def catalog_specs(self) -> list[FeatureSpec]:
        """
        按注册顺序列出功能, 用于目录。

        Returns:
            list[FeatureSpec]:
                功能列表。
        """

        with self._lock:
            return sorted(self._specs.values(), key=lambda spec: self._sequence[spec.key])

    def config_specs(self) -> list[FeatureSpec]:
        """
        按默认配置顺序列出功能。

        Returns:
            list[FeatureSpec]:
                功能列表。
        """

        with self._lock:
            return sorted(self._specs.values(), key=lambda spec: (spec.effective_config_order, self._sequence[spec.key]))

    def __iter__(self) -> Iterator[FeatureSpec]:
        """
        按应用顺序迭代功能快照。

        Returns:
            Iterator[FeatureSpec]:
                功能迭代器。
        """

        with self._lock:
            ordered = sorted(self._specs.values(), key=lambda spec: (spec.order, self._sequence[spec.key]))
        return iter(ordered)

    def __len__(self) -> int:
        """
        功能数量。

        Returns:
            int:
                已注册功能数。
        """

        with self._lock:
            return len(self._specs)

    def __contains__(self, key: object) -> bool:
        """
        判断功能是否已注册。

        Args:
            key (object):
                功能键。

        Returns:
            bool:
                已注册时返回 True。
        """

        with self._lock:
            return key in self._specs


def get_feature_registry(state: HotpatcherState | None = None) -> FeatureRegistry:
    """
    获取状态对象的功能注册表, 首次访问时创建并注册内置功能。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        FeatureRegistry:
            功能注册表。
    """

    active_state = state or get_default_state()
    registry = active_state.feature_registry
    if registry is not None:
        return registry
    with active_state.control_lock:
        if active_state.feature_registry is None:
            active_state.feature_registry = FeatureRegistry(BUILTIN_FEATURES)
        return active_state.feature_registry


def build_default_config(specs: FeatureRegistry | tuple[FeatureSpec, ...] | list[FeatureSpec]) -> dict[str, Any]:
    """
    由功能声明生成完整默认配置。

    Args:
        specs (FeatureRegistry | tuple[FeatureSpec, ...] | list[FeatureSpec]):
            注册表或按配置顺序排列的功能序列。

    Returns:
        dict[str, Any]:
            新建的默认配置。
    """

    ordered = specs.config_specs() if isinstance(specs, FeatureRegistry) else sorted(specs, key=lambda spec: spec.effective_config_order)
    config: dict[str, Any] = {}
    for spec in ordered:
        node = config
        for part in spec.path[:-1]:
            node = node.setdefault(part, {})
        node[spec.path[-1]] = copy.deepcopy(dict(spec.defaults))
    return config


def build_setting_schema(specs: FeatureRegistry | tuple[FeatureSpec, ...] | list[FeatureSpec]) -> dict[str, Any]:
    """
    由功能声明生成设置 schema (目录的静态部分)。

    Args:
        specs (FeatureRegistry | tuple[FeatureSpec, ...] | list[FeatureSpec]):
            注册表或按目录顺序排列的功能序列。

    Returns:
        dict[str, Any]:
            键为功能键, 值含 ``title``、``description``、``settings``。
    """

    ordered = specs.catalog_specs() if isinstance(specs, FeatureRegistry) else list(specs)
    return {
        spec.key: {
            "title": spec.title,
            "description": spec.description,
            "settings": copy.deepcopy(dict(spec.settings)),
        }
        for spec in ordered
    }


def feature_set_name(key: str) -> str:
    """
    功能补丁集名称。

    Args:
        key (str):
            功能键。

    Returns:
        str:
            ``feature:<key>``。
    """

    return f"{FEATURE_SET_PREFIX}{key}"


def get_feature_set(key: str, *, state: HotpatcherState | None = None) -> PatchSet | None:
    """
    查询功能当前的补丁集。

    Args:
        key (str):
            功能键。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        PatchSet | None:
            已注册的 ``feature:<key>`` 补丁集, 不存在时为 None。
    """

    from .patchset import get_patch_set

    return get_patch_set(feature_set_name(key), state=state or get_default_state())


def section_for(spec: FeatureSpec, config: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    读取功能配置区段。

    Args:
        spec (FeatureSpec):
            功能声明。
        config (Mapping[str, Any] | None):
            完整配置。

    Returns:
        dict[str, Any]:
            区段; 路径不存在或不是 dict 时为空 dict。
    """

    node: Any = config if config is not None else {}
    for part in spec.path:
        node = node.get(part, {}) if isinstance(node, Mapping) else {}
    return node if isinstance(node, dict) else {}


def probe(spec: FeatureSpec, reference: FeatureReference | None, *, state: HotpatcherState) -> bool:
    """
    执行状态探测, 异常视为 False。

    Args:
        spec (FeatureSpec):
            功能声明。
        reference (FeatureReference | None):
            ``is_active`` 或 ``is_registered``。为 None 时返回 False。
        state (HotpatcherState):
            状态对象。

    Returns:
        bool:
            探测结果。
    """

    if reference is None:
        return False
    ctx = FeatureContext(spec=spec, state=state, patch_set=get_feature_set(spec.key, state=state))
    try:
        return bool(resolve_reference(reference)(ctx))
    except Exception as exc:
        _LOGGER.debug("feature %s state probe failed: %s: %s", spec.key, type(exc).__name__, exc)
        return False


def is_lingering(spec: FeatureSpec, *, state: HotpatcherState) -> bool:
    """
    判断功能禁用后是否仍有残留效果, 用于禁用告警。

    Args:
        spec (FeatureSpec):
            功能声明。
        state (HotpatcherState):
            状态对象。

    Returns:
        bool:
            ``is_registered`` (设置时) 或 ``is_active`` 为真时返回 True。
    """

    return probe(spec, spec.is_registered if spec.is_registered is not None else spec.is_active, state=state)


def apply_feature_configs(
    config: dict[str, Any],
    result: dict[str, Any],
    *,
    runtime_client: Any = None,
    state: HotpatcherState,
    reconcile: bool = False,
) -> None:
    """
    按注册表顺序应用全部功能 (``services.apply_config`` 的主体)。

    v1 语义: 启用的功能在各自补丁集中应用 (重复应用复用同一个补丁集); 禁用的功能只执行
    ``on_disabled``。``reconcile`` 为 True 时, 之前已应用、现在被禁用的功能再通过
    ``disable_feature`` 撤销, 报告写入 ``result["reconciled"]``。

    Args:
        config (dict[str, Any]):
            规范化后的完整配置。
        result (dict[str, Any]):
            结果对象, 含 ``applied``、``warnings``、``errors``。
        runtime_client (Any):
            运行时客户端。
        state (HotpatcherState):
            状态对象。
        reconcile (bool):
            是否撤销已禁用的功能。
    """

    if reconcile:
        result.setdefault("reconciled", [])
    for spec in get_feature_registry(state):
        if spec.apply is None:
            continue
        section = section_for(spec, config)
        if spec.enabled(section):
            if spec.requires_runtime_client and runtime_client is None:
                _run_on_disabled(spec, section, result, runtime_client=runtime_client, state=state, config=config)
                result["warnings"].append({"feature": spec.key, "message": f"runtime_client is required to enable {spec.name}"})
                continue
            _apply_in_feature_set(spec, section, result, runtime_client=runtime_client, state=state, config=config, reconcile=reconcile)
            continue
        _run_on_disabled(spec, section, result, runtime_client=runtime_client, state=state, config=config)
        if reconcile:
            patch_set = get_feature_set(spec.key, state=state)
            if patch_set is not None and not patch_set.closed:
                result["reconciled"].append(disable_feature(spec.key, state=state))


def warn_disabled_but_active(config: dict[str, Any], result: dict[str, Any], *, state: HotpatcherState) -> None:
    """
    为被禁用但仍生效的功能追加 ``disabled_warning`` 告警。

    Args:
        config (dict[str, Any]):
            规范化后的完整配置。
        result (dict[str, Any]):
            结果对象。
        state (HotpatcherState):
            状态对象。
    """

    for spec in get_feature_registry(state):
        if spec.disabled_warning is None or spec.enabled(section_for(spec, config)):
            continue
        if is_lingering(spec, state=state):
            result["warnings"].append({"feature": spec.key, "message": spec.disabled_warning})


def attach_feature_state(features: dict[str, Any], defaults: dict[str, Any], *, state: HotpatcherState) -> None:
    """
    为目录中的每个功能追加 ``default``、``active`` 以及可选的 ``registered`` 字段。

    Args:
        features (dict[str, Any]):
            ``build_setting_schema`` 生成的目录功能字典, 原地修改。
        defaults (dict[str, Any]):
            完整默认配置。
        state (HotpatcherState):
            状态对象。
    """

    registry = get_feature_registry(state)
    for key, feature in features.items():
        spec = registry.get(key)
        if spec is None or not isinstance(feature, dict):
            continue
        feature["default"] = section_for(spec, defaults)
        feature["active"] = probe(spec, spec.is_active, state=state)
        if spec.is_registered is not None:
            feature["registered"] = probe(spec, spec.is_registered, state=state)


def enable_feature(
    key: str,
    config: dict[str, Any] | None = None,
    *,
    runtime_client: Any = None,
    state: HotpatcherState | None = None,
) -> dict[str, Any]:
    """
    在功能补丁集中启用功能。

    ``config`` 为该功能的配置区段, 覆盖在当前配置 (``services.get_current_config``) 的区段之上并补齐默认值。
    默认值含 ``enabled`` 且 ``config`` 未显式给出时自动设为 True。已应用的功能会在同一个补丁集中重新应用。
    不修改当前配置快照。

    Args:
        key (str):
            功能键。
        config (dict[str, Any] | None):
            功能配置区段。
        runtime_client (Any):
            运行时客户端。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            JSON 安全的报告: ``key``、``action``、``ok``、``status`` (``applied`` / ``skipped`` / ``failed``)、
            ``warnings``、``errors``、``set`` (含逐句柄状态与失败原因)。
    """

    active_state = state or get_default_state()
    report = _new_report(key, "enable")
    spec = _lookup(key, report, active_state)
    if spec is None:
        return report
    section = _prepare_section(spec, config, base=_current_section(spec, active_state), force_enabled=True, report=report, state=active_state)
    if section is None:
        return report
    if not spec.enabled(section):
        return _fail(report, "feature_not_enabled", f"feature {key!r} config is not enabled")
    _enable(spec, section, report, runtime_client=runtime_client, state=active_state)
    return report


def disable_feature(key: str, *, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    禁用功能: 关闭并移除功能补丁集, 然后调用 ``spec.revert``。

    之后若功能仍处于生效状态 (``is_registered`` / ``is_active``), 状态为 ``requires_restart`` 并附带
    ``disabled_warning``。运行时功能使用已有的卸载路径 (``uninstall_error_capture``、
    ``uninstall_log_capture``、浏览器 ``passthrough``); 无法移除的效果 (例如 ``sys.addaudithook``)
    应由 ``revert`` 返回 ``requires_restart``。

    Args:
        key (str):
            功能键。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            JSON 安全的报告: ``status`` 为 ``reverted`` / ``deregistered`` / ``requires_restart`` /
            ``failed`` / ``not_applied``, ``set`` 含逐句柄状态, ``revert`` 含撤销函数结果。
    """

    active_state = state or get_default_state()
    report = _new_report(key, "disable")
    spec = _lookup(key, report, active_state)
    if spec is None:
        return report
    _disable(spec, report, state=active_state)
    return report


def update_feature(
    key: str,
    config: dict[str, Any],
    *,
    runtime_client: Any = None,
    state: HotpatcherState | None = None,
) -> dict[str, Any]:
    """
    修改已启用功能的参数。

    ``config`` 覆盖在上次应用的区段 (未应用时为当前配置的区段) 之上并补齐默认值, 校验失败时不做任何修改。
    新区段未启用时等同于 ``disable_feature``; 功能未应用时等同于 ``enable_feature``;
    提供 ``spec.update`` 且返回真值时原地修改, 否则先禁用再启用。

    Args:
        key (str):
            功能键。
        config (dict[str, Any]):
            功能配置区段 (可只含需要修改的字段)。
        runtime_client (Any):
            运行时客户端。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            JSON 安全的报告, ``mode`` 为 ``in_place`` / ``restart`` / ``enable`` / ``disable``;
            ``restart`` 时 ``disable`` / ``enable`` 字段含两个子报告。
    """

    active_state = state or get_default_state()
    report = _new_report(key, "update")
    spec = _lookup(key, report, active_state)
    if spec is None:
        return report
    if not isinstance(config, dict):
        return _fail(report, "invalid_config", "feature config must be an object")
    patch_set = get_feature_set(key, state=active_state)
    applied = patch_set is not None and not patch_set.closed
    base = copy.deepcopy(patch_set.context.config) if patch_set is not None and applied else _current_section(spec, active_state)
    section = _prepare_section(spec, config, base=base, force_enabled=False, report=report, state=active_state)
    if section is None:
        return report
    if not spec.enabled(section):
        report["mode"] = "disable"
        _disable(spec, report, state=active_state)
        return report
    if patch_set is None or not applied:
        report["mode"] = "enable"
        _enable(spec, section, report, runtime_client=runtime_client, state=active_state)
        return report
    if spec.requires_runtime_client and runtime_client is None:
        # 在任何修改之前拒绝, 保留已应用的旧状态。
        return _fail(report, "runtime_client_required", f"runtime_client is required to enable {spec.name}")
    if spec.update is not None:
        ctx = FeatureContext(spec=spec, state=active_state, runtime_client=runtime_client, patch_set=patch_set, result=report)
        before = {handle.id for handle in patch_set.handles}
        try:
            with patch_set.context.activate():
                updated = resolve_reference(spec.update)(ctx, copy.deepcopy(base), copy.deepcopy(section))
        except Exception as exc:
            _record_error(report, spec.key, type(exc).__name__, str(exc))
            report["status"] = "failed"
            report["mode"] = "in_place"
            report["set"] = _set_summary(patch_set)
            return report
        if updated:
            patch_set.context.config = copy.deepcopy(section)
            report["mode"] = "in_place"
            _record_failed_handles(report, spec.key, patch_set, before)
            report["status"] = "failed" if report["errors"] else "applied"
            report["ok"] = not report["errors"]
            report["set"] = _set_summary(patch_set)
            return report
    report["mode"] = "restart"
    disable_report = _new_report(key, "disable")
    _disable(spec, disable_report, state=active_state)
    enable_report = _new_report(key, "enable")
    _enable(spec, section, enable_report, runtime_client=runtime_client, state=active_state)
    report["disable"] = disable_report
    report["enable"] = enable_report
    report["warnings"].extend(disable_report["warnings"] + enable_report["warnings"])
    report["errors"].extend(disable_report["errors"] + enable_report["errors"])
    report["status"] = enable_report["status"]
    report["ok"] = disable_report["ok"] and enable_report["ok"]
    report["set"] = enable_report["set"]
    return report


def list_features(*, state: HotpatcherState | None = None) -> dict[str, Any]:
    """
    列出已注册功能及其运行状态。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        dict[str, Any]:
            ``{"features": [...]}``, 按应用顺序排列; 每项含 ``key``、``title``、``order``、``builtin``、
            ``applied`` (功能补丁集处于打开状态)、``active``、可选的 ``registered`` 以及 ``set`` 摘要。
    """

    active_state = state or get_default_state()
    builtin = {spec.key: spec for spec in BUILTIN_FEATURES}
    features: list[dict[str, Any]] = []
    for spec in get_feature_registry(active_state):
        patch_set = get_feature_set(spec.key, state=active_state)
        item: dict[str, Any] = {
            "key": spec.key,
            "title": spec.title,
            "order": spec.order,
            "builtin": builtin.get(spec.key) is spec,
            "configurable_only": spec.apply is None,
            "applied": patch_set is not None and not patch_set.closed,
            "active": probe(spec, spec.is_active, state=active_state),
        }
        if spec.is_registered is not None:
            item["registered"] = probe(spec, spec.is_registered, state=active_state)
        item["set"] = _set_summary(patch_set) if patch_set is not None else None
        features.append(item)
    return {"features": features}


def _new_result() -> dict[str, Any]:
    return {"applied": [], "warnings": [], "errors": []}


def _new_report(key: str, action: str) -> dict[str, Any]:
    return {"key": key, "action": action, "ok": True, "status": None, "warnings": [], "errors": [], "set": None}


def _fail(report: dict[str, Any], code: str, message: str) -> dict[str, Any]:
    _record_error(report, report["key"], code, message)
    report["status"] = "failed"
    return report


def _record_error(report: dict[str, Any], key: str, code: str, message: str) -> None:
    report["errors"].append({"feature": key, "code": code, "message": message})
    report["ok"] = False


def _lookup(key: str, report: dict[str, Any], state: HotpatcherState) -> FeatureSpec | None:
    spec = get_feature_registry(state).get(key)
    if spec is None:
        _fail(report, "unknown_feature", f"unknown feature: {key}")
        return None
    if spec.apply is None:
        _fail(report, "not_applicable", f"feature {key!r} has no apply entry point")
        return None
    return spec


def _current_section(spec: FeatureSpec, state: HotpatcherState) -> dict[str, Any]:
    with state.current_config_lock:
        current = copy.deepcopy(state.current_config) if state.current_config is not None else None
    return copy.deepcopy(section_for(spec, current)) if current is not None else copy.deepcopy(dict(spec.defaults))


def _prepare_section(
    spec: FeatureSpec,
    overrides: dict[str, Any] | None,
    *,
    base: dict[str, Any],
    force_enabled: bool,
    report: dict[str, Any],
    state: HotpatcherState,
) -> dict[str, Any] | None:
    if overrides is not None and not isinstance(overrides, dict):
        _fail(report, "invalid_config", "feature config must be an object")
        return None
    section = _deep_merge(copy.deepcopy(base), copy.deepcopy(overrides or {}))
    section = _deep_merge(section, copy.deepcopy(dict(spec.defaults)), fill_only=True)
    if force_enabled and "enabled" in spec.defaults and "enabled" not in (overrides or {}):
        section["enabled"] = True
    # 复用 services 的配置校验: 把区段放回当前配置后整体规范化。
    from ..services import get_current_config, normalize_config

    full = get_current_config(state=state)
    node = full
    for part in spec.path[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[spec.path[-1]] = section
    try:
        normalized = normalize_config(full, state=state)
    except (TypeError, ValueError) as exc:
        _fail(report, "invalid_config", str(exc))
        return None
    return section_for(spec, normalized)


def _deep_merge(target: dict[str, Any], source: Mapping[str, Any], *, fill_only: bool = False) -> dict[str, Any]:
    for key, value in source.items():
        current = target.get(key)
        if isinstance(current, dict) and isinstance(value, Mapping):
            _deep_merge(current, value, fill_only=fill_only)
        elif not fill_only or key not in target:
            target[key] = copy.deepcopy(value)
    return target


def _ensure_feature_set(spec: FeatureSpec, section: dict[str, Any], state: HotpatcherState) -> PatchSet:
    from .patchset import PatchSet, register_patch_set, remove_patch_set

    name = feature_set_name(spec.key)
    while True:
        existing = get_feature_set(spec.key, state=state)
        if existing is not None and not existing.closed:
            return existing
        if existing is not None:
            remove_patch_set(existing, state=state)
        # 非事务: 应用失败时保留已登记的补丁 (v1 语义), 也不会撤销之前成功的应用。
        patch_set = PatchSet(name, transactional=False, config=section, state=state)
        try:
            return register_patch_set(patch_set, state=state)
        except ValueError:
            # 并发创建同名补丁集, 重新读取。
            continue


def _apply_in_feature_set(
    spec: FeatureSpec,
    section: dict[str, Any],
    result: dict[str, Any],
    *,
    runtime_client: Any,
    state: HotpatcherState,
    config: dict[str, Any] | None,
    reconcile: bool = False,
) -> tuple[str, PatchSet | None]:
    try:
        patch_set = _ensure_feature_set(spec, section, state)
    except Exception as exc:
        result["errors"].append({"feature": spec.key, "code": type(exc).__name__, "message": str(exc)})
        return "failed", None
    ctx = FeatureContext(spec=spec, state=state, runtime_client=runtime_client, patch_set=patch_set, result=result, config=config, reconcile=reconcile)
    before = {handle.id for handle in patch_set.handles}
    try:
        with patch_set.context.activate():
            returned = resolve_reference(spec.apply)(ctx, section) if spec.apply is not None else None
    except Exception as exc:
        result["errors"].append({"feature": spec.key, "code": type(exc).__name__, "message": str(exc)})
        return "failed", patch_set
    patch_set.context.config = copy.deepcopy(section)
    if spec.optional and not returned:
        status = "skipped"
        if not patch_set.handles:
            # 可选功能被跳过且没有登记任何补丁: 不保留空补丁集, 功能视为未应用。
            from .patchset import remove_patch_set

            patch_set.close()
            remove_patch_set(patch_set, state=state)
            return status, None
    else:
        result["applied"].append(spec.key)
        status = "applied"
    if _record_failed_handles(result, spec.key, patch_set, before):
        status = "failed"
    return status, patch_set


def _record_failed_handles(result: dict[str, Any], key: str, patch_set: PatchSet, before: set[str]) -> bool:
    from .handles import PatchStatus

    failed = False
    for handle in patch_set.handles:
        if handle.id in before or handle.status is not PatchStatus.FAILED:
            continue
        failed = True
        outcome = handle.last_outcome
        reason = None
        if outcome is not None:
            reason = outcome.reason
            if outcome.error_type:
                reason = f"{outcome.error_type}: {outcome.error_message}" if reason is None else f"{reason}: {outcome.error_type}: {outcome.error_message}"
        result["errors"].append({"feature": key, "code": "patch_failed", "message": f"{handle.kind} {handle.target}: {reason or 'failed'}"})
        if "ok" in result:
            result["ok"] = False
    return failed


def _run_on_disabled(
    spec: FeatureSpec,
    section: dict[str, Any],
    result: dict[str, Any],
    *,
    runtime_client: Any,
    state: HotpatcherState,
    config: dict[str, Any] | None,
) -> None:
    if spec.on_disabled is None:
        return
    # 与 v1 一致: 禁用处理抛出的异常不吞掉。
    ctx = FeatureContext(spec=spec, state=state, runtime_client=runtime_client, patch_set=get_feature_set(spec.key, state=state), result=result, config=config)
    resolve_reference(spec.on_disabled)(ctx, section)


def _enable(spec: FeatureSpec, section: dict[str, Any], report: dict[str, Any], *, runtime_client: Any, state: HotpatcherState) -> None:
    if spec.requires_runtime_client and runtime_client is None:
        _fail(report, "runtime_client_required", f"runtime_client is required to enable {spec.name}")
        return
    result = _new_result()
    status, patch_set = _apply_in_feature_set(spec, section, result, runtime_client=runtime_client, state=state, config=None)
    report["warnings"].extend(result["warnings"])
    for error in result["errors"]:
        _record_error(report, error["feature"], error["code"], error["message"])
    report["status"] = status
    report["set"] = _set_summary(patch_set) if patch_set is not None else None


def _disable(spec: FeatureSpec, report: dict[str, Any], *, state: HotpatcherState) -> None:
    from .handles import PatchStatus
    from .patchset import remove_patch_set

    statuses: list[str] = []
    patch_set = get_feature_set(spec.key, state=state)
    if patch_set is not None:
        set_report = patch_set.close()
        remove_patch_set(patch_set, state=state)
        statuses.extend(item["status"] for item in set_report.handles)
        for error in set_report.errors:
            _record_error(report, spec.key, "undo_failed", f"{error['label']}: {error['error_type']}: {error['error_message']}")
        report["set"] = _set_summary(patch_set)
    if spec.revert is not None:
        ctx = FeatureContext(spec=spec, state=state, patch_set=patch_set, result=report)
        try:
            returned = resolve_reference(spec.revert)(ctx)
        except Exception as exc:
            _record_error(report, spec.key, type(exc).__name__, str(exc))
            report["revert"] = {"status": PatchStatus.FAILED.value, "error_type": type(exc).__name__, "error_message": str(exc)}
            statuses.append(PatchStatus.FAILED.value)
        else:
            revert_status = _coerce_status(returned)
            report["revert"] = {"status": revert_status}
            statuses.append(revert_status)
    # 有补丁集或调用过 revert 时, 没有残留句柄即视为已完全撤销。
    baseline = "reverted" if patch_set is not None or spec.revert is not None else "not_applied"
    status = max(statuses, key=lambda item: _STATUS_PRIORITY.get(item, 0)) if statuses else baseline
    if status not in _STATUS_PRIORITY:
        status = baseline
    if report["errors"]:
        status = "failed"
    if status != "failed" and is_lingering(spec, state=state):
        status = "requires_restart"
        report["warnings"].append({"feature": spec.key, "message": spec.disabled_warning or f"feature {spec.key} remains active; process restart is required to remove it"})
    report["status"] = status


def _coerce_status(value: Any) -> str:
    from .handles import PatchStatus

    if value is None:
        return PatchStatus.REVERTED.value
    if isinstance(value, PatchStatus):
        value = value.value
    if isinstance(value, str) and value in _STATUS_PRIORITY and value != "not_applied":
        return value
    return PatchStatus.REVERTED.value


def _set_summary(patch_set: PatchSet) -> dict[str, Any]:
    return {
        "id": patch_set.id,
        "name": patch_set.name,
        "status": patch_set.status.value,
        "handles": [_handle_summary(handle) for handle in patch_set.handles],
    }


def _handle_summary(handle: PatchHandle) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "id": handle.id,
        "kind": handle.kind,
        "target": handle.target,
        "stage": handle.stage,
        "status": handle.status.value,
    }
    if handle.status.value == "failed":
        outcome = handle.last_outcome
        summary["reason"] = outcome.reason if outcome is not None else None
        summary["error_type"] = outcome.error_type if outcome is not None else None
        summary["error_message"] = outcome.error_message if outcome is not None else None
    return summary


# ---------------------------------------------------------------------------
# 内置功能。默认值、schema、标题和告警文本均为普通数据; 行为通过字符串引用在调用时解析,
# core / runtime 功能的实现位于 services 模块 (便于沿用其模块级依赖), 扩展功能指向扩展包。
# 列表顺序即目录顺序; ``order`` 为应用顺序; ``config_order`` 仅在默认配置顺序不同于应用顺序时设置。
# ---------------------------------------------------------------------------


def _svc(name: str) -> str:
    return f"{_SERVICES_MODULE}:{name}"


def _ext(name: str) -> str:
    return f"{_EXT_PACKAGE}.{name}"


def _loader(name: str) -> str:
    return f"{_LOADER_MODULE}:{name}"


BUILTIN_FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec(
        key="services",
        title="服务控制",
        description="控制 hotpatcher services 在 bootstrap 和运行时控制通道中的行为。",
        defaults={
            "apply_on_bootstrap": True,
            "reconcile_disabled": False,
        },
        settings={
            "apply_on_bootstrap": {
                "type": "bool",
                "title": "启动时应用配置",
                "description": "bootstrap 读取配置后立即调用 services.apply_config()。",
            },
            "reconcile_disabled": {
                "type": "bool",
                "title": "撤销已禁用功能",
                "description": "应用配置时撤销之前已应用、现在被禁用的功能。关闭时保持原有行为：禁用只表示不再注册，已生效的补丁保留到进程重启。",
            },
        },
        order=0,
    ),
    FeatureSpec(
        key="core.import_hook",
        title="Import Hook",
        description="安装 import hook，让已注册的模块补丁在目标模块首次导入时生效。",
        defaults={
            "enabled": True,
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "启用 import hook。补丁必须在目标模块首次导入前注册。",
            },
        },
        apply=_svc("_feature_apply_import_hook"),
        is_active=_svc("_feature_import_hook_active"),
        disabled_warning="import hook is already installed and v1 services does not uninstall it",
        order=10,
    ),
    FeatureSpec(
        key="core.stack_shadow",
        title="栈隐藏",
        description="把补丁系统相关 traceback 文件名伪装成更友好的路径，降低用户日志噪音。",
        defaults={
            "enabled": True,
            "prefixes": [
                "sd_webui_all_in_one_hotpatcher",
                "sd_webui_all_in_one_hotpatcher_ext",
            ],
            "filename_template": DEFAULT_FILENAME_TEMPLATE,
            "include_source_loaders": True,
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "安装 traceback 栈隐藏器。",
            },
            "prefixes": {
                "type": "list[str]",
                "title": "隐藏模块前缀",
                "description": "需要隐藏的模块名前缀。GUI 中可用逗号分隔多个值。",
            },
            "filename_template": {
                "type": "str",
                "title": "文件名模板",
                "description": "伪装 traceback 文件名时使用的模板。",
            },
            "include_source_loaders": {
                "type": "bool",
                "title": "处理源码 loader",
                "description": "同时处理从源码 loader 获取的文件名。",
            },
        },
        apply=_svc("_feature_apply_stack_shadow"),
        is_active=_svc("_feature_stack_shadow_active"),
        disabled_warning="stack shadower is already installed and v1 services does not uninstall it",
        order=15,
    ),
    FeatureSpec(
        key="runtime.logs",
        title="运行时日志",
        description="把 logging、标准输出和子进程输出采集到 runtime host。",
        defaults={
            "enabled": False,
            "logging": True,
            "streams": list(DEFAULT_STREAMS),
            "subprocess": "safe",
            "policy": "bounded",
            "max_chars": DEFAULT_MAX_CHARS,
            "queue_size": DEFAULT_QUEUE_SIZE,
            "logger_include": [],
            "logger_exclude": list(DEFAULT_LOGGER_EXCLUDE),
            "hook_policy": DEFAULT_HOOK_POLICY,
            "hook_check_interval": DEFAULT_HOOK_CHECK_INTERVAL,
            "fd_capture": DEFAULT_FD_CAPTURE,
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用日志采集",
                "description": "启用 runtime 日志采集。需要 runtime client 可用。",
            },
            "logging": {
                "type": "bool",
                "title": "采集 logging",
                "description": "采集 Python logging 记录并发送 log.record。",
            },
            "streams": {
                "type": "list[str]",
                "title": "标准流",
                "description": "采集的标准流名称。GUI 中可用逗号分隔多个值。",
            },
            "subprocess": {
                "type": "choice",
                "title": "子进程采集",
                "description": "控制是否包装子进程输出。safe 仅在安全场景启用，force 强制启用。",
                "choices": ["0", "safe", "force"],
            },
            "policy": {
                "type": "choice",
                "title": "输出策略",
                "description": "bounded 会限制单条消息长度，raw 保留原始输出。",
                "choices": ["bounded", "raw"],
            },
            "max_chars": {
                "type": "int",
                "title": "最大字符数",
                "description": "bounded 策略下单条日志最多保留的字符数。",
            },
            "queue_size": {
                "type": "int",
                "title": "队列大小",
                "description": "日志发送队列的最大长度。",
            },
            "logger_include": {
                "type": "list[str]",
                "title": "包含 logger",
                "description": "只采集这些 logger 前缀。为空表示不限制。",
            },
            "logger_exclude": {
                "type": "list[str]",
                "title": "排除 logger",
                "description": "不采集这些 logger 前缀。GUI 中可用逗号分隔多个值。",
            },
            "hook_policy": {
                "type": "choice",
                "title": "Hook 冲突策略",
                "description": "控制日志 hook 被其它软件替换后的处理方式。cooperative 只协作包装，warn 仅告警，reapply 自动重新接管。",
                "choices": ["cooperative", "warn", "reapply"],
            },
            "hook_check_interval": {
                "type": "int",
                "title": "Hook 检查间隔",
                "description": "warn/reapply 策略下检查日志 hook 状态的间隔秒数。",
            },
            "fd_capture": {
                "type": "choice",
                "title": "FD 级捕获",
                "description": "实验性标准流捕获。0 关闭，fallback 在普通 stream hook 丢失时尝试启用，force 启动时直接启用。",
                "choices": ["0", "fallback", "force"],
            },
        },
        apply=_svc("_feature_apply_logs"),
        revert=_svc("_feature_revert_logs"),
        requires_runtime_client=True,
        order=30,
    ),
    FeatureSpec(
        key="runtime.browser",
        title="浏览器控制",
        description="控制标准库 webbrowser 请求是否交给 runtime host。",
        defaults={
            "enabled": False,
            "mode": "host",
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用浏览器控制",
                "description": "在 WebUI 导入前应用标准库 webbrowser 补丁。",
            },
            "mode": {
                "type": "choice",
                "title": "处理模式",
                "description": "host 发送事件并抑制系统浏览器，suppress 仅抑制，passthrough 保持标准行为。",
                "choices": ["host", "suppress", "passthrough"],
            },
        },
        apply=_svc("_feature_apply_browser"),
        is_active=_svc("_feature_browser_active"),
        is_registered=_svc("_feature_browser_registered"),
        revert=_svc("_feature_revert_browser"),
        update=_svc("_feature_update_browser"),
        on_disabled=_svc("_feature_browser_disabled"),
        disabled_warning="browser wrapper remains registered in passthrough mode; process restart is required to remove it",
        order=20,
    ),
    FeatureSpec(
        key="runtime.errors",
        title="运行时错误",
        description="捕获未处理 Python 异常并发送结构化 error.exception 事件到 runtime host。",
        defaults={
            "enabled": False,
            "sys_excepthook": True,
            "threading_excepthook": True,
            "unraisablehook": True,
            "asyncio": True,
            "include_locals": False,
            "caught_exceptions": {
                "enabled": False,
                "threading": True,
                "module_prefixes": [],
                "exclude_module_prefixes": list(DEFAULT_CAUGHT_EXCLUDE_MODULE_PREFIXES),
                "max_events_per_second": 20,
            },
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用错误捕获",
                "description": "启用未处理 Python 异常捕获。需要 runtime client 可用。",
            },
            "sys_excepthook": {
                "type": "bool",
                "title": "主线程异常",
                "description": "捕获 sys.excepthook 处理的主线程未处理异常。",
            },
            "threading_excepthook": {
                "type": "bool",
                "title": "线程异常",
                "description": "捕获 threading.excepthook 处理的线程未处理异常。",
            },
            "unraisablehook": {
                "type": "bool",
                "title": "Unraisable 异常",
                "description": "捕获 sys.unraisablehook 处理的析构、回调等不可抛出异常。",
            },
            "asyncio": {
                "type": "bool",
                "title": "Asyncio 异常",
                "description": "捕获 asyncio event loop exception handler 中的异常上下文。",
            },
            "include_locals": {
                "type": "bool",
                "title": "包含局部变量",
                "description": "在 error.exception 的 traceback frame 中附带脱敏后的局部变量 repr 摘要。",
            },
            "caught_exceptions.enabled": {
                "type": "bool",
                "title": "捕获已处理异常",
                "description": "实验性功能。使用 sys.settrace 捕获被业务代码 except 处理过的异常, 可能影响性能。",
            },
            "caught_exceptions.threading": {
                "type": "bool",
                "title": "跟踪新线程",
                "description": "为后续新建线程安装 caught exception trace 捕获。",
            },
            "caught_exceptions.module_prefixes": {
                "type": "list[str]",
                "title": "包含模块前缀",
                "description": "只捕获这些模块名前缀中的异常。为空表示不限制。",
            },
            "caught_exceptions.exclude_module_prefixes": {
                "type": "list[str]",
                "title": "排除模块前缀",
                "description": "不捕获这些模块名前缀中的异常。GUI 中可用逗号分隔多个值。",
            },
            "caught_exceptions.max_events_per_second": {
                "type": "int",
                "title": "每秒事件上限",
                "description": "caught exception 事件限流值。用于降低 sys.settrace 带来的事件噪音。",
            },
        },
        apply=_svc("_feature_apply_errors"),
        is_active=_svc("_feature_errors_active"),
        revert=_svc("_feature_revert_errors"),
        on_disabled=_svc("_feature_errors_disabled"),
        requires_runtime_client=True,
        order=25,
    ),
    FeatureSpec(
        key="extensions.zluda",
        title="ZLUDA",
        description="注册 ZLUDA 兼容性补丁和可选路径注入。",
        defaults={
            "enabled": False,
            "compat": False,
            "path": "",
            "torch_zluda_timer": False,
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "启用 ZLUDA 扩展补丁。",
            },
            "compat": {
                "type": "bool",
                "title": "兼容模式",
                "description": "注册 torch / torch.backends.cuda 的 ZLUDA 兼容性补丁。",
            },
            "path": {
                "type": "str",
                "title": "ZLUDA 路径",
                "description": "添加到动态库搜索路径的 ZLUDA 目录。为空则不注入路径。",
            },
            "torch_zluda_timer": {
                "type": "bool",
                "title": "Torch 编译热修复",
                "description": "修复 torch.utils.cpp_extension 中不兼容 ZLUDA 的 HIP_HOME 判断。",
            },
        },
        apply=ConfigCall(f"{_ext('zluda')}:apply_from_config"),
        order=45,
    ),
    FeatureSpec(
        key="extensions.comfyui_auto_port",
        title="ComfyUI 端口自动避让",
        description="ComfyUI 使用默认端口时，自动避开已经被占用的端口。",
        defaults={
            "enabled": True,
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "检测 ComfyUI 默认端口 8188，并在被占用时自动选择后续可用端口。",
            },
        },
        apply=ConfigCall(f"{_ext('comfyui_auto_port')}:apply_from_config"),
        is_active=NoArgCall(f"{_ext('comfyui_auto_port')}:is_comfyui_auto_port_patch_registered"),
        disabled_warning="ComfyUI auto-port patch remains registered; process restart is required to remove it",
        order=40,
    ),
    FeatureSpec(
        key="extensions.extension_index",
        title="扩展索引镜像",
        description="替换 WebUI / ComfyUI 扩展索引和 ComfyUI-Manager 相关 URL。",
        defaults={
            "webui": {
                "enabled": False,
                "url": "auto",
            },
            "comfyui_manager": {
                "enabled": False,
                "url": "auto",
            },
        },
        settings={
            "webui.enabled": {
                "type": "bool",
                "title": "启用 SD WebUI 镜像",
                "description": "启用 A1111 / Forge / Vladmandic 扩展索引镜像补丁。",
            },
            "webui.url": {
                "type": "str",
                "title": "SD WebUI 镜像 URL",
                "description": "用于替换 A1111 / Forge / Vladmandic 扩展索引的镜像 JSON URL；填 auto 时自动检测网络并按需使用 GitHub raw 镜像。",
            },
            "comfyui_manager.enabled": {
                "type": "bool",
                "title": "启用 ComfyUI-Manager 镜像",
                "description": "启用 ComfyUI-Manager channel 镜像补丁。",
            },
            "comfyui_manager.url": {
                "type": "str",
                "title": "ComfyUI-Manager 镜像 URL",
                "description": "用于替换 ComfyUI-Manager channel 前缀的镜像 URL；填 auto 时自动检测网络并按需使用 GitHub raw 镜像。",
            },
        },
        apply=ConfigCall(f"{_ext('extension_index')}:apply_from_config"),
        enabled=_any_subsection_enabled,
        order=50,
    ),
    FeatureSpec(
        key="extensions.hf_endpoint_mirror",
        title="Hugging Face 镜像",
        description="注册 Hugging Face endpoint 镜像相关补丁。",
        defaults={
            "enabled": False,
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "启用 Hugging Face endpoint 镜像补丁。",
            },
        },
        apply=ConfigCall(f"{_ext('hf_endpoint_mirror')}:apply_from_config"),
        order=55,
    ),
    FeatureSpec(
        key="extensions.xformers_cutlass",
        title="xFormers CUTLASS",
        description="在 torch>=2.9.0 且 xformers>=0.0.33 时提升 CUTLASS FwOp CUDA capability 上限。",
        defaults={
            "enabled": True,
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "启用 xFormers CUTLASS CUDA capability 补丁；版本不满足时会自动跳过。",
            },
        },
        apply=ConfigCall(f"{_ext('xformers_cutlass')}:apply_from_config"),
        is_active=NoArgCall(f"{_ext('xformers_cutlass')}:is_xformers_cutlass_patch_active"),
        optional=True,
        order=65,
        config_order=60,
    ),
    FeatureSpec(
        key="extensions.uv_pip",
        title="uv Pip 替换",
        description="把 subprocess.run() 调用中的 pip 命令改写为 uv pip，用于加速运行期依赖安装。",
        defaults={
            "enabled": False,
            "symlink": False,
        },
        settings={
            "enabled": {
                "type": "bool",
                "title": "启用",
                "description": "启用 uv pip 命令替换补丁。",
            },
            "symlink": {
                "type": "bool",
                "title": "符号链接模式",
                "description": "为 uv pip 命令添加 --link-mode symlink。通常只在明确需要共享文件链接时启用。",
            },
        },
        apply=ConfigCall(f"{_ext('uv_pip')}:apply_from_config"),
        is_active=NoArgCall(f"{_ext('uv_pip')}:is_uv_patch_installed"),
        revert=NoArgCall(f"{_ext('uv_pip')}:unpatch_uv_to_subprocess"),
        disabled_warning="uv pip patch is already installed and v1 services does not uninstall it",
        order=60,
        config_order=65,
    ),
    FeatureSpec(
        key="control",
        title="运行时控制",
        description="运行时补丁加载与控制平面设置。patch_sets 中声明的补丁模块在全部扩展之后加载。",
        defaults={
            "allow_remote_load": False,
            "patch_sets": [],
            "watch": {
                "enabled": False,
                "interval": 1.0,
            },
        },
        settings={
            "allow_remote_load": {
                "type": "bool",
                "title": "允许远程加载补丁",
                "description": "允许通过运行时控制通道加载补丁代码 (等同于远程代码执行)。旧版传输还要求非空 token。进程内 Python API 不受此限制。",
            },
            "patch_sets": {
                "type": "json",
                "title": "补丁集",
                "description": '随配置加载的补丁模块列表 (JSON 数组)，每项形如 {"source": "pkg.mod 或 /path/patch.py", "name": "可选名称", "config": {}, "enabled": true}。',
            },
            "watch.enabled": {
                "type": "bool",
                "title": "监视补丁文件",
                "description": "轮询已加载补丁模块的源文件，内容变化时自动重新加载。也可通过 SD_WEBUI_ALL_IN_ONE_HOTPATCHER_WATCH=1 启用。",
            },
            "watch.interval": {
                "type": "float",
                "title": "监视间隔",
                "description": "轮询补丁文件的间隔秒数。",
            },
        },
        apply=_loader("_feature_apply_control"),
        is_active=_loader("_feature_control_active"),
        revert=_loader("_feature_revert_control"),
        update=_loader("_feature_update_control"),
        enabled=_always_enabled,
        optional=True,
        order=90,
    ),
)
"""内置功能, 顺序即目录顺序"""
