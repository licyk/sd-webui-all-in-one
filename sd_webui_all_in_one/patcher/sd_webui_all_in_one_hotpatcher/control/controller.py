"""热补丁控制器: 统一命令注册表之上的 Python 门面。

``from sd_webui_all_in_one_hotpatcher import hotpatch`` 返回默认状态的控制器 (惰性导入本模块)。
``hotpatch.call(name, payload)`` 与远程分发走同一个 ``CommandRegistry.dispatch``, 返回 envelope;
其余友好方法返回成功载荷, 失败时抛出 ``CommandError`` (保留错误码与 ``details``)。

操作锁: 同一功能键或同一补丁集名称的修改操作通过专用的非嵌套锁串行化, 锁只包住单次操作调用, 获取超时
(``OPERATION_LOCK_TIMEOUT``) 时返回 ``busy`` 而不是长时间等待。这些锁不是 ``control_lock``: 持有期间会执行
用户补丁代码或导入扩展模块 (因此可能等待导入锁)。由于获取总是带超时, 即使导入中的代码反向调用控制命令也只会
得到 ``busy``, 不会死锁; ``control_lock`` 仍然只在创建锁对象时短暂持有。
"""

from __future__ import annotations

import builtins
import contextlib
import threading
from collections.abc import Generator, Iterable
from typing import TYPE_CHECKING, Any

from ..state import HotpatcherState, get_default_state
from .builtin_commands import register_builtin_commands
from .commands import CommandContext, CommandError, CommandRegistry, CommandSpec, run_after_send, unwrap_envelope
from .patchset import PatchContext, PatchSet, get_patch_set, register_patch_set, remove_patch_set

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = [
    "OPERATION_LOCK_TIMEOUT",
    "HotpatchController",
    "get_controller",
]

OPERATION_LOCK_TIMEOUT = 0.2
"""获取功能/补丁集操作锁的最长等待秒数, 超时返回 ``busy``"""


class _UseBootstrapClient:
    """表示使用 ``state.bootstrap_runtime_client`` 的哨兵类型。"""


_USE_BOOTSTRAP_CLIENT = _UseBootstrapClient()


class _Namespace:
    """友好方法命名空间的基类。"""

    def __init__(self, controller: HotpatchController) -> None:
        """
        绑定控制器。

        Args:
            controller (HotpatchController):
                所属控制器。
        """

        self._controller = controller


class PatchCommands(_Namespace):
    """补丁句柄相关的友好方法 (``hotpatch.patches.*``)。"""

    def list(self, *, owner: str | None = None, limit: int | None = None) -> dict[str, Any]:
        """
        列出补丁句柄摘要。

        Args:
            owner (str | None):
                只列出属于该补丁集 ID 的句柄。
            limit (int | None):
                最多返回的条目数。

        Returns:
            dict[str, Any]:
                ``patches``、``count``、``truncated``。
        """

        return self._controller.request("hotpatch.patches.list", _compact({"owner": owner, "limit": limit}))

    def get(self, handle_id: str) -> dict[str, Any]:
        """
        查询单个句柄详情。

        Args:
            handle_id (str):
                句柄 ID。

        Returns:
            dict[str, Any]:
                句柄详情 (``PatchHandle.to_dict`` 的有界版本)。
        """

        return self._controller.request("hotpatch.patches.get", {"id": handle_id})["patch"]

    def unload(self, handle_id: str) -> dict[str, Any]:
        """
        按句柄移除 import 阶段补丁条目或别名。

        Args:
            handle_id (str):
                句柄 ID。

        Returns:
            dict[str, Any]:
                ``id`` 与移除后的 ``status``。
        """

        return self._controller.request("hotpatch.patches.unload", {"id": handle_id})


class FeatureCommands(_Namespace):
    """功能相关的友好方法 (``hotpatch.features.*``)。"""

    def list(self) -> builtins.list[dict[str, Any]]:
        """
        列出已注册功能及其运行状态。

        Returns:
            builtins.list[dict[str, Any]]:
                ``list_features`` 的 ``features`` 列表。
        """

        return self._controller.request("hotpatch.features.list")["features"]

    def enable(self, key: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        启用功能。

        Args:
            key (str):
                功能键。
            config (dict[str, Any] | None):
                功能配置区段。

        Returns:
            dict[str, Any]:
                ``enable_feature`` 报告。
        """

        return self._controller.request("hotpatch.features.enable", _compact({"key": key, "config": config}))

    def disable(self, key: str) -> dict[str, Any]:
        """
        禁用功能。

        Args:
            key (str):
                功能键。

        Returns:
            dict[str, Any]:
                ``disable_feature`` 报告。
        """

        return self._controller.request("hotpatch.features.disable", {"key": key})

    def update(self, key: str, config: dict[str, Any]) -> dict[str, Any]:
        """
        修改已启用功能的参数。

        Args:
            key (str):
                功能键。
            config (dict[str, Any]):
                功能配置区段 (可只含需要修改的字段)。

        Returns:
            dict[str, Any]:
                ``update_feature`` 报告。
        """

        return self._controller.request("hotpatch.features.update", {"key": key, "config": config})


class DebugCommands(_Namespace):
    """调试相关的友好方法 (``hotpatch.debug.*``)。"""

    def trace(self, tags: str | Iterable[str] | None, *, file: str | None = None) -> dict[str, Any]:
        """
        修改跟踪标签与输出文件。

        Args:
            tags (str | Iterable[str] | None):
                标签集合, ``all`` 表示全部, 空或 None 表示关闭。
            file (str | None):
                输出文件路径, 空字符串表示改为 stderr, None 表示不变。

        Returns:
            dict[str, Any]:
                修改后的跟踪状态。
        """

        payload_tags: Any = tags if tags is None or isinstance(tags, str) else list(tags)
        return self._controller.request("hotpatch.debug.trace.set", _compact({"tags": payload_tags, "file": file}, keep=("tags",)))

    def get_trace(self) -> dict[str, Any]:
        """
        查询跟踪状态。

        Returns:
            dict[str, Any]:
                ``enabled``、``tags``、``file``、``available_tags``。
        """

        return self._controller.request("hotpatch.debug.trace.get")

    def strict(self, enabled: bool) -> dict[str, Any]:
        """
        设置补丁严格模式。

        Args:
            enabled (bool):
                是否启用。

        Returns:
            dict[str, Any]:
                ``strict`` 与 ``previous``。
        """

        return self._controller.request("hotpatch.debug.strict.set", {"enabled": bool(enabled)})

    def events(self, since_cursor: int = 0, limit: int | None = None) -> dict[str, Any]:
        """
        读取补丁事件。

        Args:
            since_cursor (int):
                起始游标。
            limit (int | None):
                最多返回的事件数。

        Returns:
            dict[str, Any]:
                ``events``、``start_cursor``、``next_cursor``、``truncated``、``has_more``。
        """

        return self._controller.request("hotpatch.debug.events.read", _compact({"since_cursor": since_cursor, "limit": limit}))


class InspectCommands(_Namespace):
    """诊断相关的友好方法 (``hotpatch.inspect.*``)。"""

    def explain(self, module: str) -> dict[str, Any]:
        """
        解释模块为什么 (没有) 被打补丁。

        Args:
            module (str):
                完整模块名。

        Returns:
            dict[str, Any]:
                ``explain`` 结果。
        """

        return self._controller.request("hotpatch.inspect.explain", {"module": module})

    def source(self, module: str, *, max_bytes: int | None = None) -> dict[str, Any]:
        """
        预演源码与 AST 补丁并输出补丁后的源码。

        Args:
            module (str):
                完整模块名。
            max_bytes (int | None):
                源码字节上限。

        Returns:
            dict[str, Any]:
                ``render_patched_source`` 结果。
        """

        return self._controller.request("hotpatch.inspect.source", _compact({"module": module, "max_bytes": max_bytes}))

    def verify(self, module: str | None = None) -> dict[str, Any]:
        """
        预演源码、AST 和字节码补丁链。

        Args:
            module (str | None):
                只校验该模块, 为 None 时校验全部。

        Returns:
            dict[str, Any]:
                ``verify_source_patches`` 结果。
        """

        return self._controller.request("hotpatch.inspect.verify", _compact({"module": module}))

    def status(self) -> dict[str, Any]:
        """
        生成状态快照。

        Returns:
            dict[str, Any]:
                ``status_snapshot`` 结果。
        """

        return self._controller.request("hotpatch.status")


class ConnectionCommands(_Namespace):
    """连接相关的友好方法 (``hotpatch.connection.*``)。"""

    def get(self) -> dict[str, Any]:
        """
        查询当前运行时连接 (token 已脱敏)。

        Returns:
            dict[str, Any]:
                ``mode``、``connected``、``settings`` (旧版连接 ``editable`` 为 True, 桌面为 False)、``status``;
                旧版连接另有 ``manager`` (连接状态、丢弃事件数、重连与切换计数、诊断)。
        """

        return self._controller.request("hotpatch.connection.get")

    def test(self, **changes: Any) -> dict[str, Any]:
        """
        按修改后的参数测试连接 (建连并发送 hello 后关闭, 不切换)。

        Args:
            **changes (Any):
                连接字段: ``host``、``port``、``token``、``connect_timeout``、``request_timeout``、
                ``event_write_timeout``、``reconnect``、``reconnect_initial``、``reconnect_max``、``allow_non_loopback``。

        Returns:
            dict[str, Any]:
                ``ok``、脱敏后的 ``settings`` 与 ``elapsed_ms``。
        """

        return self._controller.request("hotpatch.connection.test", changes)

    def update(self, **changes: Any) -> dict[str, Any]:
        """
        先建后拆地切换旧版运行时连接; 进程内调用立即切换。

        Args:
            **changes (Any):
                连接字段, 同 ``test``。

        Returns:
            dict[str, Any]:
                ``status`` 为 ``switched`` 的切换报告; 建连失败或回滚时抛出 ``CommandError`` (``connection_failed``)。
        """

        return self._controller.request("hotpatch.connection.update", changes)


class HotpatchController:
    """
    单个 ``HotpatcherState`` 的控制门面。

    Attributes:
        state (HotpatcherState):
            所属状态对象。
        registry (CommandRegistry):
            命令注册表, 创建时注册全部内置命令。
        patches (PatchCommands):
            补丁句柄命令。
        features (FeatureCommands):
            功能命令。
        debug (DebugCommands):
            调试命令。
        inspect (InspectCommands):
            诊断命令。
        connection (ConnectionCommands):
            连接命令。
    """

    def __init__(self, state: HotpatcherState | None = None) -> None:
        """
        创建控制器并注册内置命令。通常通过 ``get_controller`` 获取。

        Args:
            state (HotpatcherState | None):
                所属状态对象。为 None 时使用默认状态。
        """

        self.state = state or get_default_state()
        self.registry = CommandRegistry()
        self._operation_locks: dict[str, threading.Lock] = {}
        self.patches = PatchCommands(self)
        self.features = FeatureCommands(self)
        self.debug = DebugCommands(self)
        self.inspect = InspectCommands(self)
        self.connection = ConnectionCommands(self)
        register_builtin_commands(self)

    def __repr__(self) -> str:
        """
        返回调试表示。

        Returns:
            str:
                包含已注册命令数量的字符串。
        """

        return f"<HotpatchController commands={len(self.registry.names())}>"

    # -- 分发 -------------------------------------------------------------

    def context(
        self,
        transport: str = "inprocess",
        *,
        token: str | None = None,
        runtime_client: Any = _USE_BOOTSTRAP_CLIENT,
        after_send: list[Callable[[], Any]] | None = None,
    ) -> CommandContext:
        """
        创建命令上下文。

        Args:
            transport (str):
                来源传输。
            token (str | None):
                旧版通道 token。
            runtime_client (Any):
                运行时客户端; 未指定时使用 ``state.bootstrap_runtime_client``。
            after_send (list[Callable[[], Any]] | None):
                响应后回调列表, 为 None 时新建。

        Returns:
            CommandContext:
                命令上下文。
        """

        client = self.state.bootstrap_runtime_client if isinstance(runtime_client, _UseBootstrapClient) else runtime_client
        return CommandContext(
            state=self.state,
            transport=transport,
            token=token,
            runtime_client=client,
            after_send=after_send if after_send is not None else [],
        )

    def dispatch(
        self,
        name: str,
        payload: Any = None,
        *,
        transport: str = "inprocess",
        token: str | None = None,
        runtime_client: Any = _USE_BOOTSTRAP_CLIENT,
        after_send: list[Callable[[], Any]] | None = None,
    ) -> dict[str, Any]:
        """
        分发命令并返回 envelope, 不执行响应后回调 (由传输在发出响应后执行)。

        Args:
            name (str):
                命令名或别名。
            payload (Any):
                载荷。
            transport (str):
                来源传输。
            token (str | None):
                旧版通道 token。
            runtime_client (Any):
                运行时客户端; 未指定时使用 ``state.bootstrap_runtime_client``。
            after_send (list[Callable[[], Any]] | None):
                接收处理函数登记的响应后回调的列表。

        Returns:
            dict[str, Any]:
                成功或错误 envelope。
        """

        ctx = self.context(transport, token=token, runtime_client=runtime_client, after_send=after_send)
        return self.registry.dispatch(name, payload, ctx)

    def call(self, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        进程内分发命令, 与远程分发结果相同; 响应后回调在分发返回后立即执行。

        Args:
            name (str):
                命令名或别名。
            payload (dict[str, Any] | None):
                载荷。

        Returns:
            dict[str, Any]:
                成功或错误 envelope。
        """

        callbacks: list[Callable[[], Any]] = []
        envelope = self.dispatch(name, payload, after_send=callbacks)
        run_after_send(callbacks)
        return envelope

    def request(self, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        进程内分发命令并取出成功载荷。

        Args:
            name (str):
                命令名或别名。
            payload (dict[str, Any] | None):
                载荷。

        Returns:
            dict[str, Any]:
                成功载荷。

        Raises:
            CommandError:
                命令失败时抛出, 保留错误码、信息与 ``details``。
        """

        return unwrap_envelope(self.call(name, payload))

    def register_command(self, spec: CommandSpec, *, replace: bool = False) -> CommandSpec:
        """
        注册自定义命令。

        Args:
            spec (CommandSpec):
                命令声明。
            replace (bool):
                是否替换同名命令。

        Returns:
            CommandSpec:
                同一个命令声明。
        """

        return self.registry.register(spec, replace=replace)

    def unregister_command(self, name: str) -> CommandSpec | None:
        """
        注销命令。

        Args:
            name (str):
                命令名或别名。

        Returns:
            CommandSpec | None:
                被注销的命令。
        """

        return self.registry.unregister(name)

    def commands(self) -> list[str]:
        """
        列出已注册命令名。

        Returns:
            list[str]:
                排序后的规范命令名。
        """

        return self.registry.names()

    def capabilities(self) -> dict[str, Any]:
        """
        查询进程内传输的能力。

        Returns:
            dict[str, Any]:
                ``hotpatch.capabilities`` 载荷。
        """

        return self.request("hotpatch.capabilities")

    def status(self) -> dict[str, Any]:
        """
        生成状态快照。

        Returns:
            dict[str, Any]:
                ``hotpatch.status`` 载荷。
        """

        return self.request("hotpatch.status")

    # -- 补丁集 -----------------------------------------------------------

    @contextlib.contextmanager
    def patch_set(self, name: str, *, config: dict[str, Any] | None = None, transactional: bool = True) -> Generator[PatchContext, None, None]:
        """
        创建并注册补丁集, 在 ``with`` 块内激活它。

        块内抛出异常时 (事务模式) 撤销全部修改并注销补丁集; 正常结束时补丁集保持注册,
        之后可以通过 ``unload_patch(name)`` 卸载。同名的已关闭补丁集会被替换。

        Args:
            name (str):
                补丁集名称。
            config (dict[str, Any] | None):
                通过 ``ctx.config`` 读取的配置。
            transactional (bool):
                是否在块内异常时撤销全部修改。

        Yields:
            PatchContext:
                补丁集上下文。

        Raises:
            ValueError:
                已注册同名的打开补丁集时抛出。
            BaseException:
                ``with`` 块内抛出的异常在撤销 (事务模式) 后原样抛出。
        """

        existing = get_patch_set(name, state=self.state)
        if existing is not None and existing.closed:
            remove_patch_set(existing, state=self.state)
        patch_set = register_patch_set(PatchSet(name, transactional=transactional, config=config, state=self.state), state=self.state)
        try:
            with patch_set as ctx:
                yield ctx
        except BaseException:
            if patch_set.closed:
                remove_patch_set(patch_set, state=self.state)
            raise

    def list_sets(self, *, limit: int | None = None) -> dict[str, Any]:
        """
        列出已注册补丁集。

        Args:
            limit (int | None):
                最多返回的条目数。

        Returns:
            dict[str, Any]:
                ``sets``、``count``、``truncated``。
        """

        return self.request("hotpatch.sets.list", _compact({"limit": limit}))

    def load_patch(self, source: str, *, name: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        加载补丁模块 (点分模块名或文件路径) 并执行其 ``setup(ctx)``。

        Args:
            source (str):
                补丁来源。
            name (str | None):
                补丁名称。
            config (dict[str, Any] | None):
                补丁配置。

        Returns:
            dict[str, Any]:
                ``load_patch`` 报告。
        """

        return self.request("hotpatch.sets.load", _compact({"source": str(source), "name": name, "config": config}))

    def unload_patch(self, key: str) -> dict[str, Any]:
        """
        卸载已加载的补丁或通过 ``patch_set`` 创建的补丁集。功能补丁集请使用 ``features.disable``。

        Args:
            key (str):
                补丁集 ID 或名称。

        Returns:
            dict[str, Any]:
                卸载报告。
        """

        return self.request("hotpatch.sets.unload", {"key": key})

    def reload_patch(self, key: str, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        重新加载补丁, 新代码失败时回滚 (此时抛出 ``CommandError``, ``details`` 为报告)。

        Args:
            key (str):
                补丁集 ID 或名称。
            config (dict[str, Any] | None):
                新配置, 为 None 时沿用。

        Returns:
            dict[str, Any]:
                ``reload_patch`` 报告。
        """

        return self.request("hotpatch.sets.reload", _compact({"key": key, "config": config}))

    def update_patch(self, key: str, config: dict[str, Any]) -> dict[str, Any]:
        """
        修改补丁配置, 模块未提供 ``update`` 时以新配置重新加载。

        Args:
            key (str):
                补丁集 ID 或名称。
            config (dict[str, Any]):
                新配置。

        Returns:
            dict[str, Any]:
                ``update_patch`` 报告。
        """

        return self.request("hotpatch.sets.update", {"key": key, "config": config})

    def reload_module(self, module: str) -> dict[str, Any]:
        """
        在当前补丁计划下重新执行已导入的模块 (不可撤销)。

        Args:
            module (str):
                模块名。

        Returns:
            dict[str, Any]:
                ``module``、``status``、``handle``。
        """

        return self.request("hotpatch.modules.reload", {"module": module})

    # -- 操作锁 -----------------------------------------------------------

    @contextlib.contextmanager
    def operation_lock(self, key: str, *, timeout: float = OPERATION_LOCK_TIMEOUT) -> Generator[None, None, None]:
        """
        获取同一功能或补丁集的操作锁, 超时抛出 ``busy``。

        Args:
            key (str):
                锁键, 例如 ``feature:uv_pip`` 或 ``set:my_patch``。
            timeout (float):
                最长等待秒数。

        Yields:
            None:
                持有锁期间。

        Raises:
            CommandError:
                同一键上已有操作进行中 (等待超时) 时抛出, 错误码为 ``busy``。
        """

        with self.state.control_lock:
            lock = self._operation_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._operation_locks[key] = lock
        if not lock.acquire(timeout=timeout):
            raise CommandError("busy", f"another operation on {key!r} is in progress")
        try:
            yield
        finally:
            lock.release()


def get_controller(state: HotpatcherState | None = None) -> HotpatchController:
    """
    获取状态对象的控制器, 首次访问时创建并保存到 ``state.controller``。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        HotpatchController:
            控制器。
    """

    active_state = state or get_default_state()
    controller = active_state.controller
    if controller is not None:
        return controller
    created = HotpatchController(active_state)
    with active_state.control_lock:
        existing = active_state.controller
        if existing is None:
            active_state.controller = created
            return created
        return existing


def _compact(values: dict[str, Any], *, keep: tuple[str, ...] = ()) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None or key in keep}
