"""import 阶段热补丁框架

控制平面 (``control`` 子包) 只在注册补丁、列出句柄或撤销补丁时才会延迟导入,
``import sd_webui_all_in_one_hotpatcher`` 和安装 import hook 本身不会加载它。

锁约定: ``Monkey`` 内部锁只保护补丁列表与句柄 ID 列表的对齐, 持有时可以进入
``state.control_lock`` (分配和登记句柄 ID), 反之不允许。任何补丁函数、条件函数、
撤销函数和 ``importlib`` 调用都在锁外执行。
"""

from __future__ import annotations

import ast
import copy
import importlib
import importlib.util
import os
import sys
import threading
import weakref
from collections.abc import Callable, Generator, Sequence
from contextlib import AbstractContextManager, contextmanager, nullcontext, redirect_stdout
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import BuiltinImporter, FrozenImporter, ModuleSpec, SourceFileLoader
from io import StringIO
from types import CodeType, ModuleType
from typing import TYPE_CHECKING, Any

from .exceptions import capture_exception
from .mutable import CodeWrapper
from .state import HotpatcherState, get_default_state

if TYPE_CHECKING:
    from .control.handles import PatchHandle, PatchOutcome, PatchStatus
    from .control.journal import PatchJournal
    from .control.patchset import PatchSet

_PACKAGE_NAME = __name__.split(".", 1)[0]
_original_spec_from_file_location = importlib.util.spec_from_file_location

DEBUG_ENV = "SD_WEBUI_ALL_IN_ONE_HOTPATCHER_DEBUG"
"""调试模式环境变量名, 值为 ``1`` 时对 AST 补丁做 ``ast.dump`` 比较以识别 noop"""

PATCH_HANDLE_KIND = "import"
"""import 阶段补丁句柄的 ``kind``"""

ALIAS_HANDLE_KIND = "alias"
"""``alias_if_not_exists`` 句柄的 ``kind``"""

STAGE_ATTRIBUTES: dict[str, str] = {
    "premodule": "premodule_patches",
    "module": "module_patches",
    "function": "function_patches",
    "source": "source_patches",
    "ast": "ast_patches",
    "bytecode": "bytecode_patches",
    "output_prohibition": "output_prohibition",
    "import_injection": "import_injections",
}
"""补丁阶段名到 ``Monkey`` 公开列表属性名的映射"""

_CODE_STAGES = ("source", "ast", "bytecode")
_POST_EXEC_REVERTIBLE_STAGES = frozenset({"function", "import_injection", "output_prohibition"})
_REVERT_HOOK_STAGES = frozenset({"premodule", "module"})
_STATUS_PRIORITY = {"deregistered": 1, "reverted": 2, "requires_restart": 3, "failed": 4}


class _PatchEntry:
    """``Monkey`` 中单个补丁条目的内部记录。"""

    __slots__ = (
        "handle",
        "stage",
        "entry",
        "owner",
        "condition",
        "revert",
        "invoked",
        "detached",
        "final_status",
        "modules",
        "write_tokens",
        "live_handles",
        "unjournaled",
    )

    def __init__(
        self,
        handle: PatchHandle,
        stage: str,
        entry: Any,
        owner: PatchSet | None,
        condition: Callable[[], Any] | None,
        revert: Callable[[ModuleType], Any] | None,
    ) -> None:
        self.handle = handle
        self.stage = stage
        self.entry = entry
        self.owner = owner
        self.condition = condition
        self.revert = revert
        self.invoked = False
        self.detached = False
        self.final_status: PatchStatus | None = None
        self.modules: weakref.WeakSet[ModuleType] = weakref.WeakSet()
        self.write_tokens: dict[tuple[int, str], object] = {}
        # 模块级补丁函数执行期间通过所属补丁集登记的实时操作句柄, 以及是否存在未被日志覆盖的执行。
        self.live_handles: list[PatchHandle] = []
        self.unjournaled = False


class Monkey:
    """
    单个目标模块的补丁计划

    保存源码、AST、字节码、模块对象和函数级补丁, 在目标模块第一次导入时由
    ``MonkeySourceFileLoader`` (源码模块) 或 ``PostExecLoader`` (其他 loader) 按固定顺序执行。

    公开列表保持原有元组结构; 每个条目对应的 ``PatchHandle`` ID 保存在按阶段对齐的
    私有并行列表中。直接向公开列表追加的条目会在列出、移除或执行时惰性分配句柄。

    Attributes:
        premodule_patches (list[tuple[Callable[[ModuleType], Any], int]]):
            模块代码执行前调用的补丁
        module_patches (list[tuple[Callable[[ModuleType], Any], int]]):
            模块代码执行后调用的补丁
        function_patches (list[tuple[str, Callable[[Any, ModuleType], Any], int, bool]]):
            函数替换补丁
        source_patches (list[tuple[Callable[[str, str], str | tuple[str] | tuple[str, str]], int]]):
            源码字符串补丁
        ast_patches (list[tuple[ast.NodeTransformer | ast.NodeVisitor | Callable[[ast.AST], ast.AST], int]]):
            AST 补丁
        bytecode_patches (list[tuple[Callable[[CodeWrapper], Any], int]]):
            字节码补丁
        output_prohibition (list[str | None]):
            需要抑制 stdout 输出的方法名
        import_injections (list[tuple[str, str | None, str | None, int]]):
            需要注入到目标模块命名空间的 import
    """

    def __init__(self) -> None:
        self.premodule_patches: list[tuple[Callable[[ModuleType], Any], int]] = []
        self.module_patches: list[tuple[Callable[[ModuleType], Any], int]] = []
        self.function_patches: list[tuple[str, Callable[[Any, ModuleType], Any], int, bool]] = []
        self.source_patches: list[tuple[Callable[[str, str], str | tuple[str] | tuple[str, str]], int]] = []
        self.ast_patches: list[tuple[ast.NodeTransformer | ast.NodeVisitor | Callable[[ast.AST], ast.AST], int]] = []
        self.bytecode_patches: list[tuple[Callable[[CodeWrapper], Any], int]] = []
        self.output_prohibition: list[str | None] = []
        self.import_injections: list[tuple[str, str | None, str | None, int]] = []
        self._lock = threading.RLock()
        self._handle_ids: dict[str, list[str]] = {stage: [] for stage in STAGE_ATTRIBUTES}
        self._entries: dict[str, _PatchEntry] = {}
        self._journal: PatchJournal | None = None
        self._zoo: MonkeyZoo | None = None
        self._name: str | None = None

    @property
    def active(self) -> bool:
        """
        是否存在有效补丁

        Returns:
            bool:
                任意补丁列表非空时返回 True
        """

        return any(
            (
                self.premodule_patches,
                self.module_patches,
                self.function_patches,
                self.source_patches,
                self.ast_patches,
                self.bytecode_patches,
                self.output_prohibition,
                self.import_injections,
            )
        )

    @property
    def has_cache_side_effect(self) -> bool:
        """
        是否存在会影响 loader 缓存的补丁

        Returns:
            bool:
                存在源码或 AST 补丁时返回 True
        """

        return bool(self.source_patches or self.ast_patches)

    @property
    def name(self) -> str | None:
        """
        补丁计划对应的模块名

        Returns:
            str | None:
                通过 ``MonkeyZoo`` 获取的计划返回模块名, 独立创建且未绑定时为 None
        """

        return self._name

    def patch_function(
        self,
        function_name: str,
        hooker: Callable[[Any, ModuleType], Any],
        priority: int = 100,
        add_if_not_exists: bool = False,
        *,
        condition: Callable[[], Any] | None = None,
    ) -> PatchHandle:
        """
        注册函数替换补丁

        Args:
            function_name (str):
                目标函数名
            hooker (Callable[[Any, ModuleType], Any]):
                接收原函数和模块对象, 返回替换对象的补丁函数
            priority (int):
                执行优先级, 数字越小越早执行
            add_if_not_exists (bool):
                函数不存在时是否仍写入补丁返回值
            condition (Callable[[], Any] | None):
                应用时求值的条件, 返回假值时跳过并记录 ``skipped:condition_false``

        Returns:
            PatchHandle:
                补丁句柄
        """

        return self._register("function", (function_name, hooker, priority, add_if_not_exists), f"{self._target_name()}:{function_name}", condition=condition)

    def patch_premodule(
        self,
        hooker: Callable[[ModuleType], Any],
        priority: int = 100,
        *,
        revert: Callable[[ModuleType], Any] | None = None,
        condition: Callable[[], Any] | None = None,
    ) -> PatchHandle:
        """
        注册模块代码执行前补丁

        对非源码 loader (扩展模块等), 补丁在 loader 的 ``create_module`` 之后执行;
        单阶段初始化的扩展模块在 ``create_module`` 时已经完成初始化。

        Args:
            hooker (Callable[[ModuleType], Any]):
                接收模块对象的补丁函数
            priority (int):
                执行优先级, 数字越小越早执行
            revert (Callable[[ModuleType], Any] | None):
                卸载时对已执行过补丁的模块调用的逆操作。提供时卸载状态为 ``reverted``;
                未提供时适用 ``patch_module`` 中说明的启发式规则, 否则补丁执行后卸载状态为 ``requires_restart``
            condition (Callable[[], Any] | None):
                应用时求值的条件, 返回假值时跳过并记录 ``skipped:condition_false``

        Returns:
            PatchHandle:
                补丁句柄
        """

        return self._register("premodule", (hooker, priority), self._target_name(), condition=condition, revert=revert)

    def patch_module(
        self,
        hooker: Callable[[ModuleType], Any],
        priority: int = 100,
        *,
        revert: Callable[[ModuleType], Any] | None = None,
        condition: Callable[[], Any] | None = None,
    ) -> PatchHandle:
        """
        注册模块代码执行后补丁

        卸载启发式规则 (同样适用于 ``patch_premodule``): 补丁属于补丁集时, 补丁函数运行期间
        ``current_patch_context()`` 返回所属补丁集的上下文。若每次执行都至少通过它登记了一个实时操作
        (``ctx.set_attr`` / ``ctx.wrap`` / ``ctx.add_disposer`` 等) 且没有抛出异常, 卸载时这些操作会被撤销,
        状态报告为 ``reverted`` 而不是 ``requires_restart``。框架无法检测补丁函数直接执行的
        ``setattr`` 等未记录修改; 同时存在这类修改时应提供 ``revert``, 它优先于启发式规则。

        Args:
            hooker (Callable[[ModuleType], Any]):
                接收模块对象的补丁函数
            priority (int):
                执行优先级, 数字越小越早执行
            revert (Callable[[ModuleType], Any] | None):
                卸载时对已执行过补丁的模块调用的逆操作。提供时卸载状态为 ``reverted``;
                未提供时适用 ``patch_module`` 中说明的启发式规则, 否则补丁执行后卸载状态为 ``requires_restart``
            condition (Callable[[], Any] | None):
                应用时求值的条件, 返回假值时跳过并记录 ``skipped:condition_false``

        Returns:
            PatchHandle:
                补丁句柄
        """

        return self._register("module", (hooker, priority), self._target_name(), condition=condition, revert=revert)

    def patch_sources(
        self,
        hooker: Callable[[str, str], str | tuple[str] | tuple[str, str]],
        priority: int = 100,
        *,
        condition: Callable[[], Any] | None = None,
    ) -> PatchHandle:
        """
        注册源码补丁

        Args:
            hooker (Callable[[str, str], str | tuple[str] | tuple[str, str]]):
                接收源码和文件名, 返回新源码或新源码加新文件名的函数
            priority (int):
                执行优先级, 数字越小越早执行
            condition (Callable[[], Any] | None):
                应用时求值的条件, 返回假值时跳过并记录 ``skipped:condition_false``

        Returns:
            PatchHandle:
                补丁句柄
        """

        return self._register("source", (hooker, priority), self._target_name(), condition=condition)

    def patch_ast(
        self,
        hooker: ast.NodeTransformer | ast.NodeVisitor | Callable[[ast.AST], ast.AST],
        priority: int = 100,
        *,
        condition: Callable[[], Any] | None = None,
    ) -> PatchHandle:
        """
        注册 AST 补丁

        Args:
            hooker (ast.NodeTransformer | ast.NodeVisitor | Callable[[ast.AST], ast.AST]):
                AST visitor、transformer 或接收 AST 并返回 AST 的函数
            priority (int):
                执行优先级, 数字越小越早执行
            condition (Callable[[], Any] | None):
                应用时求值的条件, 返回假值时跳过并记录 ``skipped:condition_false``

        Returns:
            PatchHandle:
                补丁句柄
        """

        return self._register("ast", (hooker, priority), self._target_name(), condition=condition)

    def patch_bytecode(
        self,
        hooker: Callable[[CodeWrapper], Any],
        priority: int = 100,
        *,
        condition: Callable[[], Any] | None = None,
    ) -> PatchHandle:
        """
        注册字节码补丁

        Args:
            hooker (Callable[[CodeWrapper], Any]):
                接收 code object 可变代理的补丁函数
            priority (int):
                执行优先级, 数字越小越早执行
            condition (Callable[[], Any] | None):
                应用时求值的条件, 返回假值时跳过并记录 ``skipped:condition_false``

        Returns:
            PatchHandle:
                补丁句柄
        """

        return self._register("bytecode", (hooker, priority), self._target_name(), condition=condition)

    def prohibit_output(
        self,
        method: str | None = None,
        *,
        condition: Callable[[], Any] | None = None,
    ) -> PatchHandle:
        """
        注册 stdout 输出抑制

        Args:
            method (str | None):
                需要抑制输出的方法名。为 None 时抑制整个模块执行阶段输出。
            condition (Callable[[], Any] | None):
                应用时求值的条件, 返回假值时跳过并记录 ``skipped:condition_false``

        Returns:
            PatchHandle:
                补丁句柄
        """

        return self._register("output_prohibition", method, f"{self._target_name()}:{method if method is not None else '*'}", condition=condition)

    def inject_import(
        self,
        package: str,
        content: str | None = None,
        alias: str | None = None,
        priority: int = 100,
        *,
        condition: Callable[[], Any] | None = None,
    ) -> PatchHandle:
        """
        注册 import 注入

        Args:
            package (str):
                需要导入的包或模块名
            content (str | None):
                从模块中取出的成员名
            alias (str | None):
                注入到目标模块时使用的名称
            priority (int):
                执行优先级, 数字越小越早执行
            condition (Callable[[], Any] | None):
                应用时求值的条件, 返回假值时跳过并记录 ``skipped:condition_false``

        Returns:
            PatchHandle:
                补丁句柄
        """

        alias_name = alias if alias is not None else content if content is not None else package
        return self._register("import_injection", (package, content, alias, priority), f"{self._target_name()}:{alias_name}", condition=condition)

    def handles(self, stage: str | None = None) -> list[PatchHandle]:
        """
        列出补丁句柄

        直接追加到公开列表的条目会在此时分配句柄。

        Args:
            stage (str | None):
                只列出该阶段 (``STAGE_ATTRIBUTES`` 的键)。为 None 时按阶段顺序列出全部

        Returns:
            list[PatchHandle]:
                句柄列表, 每个阶段内与公开列表顺序一致

        Raises:
            KeyError:
                阶段名未知时抛出。
        """

        stages = list(STAGE_ATTRIBUTES) if stage is None else [stage]
        for name in stages:
            if name not in STAGE_ATTRIBUTES:
                raise KeyError(name)
        with self._lock:
            self._sync_locked()
            return [self._entries[handle_id].handle for name in stages for handle_id in self._handle_ids[name]]

    def remove(self, handle: PatchHandle | str) -> PatchStatus | None:
        """
        从补丁计划移除条目, 并撤销框架记录的实时写入

        按身份 (``is``) 在阶段列表中查找条目, 同时删除公开列表和句柄 ID 列表中的同一位置。
        属于补丁集的条目通过补丁集日志撤销。状态规则: 目标模块从未以该条目执行过时为
        ``deregistered``; 函数、import 注入和输出抑制补丁为 ``reverted`` (写入已被之后的其他对象覆盖时为
        ``requires_restart``); 提供了 ``revert`` 的模块级补丁为 ``reverted``; 模块级补丁每次执行都通过
        ``current_patch_context()`` 登记了实时操作且没有抛出异常时, 这些操作会一并撤销并报告 ``reverted``
        (启发式规则, 见 ``patch_module``); 其余为 ``requires_restart``。

        Args:
            handle (PatchHandle | str):
                句柄或句柄 ID

        Returns:
            PatchStatus | None:
                移除后的句柄状态, 句柄不属于本计划时为 None
        """

        from .control.handles import PatchOutcome, PatchStatus

        handle_id = handle if isinstance(handle, str) else handle.id
        with self._lock:
            self._sync_locked()
            record = self._entries.get(handle_id)
        if record is None:
            return None
        owner = record.owner
        status: PatchStatus | None
        if owner is not None:
            status = _undo_owned_handle(owner, record.handle)
            if status is None:
                status = self._undo_entry(record)
        else:
            try:
                status = self._undo_entry(record)
            except Exception as exc:
                record.handle.record_outcome(PatchOutcome.failed(exc, reason="undo_failed"))
                capture_exception(exc, state=self._get_state())
                status = PatchStatus.FAILED
                record.final_status = status
        record.handle.status = status
        return status

    def apply_to_loaded(self, module: ModuleType, *, handle_ids: set[str] | frozenset[str] | None = None) -> None:
        """
        把补丁计划追溯应用到已导入的模块

        只执行函数、模块、import 注入和方法级输出抑制补丁; 源码、AST、字节码、模块执行前补丁
        和整模块输出抑制记录为 ``skipped:already_imported``。每个条目对同一个模块对象最多追溯
        应用一次, 之后真实导入或 ``reload`` 仍会正常执行。

        Args:
            module (ModuleType):
                已导入的模块对象
            handle_ids (set[str] | frozenset[str] | None):
                只应用这些句柄对应的条目。为 None 时应用全部条目
        """

        from .control.handles import PatchOutcome

        def select(record: _PatchEntry) -> bool:
            return (handle_ids is None or record.handle.id in handle_ids) and module not in record.modules

        for stage in (*_CODE_STAGES, "premodule", "output_prohibition"):
            for item, record in self._stage_records(stage):
                if stage == "output_prohibition" and item is not None:
                    continue
                if select(record) and self._can_run(record):
                    self._record_outcome(record, PatchOutcome.skipped("already_imported"))
        self._run_import_injection(module, select)
        self._run_function(module, select)
        self._run_module_hookers("module", module, select)
        self._run_prohibit_output(module, select)

    def eval_source(self, source: str, filename: str, *, module: ModuleType | None = None, record_outcomes: bool = True) -> tuple[str, str]:
        """
        执行源码补丁链

        Args:
            source (str):
                原始源码
            filename (str):
                原始文件名
            module (ModuleType | None):
                即将执行该代码的模块对象。提供时条目视为已对该模块生效
            record_outcomes (bool):
                是否记录执行结果和句柄状态, 预演时传入 False

        Returns:
            tuple[str, str]:
                补丁后的源码和文件名

        Raises:
            TypeError:
                严格模式下源码补丁返回值类型不受支持时抛出。
            ValueError:
                严格模式下源码补丁返回的元组长度不受支持时抛出。
        """

        entries = self._stage_records("source")
        if not entries:
            return source, filename

        from .control.handles import PatchOutcome

        for (hooker, _), record in sorted(entries, key=lambda pair: pair[0][1]):
            if not self._can_run(record) or not self._condition_allows(record, module, record_outcomes):
                continue
            try:
                with self._activation(record):
                    result = hooker(source, filename)
                if isinstance(result, str):
                    new_source, new_filename = result, filename
                elif isinstance(result, tuple):
                    if len(result) == 1:
                        new_source, new_filename = result[0], filename
                    elif len(result) == 2:
                        new_source, new_filename = result
                    else:
                        raise ValueError("Invalid source patch return value")
                else:
                    raise TypeError("Source patch must return str, tuple[str], or tuple[str, str]")
            except Exception as exc:
                self._handle_failure(record, exc, module, record_outcomes)
                continue
            unchanged = new_source == source and new_filename == filename
            source, filename = new_source, new_filename
            self._record_outcome(record, PatchOutcome.noop() if unchanged else PatchOutcome.applied(), module, enabled=record_outcomes)
        return source, filename

    def eval_ast(self, tree: ast.AST, *, module: ModuleType | None = None, record_outcomes: bool = True) -> ast.AST:
        """
        执行 AST 补丁链

        严格模式或调试模式下会用 ``ast.dump`` 比较前后 AST, 没有变化时记录 ``noop``。

        Args:
            tree (ast.AST):
                原始 AST
            module (ModuleType | None):
                即将执行该代码的模块对象。提供时条目视为已对该模块生效
            record_outcomes (bool):
                是否记录执行结果和句柄状态, 预演时传入 False

        Returns:
            ast.AST:
                补丁后的 AST
        """

        entries = self._stage_records("ast")
        if not entries:
            return tree

        from .control.handles import PatchOutcome

        compare = self._get_state().strict_mode or os.getenv(DEBUG_ENV) == "1"
        for (hooker, _), record in sorted(entries, key=lambda pair: pair[0][1]):
            if not self._can_run(record) or not self._condition_allows(record, module, record_outcomes):
                continue
            before = ast.dump(tree) if compare else None
            try:
                with self._activation(record):
                    if isinstance(hooker, ast.NodeTransformer):
                        tree = hooker.visit(tree)
                    elif isinstance(hooker, ast.NodeVisitor):
                        hooker.visit(tree)
                    else:
                        tree = hooker(tree)
            except Exception as exc:
                self._handle_failure(record, exc, module, record_outcomes)
                continue
            unchanged = before is not None and isinstance(tree, ast.AST) and ast.dump(tree) == before
            self._record_outcome(record, PatchOutcome.noop() if unchanged else PatchOutcome.applied(), module, enabled=record_outcomes)
        return tree

    def eval_bytecode(self, code_object: CodeType, *, module: ModuleType | None = None, record_outcomes: bool = True) -> CodeType:
        """
        执行字节码补丁链

        Args:
            code_object (CodeType):
                原始 code object
            module (ModuleType | None):
                即将执行该代码的模块对象。提供时条目视为已对该模块生效
            record_outcomes (bool):
                是否记录执行结果和句柄状态, 预演时传入 False

        Returns:
            CodeType:
                补丁后的 code object
        """

        entries = self._stage_records("bytecode")
        code_wrapper = CodeWrapper(code_object)
        if not entries:
            return code_wrapper.conclude()

        from .control.handles import PatchOutcome

        for (hooker, _), record in sorted(entries, key=lambda pair: pair[0][1]):
            if not self._can_run(record) or not self._condition_allows(record, module, record_outcomes):
                continue
            try:
                with self._activation(record):
                    hooker(code_wrapper)
            except Exception as exc:
                self._handle_failure(record, exc, module, record_outcomes)
                continue
            self._record_outcome(record, PatchOutcome.applied(), module, enabled=record_outcomes)
        return code_wrapper.conclude()

    def eval_premodule(self, module: ModuleType) -> None:
        """
        执行模块代码前补丁链

        Args:
            module (ModuleType):
                正在导入的模块对象
        """

        self._run_module_hookers("premodule", module, None)

    def eval_module(self, module: ModuleType) -> None:
        """
        执行模块代码后补丁链

        Args:
            module (ModuleType):
                已执行代码的模块对象
        """

        self._run_module_hookers("module", module, None)

    def eval_function(self, module: ModuleType) -> None:
        """
        执行函数替换补丁链

        Args:
            module (ModuleType):
                已执行代码的模块对象
        """

        self._run_function(module, None)

    def eval_prohibit_output(self, module: ModuleType) -> None:
        """
        执行方法级输出抑制补丁

        Args:
            module (ModuleType):
                已执行代码的模块对象
        """

        self._run_prohibit_output(module, None)

    def eval_import_injection(self, module: ModuleType) -> None:
        """
        执行 import 注入补丁链

        Args:
            module (ModuleType):
                正在导入的模块对象
        """

        self._run_import_injection(module, None)

    def suppress_module_output(self, module: ModuleType) -> bool:
        """
        判断模块执行阶段是否需要抑制 stdout, 并记录整模块输出抑制条目的结果

        Args:
            module (ModuleType):
                即将执行代码的模块对象

        Returns:
            bool:
                存在条件满足的 ``prohibit_output(None)`` 条目时返回 True
        """

        if None not in self.output_prohibition:
            return False

        from .control.handles import PatchOutcome

        suppress = False
        for method, record in self._stage_records("output_prohibition"):
            if method is not None or not self._can_run(record) or not self._condition_allows(record, module, True):
                continue
            suppress = True
            self._record_outcome(record, PatchOutcome.applied(), module)
        return suppress

    def skip_code_stages(self, reason: str) -> None:
        """
        把源码、AST 和字节码补丁记录为跳过

        Args:
            reason (str):
                跳过原因, 例如 ``unsupported_loader``
        """

        if not (self.source_patches or self.ast_patches or self.bytecode_patches):
            return

        from .control.handles import PatchOutcome

        for stage in _CODE_STAGES:
            for _, record in self._stage_records(stage):
                if self._can_run(record):
                    self._record_outcome(record, PatchOutcome.skipped(reason))

    # ------------------------------------------------------------------ 内部实现

    def _bind(self, zoo: MonkeyZoo, name: str) -> None:
        if self._zoo is None:
            self._zoo = zoo
        if self._name is None:
            self._name = name

    def _get_state(self) -> HotpatcherState:
        return self._zoo.state if self._zoo is not None else get_default_state()

    def _target_name(self) -> str:
        return self._name if self._name is not None else "<unbound>"

    def _invalidate(self) -> None:
        if self._zoo is not None and self._name is not None:
            self._zoo.invalidate(self._name)

    def _register(
        self,
        stage: str,
        entry: Any,
        target: str,
        *,
        condition: Callable[[], Any] | None = None,
        revert: Callable[[ModuleType], Any] | None = None,
    ) -> PatchHandle:
        from .control.handles import create_patch_handle
        from .control.patchset import PatchSetClosedError, current_patch_context

        context = current_patch_context()
        owner = context.patch_set if context is not None else None
        handle = create_patch_handle(PATCH_HANDLE_KIND, target, stage=stage, register=owner is None, state=self._get_state())
        record = _PatchEntry(handle, stage, entry, owner, condition, revert)
        if owner is not None:
            # 先归属再写入计划: 补丁集已关闭时直接抛出, 计划中不会留下无主条目。
            owner.adopt_handle(handle, undo=lambda: self._undo_entry(record))
        with self._lock:
            self._sync_locked()
            getattr(self, STAGE_ATTRIBUTES[stage]).append(entry)
            self._handle_ids[stage].append(handle.id)
            self._entries[handle.id] = record
        if owner is not None and owner.closed:
            self._undo_entry(record)
            raise PatchSetClosedError(f"patch set {owner.name!r} was closed while registering {stage} patch for {target!r}")
        self._invalidate()
        return handle

    def _new_lazy_entry_locked(self, stage: str, item: Any) -> _PatchEntry:
        from .control.handles import create_patch_handle

        handle = create_patch_handle(PATCH_HANDLE_KIND, _describe_entry(self._target_name(), stage, item), stage=stage, state=self._get_state())
        record = _PatchEntry(handle, stage, item, None, None, None)
        self._entries[handle.id] = record
        return record

    def _sync_locked(self) -> None:
        for stage in STAGE_ATTRIBUTES:
            self._sync_stage_locked(stage)

    def _sync_stage_locked(self, stage: str) -> None:
        public = getattr(self, STAGE_ATTRIBUTES[stage])
        ids = self._handle_ids[stage]
        entries = self._entries
        if len(public) == len(ids) and all(handle_id in entries and entries[handle_id].entry is item for handle_id, item in zip(ids, public)):
            return
        # 公开列表被绕过 patch_* 直接修改: 按身份重新对齐, 新条目惰性分配句柄, 消失的条目视为已移除。
        pending = [self._entries[handle_id] for handle_id in ids if handle_id in self._entries]
        new_ids: list[str] = []
        for item in public:
            for index, candidate in enumerate(pending):
                if candidate.entry is item:
                    del pending[index]
                    new_ids.append(candidate.handle.id)
                    break
            else:
                new_ids.append(self._new_lazy_entry_locked(stage, item).handle.id)
        ids[:] = new_ids
        for orphan in pending:
            self._entries.pop(orphan.handle.id, None)
            self._forget(orphan)

    def _stage_records(self, stage: str) -> list[tuple[Any, _PatchEntry]]:
        with self._lock:
            if not getattr(self, STAGE_ATTRIBUTES[stage]) and not self._handle_ids[stage]:
                return []
            self._sync_stage_locked(stage)
            ids = list(self._handle_ids[stage])
            items = list(getattr(self, STAGE_ATTRIBUTES[stage]))
            return [(item, self._entries[handle_id]) for item, handle_id in zip(items, ids)]

    def _handle_id_snapshot(self) -> frozenset[str]:
        if not self.active:
            return frozenset()
        with self._lock:
            self._sync_locked()
            return frozenset(self._entries)

    def _detach(self, record: _PatchEntry) -> None:
        with self._lock:
            if record.detached:
                return
            stage = record.stage
            self._sync_stage_locked(stage)
            public = getattr(self, STAGE_ATTRIBUTES[stage])
            ids = self._handle_ids[stage]
            # 按身份查找: output_prohibition 中的 None 和驻留字符串会重复, 同时核对句柄 ID 以确定唯一位置。
            for index, item in enumerate(public):
                if item is record.entry and ids[index] == record.handle.id:
                    del public[index]
                    del ids[index]
                    break
            self._entries.pop(record.handle.id, None)
            record.detached = True
            emptied = not self.active
        zoo = self._zoo
        if emptied and zoo is not None and self._name is not None:
            key = self._name.casefold()
            if zoo.monkeys.get(key) is self:
                zoo.monkeys.pop(key, None)
        self._invalidate()

    def _undo_entry(self, record: _PatchEntry) -> PatchStatus:
        from .control.handles import PatchStatus, unregister_patch_handle

        if record.final_status is not None:
            return record.final_status
        self._detach(record)
        status = PatchStatus.DEREGISTERED
        if record.owner is None and self._journal is not None:
            # 无主条目的框架写入记录在本计划自己的日志中; 有主条目的写入位于补丁集日志, 由补丁集按 LIFO 撤销。
            report = self._journal.undo(handle_id=record.handle.id)
            for result in report.results:
                if result.error is not None:
                    capture_exception(result.error, state=self._get_state())
                    status = _merge_status(status, PatchStatus.FAILED)
                else:
                    status = _merge_status(status, _coerce_status(result.result))
        if record.invoked:
            if record.stage in _POST_EXEC_REVERTIBLE_STAGES:
                status = _merge_status(status, PatchStatus.REVERTED)
            elif record.stage in _REVERT_HOOK_STAGES:
                live_status = self._undo_live_operations(record)
                if live_status is not None:
                    status = _merge_status(status, live_status)
                if record.revert is not None:
                    for module in list(record.modules):
                        record.revert(module)
                    status = _merge_status(status, PatchStatus.REVERTED)
                elif live_status is not None and not record.unjournaled:
                    # 启发式: 每次执行的效果都由补丁集日志中的实时操作覆盖, 撤销这些操作即完全还原。
                    status = _merge_status(status, PatchStatus.REVERTED)
                else:
                    status = _merge_status(status, PatchStatus.REQUIRES_RESTART)
            else:
                status = _merge_status(status, PatchStatus.REQUIRES_RESTART)
        record.final_status = status
        # 直接写入句柄状态: PatchSet.close() 会跳过状态为 failed 的句柄, 这里保证两条卸载路径结果一致。
        record.handle.status = status
        if record.owner is None:
            unregister_patch_handle(record.handle.id, state=self._get_state())
        return status

    def _undo_live_operations(self, record: _PatchEntry) -> PatchStatus | None:
        # 撤销模块级补丁函数登记的实时操作 (LIFO)。补丁集关闭时这些条目已被整体撤销, 此处为空操作。
        from .control.handles import PatchStatus

        owner = record.owner
        handles = [handle for handle in record.live_handles if handle.status is not PatchStatus.FAILED]
        if owner is None or not handles:
            return None
        status = PatchStatus.REVERTED
        for handle in reversed(handles):
            result = _undo_owned_handle(owner, handle)
            if result is None:
                if handle.status is PatchStatus.REQUIRES_RESTART:
                    status = _merge_status(status, PatchStatus.REQUIRES_RESTART)
                continue
            if result is PatchStatus.DEREGISTERED:
                result = PatchStatus.REVERTED
            handle.status = result
            status = _merge_status(status, result)
        return status

    def _note_live_operations(self, record: _PatchEntry, collected: list[PatchHandle], *, failed: bool) -> None:
        from .control.handles import PatchStatus

        owner = record.owner
        if owner is None:
            return
        operations = [handle for handle in collected if handle.owner == owner.id and handle.kind != PATCH_HANDLE_KIND]
        record.live_handles.extend(operations)
        if failed or not any(handle.status is not PatchStatus.FAILED for handle in operations):
            record.unjournaled = True

    @contextmanager
    def _hooker_scope(self, record: _PatchEntry) -> Generator[list[PatchHandle], None, None]:
        # 激活所属补丁集并收集补丁函数登记的实时操作; 无主条目不收集。
        owner = record.owner
        if owner is None:
            yield []
            return

        from .control.patchset import collect_operations

        with owner.context.activate(), collect_operations() as collected:
            yield collected

    def _forget(self, record: _PatchEntry) -> None:
        # 只从计划中忘记条目, 不撤销实时写入 (discard / clear 语义)。有主条目留给补丁集关闭时处理。
        record.detached = True
        if record.owner is not None or record.final_status is not None:
            return
        from .control.handles import PatchStatus, unregister_patch_handle

        status = PatchStatus.REQUIRES_RESTART if record.invoked else PatchStatus.DEREGISTERED
        record.final_status = status
        record.handle.status = status
        unregister_patch_handle(record.handle.id, state=self._get_state())

    def _forget_all(self) -> None:
        with self._lock:
            records = list(self._entries.values())
        for record in records:
            self._forget(record)

    def _local_journal(self) -> PatchJournal:
        if self._journal is None:
            from .control.journal import PatchJournal

            with self._lock:
                if self._journal is None:
                    self._journal = PatchJournal()
        return self._journal

    def _can_run(self, record: _PatchEntry) -> bool:
        if record.detached:
            return False
        owner = record.owner
        return owner is None or not owner.closed

    def _activation(self, record: _PatchEntry) -> AbstractContextManager[Any]:
        # 补丁函数在 import 时运行, 注册时的 with 块早已退出; 重新激活所属补丁集,
        # 使补丁函数内部通过 current_patch_context() 登记的逆操作归属到同一补丁集。
        owner = record.owner
        if owner is None:
            return nullcontext()
        return owner.context.activate()

    def _condition_allows(self, record: _PatchEntry, module: ModuleType | None, enabled: bool) -> bool:
        condition = record.condition
        if condition is None:
            return True

        from .control.handles import PatchOutcome

        try:
            with self._activation(record):
                allowed = bool(condition())
        except Exception as exc:
            self._handle_failure(record, exc, None, enabled)
            return False
        if not allowed:
            self._record_outcome(record, PatchOutcome.skipped("condition_false"), enabled=enabled)
        return allowed

    def _record_outcome(self, record: _PatchEntry, outcome: PatchOutcome, module: ModuleType | None = None, *, enabled: bool = True) -> None:
        from .control.handles import PatchOutcomeKind, PatchStatus

        kind = outcome.kind
        if module is not None and kind is not PatchOutcomeKind.SKIPPED:
            record.invoked = True
            record.modules.add(module)
        if not enabled:
            return
        handle = record.handle
        handle.record_outcome(outcome)
        if record.final_status is not None:
            return
        if kind is PatchOutcomeKind.FAILED:
            handle.status = PatchStatus.FAILED
        elif kind is not PatchOutcomeKind.SKIPPED:
            handle.status = PatchStatus.APPLIED

    def _handle_failure(self, record: _PatchEntry, exc: Exception, module: ModuleType | None, enabled: bool) -> None:
        from .control.handles import PatchOutcome

        self._record_outcome(record, PatchOutcome.failed(exc), module, enabled=enabled)
        state = self._get_state()
        if state.strict_mode:
            raise exc
        capture_exception(exc, state=state)

    def _write(self, record: _PatchEntry, module: ModuleType, name: str, value: Any) -> None:
        from .control.journal import NOTSET

        namespace = module.__dict__
        previous = namespace.get(name, NOTSET)
        namespace[name] = value
        # 同一条目对同一命名空间键的新写入 (例如 reload 重新执行模块后再次打补丁) 取代旧写入, 旧条目撤销时为空操作。
        token = object()
        record.write_tokens[(id(namespace), name)] = token
        owner = record.owner
        journal = owner.journal if owner is not None else self._local_journal()
        label = f"{getattr(module, '__name__', '<module>')}.{name}"
        journal.record_callback(_namespace_restorer(record, namespace, name, value, previous, token), label, kind="item", handle_id=record.handle.id)
        if owner is not None and owner.closed:
            # 补丁集在写入期间关闭: 日志已被清空, 立即撤销本次写入, 不留下无人撤销的条目。
            owner.journal.undo(handle_id=record.handle.id)

    def _run_module_hookers(self, stage: str, module: ModuleType, select: Callable[[_PatchEntry], bool] | None) -> None:
        entries = self._stage_records(stage)
        if not entries:
            return

        from .control.handles import PatchOutcome

        for (hooker, _), record in sorted(entries, key=lambda pair: pair[0][1]):
            if (select is not None and not select(record)) or not self._can_run(record) or not self._condition_allows(record, module, True):
                continue
            collected: list[PatchHandle] = []
            try:
                with self._hooker_scope(record) as collected:
                    hooker(module)
            except Exception as exc:
                self._note_live_operations(record, collected, failed=True)
                self._handle_failure(record, exc, module, True)
                continue
            self._note_live_operations(record, collected, failed=False)
            self._record_outcome(record, PatchOutcome.applied(), module)

    def _run_function(self, module: ModuleType, select: Callable[[_PatchEntry], bool] | None) -> None:
        entries = self._stage_records("function")
        if not entries:
            return

        from .control.handles import PatchOutcome

        for (function_name, hooker, _, add_if_not_exists), record in sorted(entries, key=lambda pair: pair[0][2]):
            if (select is not None and not select(record)) or not self._can_run(record) or not self._condition_allows(record, module, True):
                continue
            if not (add_if_not_exists or function_name in module.__dict__):
                self._record_outcome(record, PatchOutcome.skipped("function_missing"))
                continue
            try:
                original = module.__dict__.get(function_name)
                with self._activation(record):
                    replacement = hooker(original, module)
                if replacement is not None:
                    self._write(record, module, function_name, replacement)
            except Exception as exc:
                self._handle_failure(record, exc, module, True)
                continue
            self._record_outcome(record, PatchOutcome.noop() if replacement is None else PatchOutcome.applied(), module)

    def _run_prohibit_output(self, module: ModuleType, select: Callable[[_PatchEntry], bool] | None) -> None:
        entries = self._stage_records("output_prohibition")
        if not entries:
            return

        from .control.handles import PatchOutcome

        for method, record in entries:
            if method is None:
                continue
            if (select is not None and not select(record)) or not self._can_run(record) or not self._condition_allows(record, module, True):
                continue
            if method not in module.__dict__:
                self._record_outcome(record, PatchOutcome.skipped("function_missing"))
                continue

            original = module.__dict__[method]

            def wrapper(*args: Any, _original: Callable[..., Any] = original, **kwargs: Any) -> Any:
                with redirect_stdout(StringIO()):
                    return _original(*args, **kwargs)

            try:
                self._write(record, module, method, wrapper)
            except Exception as exc:
                self._handle_failure(record, exc, module, True)
                continue
            self._record_outcome(record, PatchOutcome.applied(), module)

    def _run_import_injection(self, module: ModuleType, select: Callable[[_PatchEntry], bool] | None) -> None:
        entries = self._stage_records("import_injection")
        if not entries:
            return

        from .control.handles import PatchOutcome

        for (package, content, alias, _), record in sorted(entries, key=lambda pair: pair[0][3]):
            if (select is not None and not select(record)) or not self._can_run(record) or not self._condition_allows(record, module, True):
                continue
            wrote = True
            try:
                if content is None and alias is None and "." in package:
                    wrote = False
                    module_parts = package.split(".")
                    constructed_name = ""
                    constructed_tree = module.__dict__
                    for part in module_parts:
                        constructed_name += part if constructed_name == "" else "." + part
                        if part not in constructed_tree:
                            component = importlib.import_module(constructed_name)
                            if constructed_tree is module.__dict__:
                                # 只记录写入目标模块命名空间的部分; 更深层写入落在真实包的命名空间中。
                                self._write(record, module, part, component)
                                wrote = True
                            else:
                                constructed_tree[part] = component
                        constructed_tree = constructed_tree[part].__dict__
                else:
                    injected = importlib.import_module(package)
                    if content is not None:
                        injected = getattr(injected, content)
                    alias_name = alias if alias is not None else content if content is not None else package
                    self._write(record, module, alias_name, injected)
            except Exception as exc:
                self._handle_failure(record, exc, module, True)
                continue
            self._record_outcome(record, PatchOutcome.applied() if wrote else PatchOutcome.noop(), module)


class MonkeyZoo:
    """
    模块名到补丁计划的注册表

    ``MonkeyZoo`` 通过上下文管理器暴露单个模块的 ``Monkey``。退出上下文时,
    只有包含有效补丁的计划会保留。每次计划变化都会使 finder 中该模块的 spec 缓存失效。

    Attributes:
        monkeys (dict[str, Monkey]):
            按小写模块名索引的补丁计划
        aliases_fallback (dict[str, str]):
            找不到目标模块时使用的别名模块映射
    """

    def __init__(self, *, state: HotpatcherState | None = None) -> None:
        """
        创建注册表

        Args:
            state (HotpatcherState | None):
                所属状态对象。为 None 时使用默认状态
        """

        self.monkeys: dict[str, Monkey] = {}
        self.aliases_fallback: dict[str, str] = {}
        self._state = state
        self._finders: weakref.WeakSet[HookedMetaPathFinder] = weakref.WeakSet()
        self._alias_handles: dict[str, tuple[str, str, PatchHandle, PatchSet | None]] = {}

    @property
    def state(self) -> HotpatcherState:
        """
        所属状态对象

        Returns:
            HotpatcherState:
                创建时指定的状态, 未指定时为默认状态
        """

        return self._state if self._state is not None else get_default_state()

    def __getitem__(self, module: str | ModuleType) -> Monkey | None:
        fullname = module.__name__ if isinstance(module, ModuleType) else module
        return self.monkeys.get(fullname.casefold())

    def __contains__(self, item: str) -> bool:
        return item.casefold() in self.monkeys

    @contextmanager
    def __call__(self, module: str | ModuleType, *, apply_if_loaded: bool = False) -> Generator[Monkey, None, None]:
        """
        获取模块的补丁计划

        Args:
            module (str | ModuleType):
                目标模块名或模块对象
            apply_if_loaded (bool):
                为 True 时, 若目标模块已在 ``sys.modules`` 中, 退出上下文时把本次新增条目的
                执行后阶段追溯应用到该模块, 见 ``Monkey.apply_to_loaded``

        Yields:
            Monkey:
                目标模块的补丁计划
        """

        fullname = module.__name__ if isinstance(module, ModuleType) else module
        key = fullname.casefold()
        monkey = self.monkeys.get(key, Monkey())
        monkey._bind(self, fullname)
        known = monkey._handle_id_snapshot() if apply_if_loaded else frozenset()
        yield monkey
        if monkey.active:
            self.monkeys[key] = monkey
        else:
            self.monkeys.pop(key, None)
        self.invalidate(fullname)
        if apply_if_loaded:
            loaded = module if isinstance(module, ModuleType) else sys.modules.get(fullname)
            if isinstance(loaded, ModuleType):
                monkey.apply_to_loaded(loaded, handle_ids=monkey._handle_id_snapshot() - known)

    def alias_if_not_exists(self, module: str, alias: str) -> PatchHandle:
        """
        注册模块不存在时使用的别名

        Args:
            module (str):
                原模块名
            alias (str):
                回退使用的模块名

        Returns:
            PatchHandle:
                别名句柄。卸载时若原模块名已在 ``sys.modules`` 中则为 ``requires_restart``
        """

        from .control.handles import PatchStatus, create_patch_handle, unregister_patch_handle
        from .control.patchset import current_patch_context

        key = module.casefold()
        context = current_patch_context()
        owner = context.patch_set if context is not None else None
        state = self.state
        handle = create_patch_handle(ALIAS_HANDLE_KIND, f"{module}->{alias}", stage="alias", register=owner is None, state=state)

        def undo() -> PatchStatus:
            current = self._alias_handles.get(key)
            if current is not None and current[2] is handle:
                del self._alias_handles[key]
                if self.aliases_fallback.get(key) == alias:
                    del self.aliases_fallback[key]
                self.invalidate(module)
            if owner is None:
                unregister_patch_handle(handle.id, state=state)
            return PatchStatus.REQUIRES_RESTART if module in sys.modules else PatchStatus.DEREGISTERED

        if owner is not None:
            owner.adopt_handle(handle, undo=undo)
        previous = self._alias_handles.get(key)
        self._alias_handles[key] = (module, alias, handle, owner)
        self.aliases_fallback[key] = alias
        if previous is not None and previous[3] is None:
            previous[2].status = PatchStatus.DEREGISTERED
            unregister_patch_handle(previous[2].id, state=state)
        self.invalidate(module)
        return handle

    def handles(self) -> list[PatchHandle]:
        """
        列出全部补丁计划和别名的句柄

        Returns:
            list[PatchHandle]:
                按模块名排序的句柄列表, 别名句柄在最后
        """

        result: list[PatchHandle] = []
        for _, monkey in sorted(self.monkeys.items()):
            result.extend(monkey.handles())
        result.extend(item[2] for _, item in sorted(self._alias_handles.items()))
        return result

    def remove(self, handle: PatchHandle | str) -> PatchStatus | None:
        """
        按句柄移除补丁条目或别名

        Args:
            handle (PatchHandle | str):
                句柄或句柄 ID

        Returns:
            PatchStatus | None:
                移除后的句柄状态, 句柄不属于本注册表时为 None
        """

        handle_id = handle if isinstance(handle, str) else handle.id
        for monkey in list(self.monkeys.values()):
            if handle_id in {item.id for item in monkey.handles()}:
                return monkey.remove(handle_id)
        for key, (_, _, alias_handle, owner) in list(self._alias_handles.items()):
            if alias_handle.id != handle_id:
                continue
            status = _undo_owned_handle(owner, alias_handle) if owner is not None else None
            if status is None:
                status = self._undo_alias(key, unregister=owner is None)
            alias_handle.status = status
            return status
        return None

    def discard(self, name: str) -> Monkey | None:
        """
        丢弃模块的补丁计划

        只从计划中移除, 不撤销已经写入模块的修改。无主条目的句柄被注销并标记为
        ``deregistered`` (从未执行) 或 ``requires_restart`` (已执行); 属于补丁集的条目在补丁集
        卸载时报告状态并撤销框架写入。

        Args:
            name (str):
                模块名

        Returns:
            Monkey | None:
                被丢弃的补丁计划, 不存在时为 None
        """

        monkey = self.monkeys.pop(name.casefold(), None)
        self.invalidate(name)
        if monkey is not None:
            monkey._forget_all()
        return monkey

    def invalidate(self, fullname: str) -> None:
        """
        使关联 finder 中该模块的 spec 缓存失效

        Args:
            fullname (str):
                模块名, 不区分大小写
        """

        for finder in self._iter_finders():
            finder.invalidate(fullname)

    def clear(self) -> None:
        """清空全部补丁计划和别名映射, 注销无主句柄, 不撤销已经写入模块的修改"""

        monkeys = list(self.monkeys.values())
        aliases = list(self._alias_handles.values())
        self.monkeys.clear()
        self.aliases_fallback.clear()
        self._alias_handles.clear()
        for finder in self._iter_finders():
            finder.invalidate_caches()
        for monkey in monkeys:
            monkey._forget_all()
        if any(owner is None for _, _, _, owner in aliases):
            from .control.handles import PatchStatus, unregister_patch_handle

            for _, _, alias_handle, owner in aliases:
                if owner is None:
                    alias_handle.status = PatchStatus.DEREGISTERED
                    unregister_patch_handle(alias_handle.id, state=self.state)

    def _undo_alias(self, key: str, *, unregister: bool) -> PatchStatus:
        from .control.handles import PatchStatus, unregister_patch_handle

        module, alias, alias_handle, _ = self._alias_handles.pop(key)
        if self.aliases_fallback.get(key) == alias:
            del self.aliases_fallback[key]
        self.invalidate(module)
        if unregister:
            unregister_patch_handle(alias_handle.id, state=self.state)
        return PatchStatus.REQUIRES_RESTART if module in sys.modules else PatchStatus.DEREGISTERED

    def _iter_finders(self) -> list[HookedMetaPathFinder]:
        finders = list(self._finders)
        state = self._state if self._state is not None else get_default_state()
        state_finder = state.import_hook_finder
        if state_finder is not None and state_finder.zoo is self and state_finder not in finders:
            finders.append(state_finder)
        return finders


def _state_monkey_zoo(state: HotpatcherState) -> MonkeyZoo:
    if state.monkey_zoo is None:
        state.monkey_zoo = MonkeyZoo(state=state)
    elif state.monkey_zoo._state is None:
        state.monkey_zoo._state = state
    return state.monkey_zoo


monkey_zoo = _state_monkey_zoo(get_default_state())
"""补丁计划的注册表实例"""


class LoadingSkipper:
    """
    记录当前线程正在导入的模块以避免递归 hook。

    每个线程使用独立的栈, 其他线程 (例如控制线程) 并发调用 ``find_spec`` 时,
    不会因为本线程正在导入同名模块而拿到未包装的 spec。
    """

    def __init__(self) -> None:
        self._local = threading.local()

    @property
    def currently_loading(self) -> list[str]:
        """
        当前线程正在导入的模块名栈

        Returns:
            list[str]:
                当前线程的模块名栈, 首次访问时创建
        """

        stack = getattr(self._local, "stack", None)
        if stack is None:
            stack = []
            self._local.stack = stack
        return stack

    def __contains__(self, module: str | ModuleType) -> bool:
        fullname = module.__name__ if isinstance(module, ModuleType) else module
        return fullname in self.currently_loading

    @contextmanager
    def __call__(self, module: str | ModuleType) -> Generator[None, None, None]:
        fullname = module.__name__ if isinstance(module, ModuleType) else module
        stack = self.currently_loading
        stack.append(fullname)
        try:
            yield
        finally:
            stack.pop()


class AliasLoader(Loader):
    """将缺失模块名代理到真实模块的加载器。"""

    def __init__(self, alias: str):
        self.alias = alias

    def create_module(self, spec: ModuleSpec) -> ModuleType:
        """
        创建别名模块对象

        Args:
            spec (ModuleSpec):
                目标模块 spec

        Returns:
            ModuleType:
                别名模块导入结果
        """

        return importlib.import_module(self.alias)

    def exec_module(self, module: ModuleType) -> None:
        """
        执行别名模块

        Args:
            module (ModuleType):
                已创建的模块对象
        """

        return None


class HookedMetaPathFinder(MetaPathFinder):
    """按补丁计划查找并包装模块 spec 的 finder。"""

    def __init__(self, zoo: MonkeyZoo, *, state: HotpatcherState | None = None):
        self.cache: dict[str, ModuleSpec] = {}
        self.currently_loading = LoadingSkipper()
        self.zoo = zoo
        self.state = state
        finders = getattr(zoo, "_finders", None)
        if finders is not None:
            finders.add(self)

    def find_spec(
        self,
        fullname: str,
        path: Sequence[bytes | str] | None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        """
        查找并按需包装目标模块 spec

        Args:
            fullname (str):
                完整模块名
            path (Sequence[bytes | str] | None):
                包路径
            target (ModuleType | None):
                reload 目标模块

        Returns:
            ModuleSpec | None:
                已包装的模块 spec, 或不处理时返回 None
        """

        if fullname in self.currently_loading:
            return None

        if fullname in self.cache:
            return self.cache[fullname]

        if fullname == _PACKAGE_NAME or fullname.startswith(f"{_PACKAGE_NAME}."):
            return None

        if fullname in self.zoo:
            with self.currently_loading(fullname):
                spec = importlib.util.find_spec(fullname)
            return self._wrap_and_cache(fullname, spec, self.zoo[fullname])

        alias = self.zoo.aliases_fallback.get(fullname.casefold())
        if alias is None:
            return None

        with self.currently_loading(fullname):
            spec = importlib.util.find_spec(fullname)
        if spec is not None:
            if fullname in self.zoo:
                return self._wrap_and_cache(fullname, spec, self.zoo[fullname])
            return None

        with self.currently_loading(alias):
            alias_spec = importlib.util.find_spec(alias)
        if alias_spec is None:
            return None

        alias_loader = AliasLoader(alias)
        alias_module_spec = ModuleSpec(
            fullname,
            alias_loader,
            origin=f"alias:{alias}",
            is_package=alias_spec.submodule_search_locations is not None,
        )
        if alias_spec.submodule_search_locations is not None:
            alias_module_spec.submodule_search_locations = list(alias_spec.submodule_search_locations)
        self.cache[fullname] = alias_module_spec
        return alias_module_spec

    def invalidate_caches(self) -> None:
        """清空全部 spec 缓存"""

        self.cache.clear()

    def invalidate(self, fullname: str) -> None:
        """
        清除单个模块的 spec 缓存

        补丁计划变化时调用, 避免缓存的 spec 继续引用旧计划。

        Args:
            fullname (str):
                模块名, 不区分大小写
        """

        folded = fullname.casefold()
        for key in [key for key in list(self.cache) if key.casefold() == folded]:
            self.cache.pop(key, None)

    def _wrap_and_cache(
        self,
        fullname: str,
        spec: ModuleSpec | None,
        monkey: Monkey | None,
    ) -> ModuleSpec | None:
        if monkey is None or spec is None:
            return None
        monkey._bind(self.zoo, fullname)
        wrapped = _wrap_spec(fullname, spec, monkey, self)
        if wrapped is None:
            return None
        self.cache[fullname] = wrapped
        return wrapped


class MonkeySourceFileLoader(Loader):
    """加载源码模块并在执行前应用补丁计划。"""

    def __init__(
        self,
        filename: str,
        meta_path_finder: HookedMetaPathFinder | None,
        loader: SourceFileLoader,
        monkey: Monkey,
    ):
        self.filename = filename
        self.meta_path_finder = meta_path_finder
        self.loader = loader
        self.monkey = monkey

    def create_module(self, spec: ModuleSpec) -> ModuleType | None:
        """
        使用默认模块创建逻辑

        Args:
            spec (ModuleSpec):
                目标模块 spec

        Returns:
            ModuleType | None:
                返回 None 表示交给 import 系统默认创建
        """

        return None

    def get_code(self, fullname: str | None = None) -> CodeType:
        """
        读取、补丁并编译模块代码

        Args:
            fullname (str | None):
                完整模块名

        Returns:
            CodeType:
                补丁后的 code object

        Raises:
            ImportError:
                缺少模块名或无法加载 code object 时抛出。
        """

        if fullname is None:
            raise ImportError("Missing module name for patched loader")
        return self._patched_code(fullname, None)

    def exec_module(self, module: ModuleType) -> None:
        """
        执行补丁后的模块代码

        Args:
            module (ModuleType):
                目标模块对象
        """

        code_object = self._patched_code(module.__name__, module)
        loading_context = self.meta_path_finder.currently_loading(module.__name__) if self.meta_path_finder is not None else nullcontext()
        with loading_context:
            self.monkey.eval_premodule(module)
            execution_context = redirect_stdout(StringIO()) if self.monkey.suppress_module_output(module) else nullcontext()
            with execution_context:
                self.monkey.eval_import_injection(module)
                exec(code_object, module.__dict__)
            self.monkey.eval_function(module)
            self.monkey.eval_module(module)
            self.monkey.eval_prohibit_output(module)

    def _patched_code(self, fullname: str, module: ModuleType | None) -> CodeType:
        if not self.monkey.has_cache_side_effect:
            code_object = self.loader.get_code(fullname)
            if code_object is None:
                raise ImportError(f"Could not load code object for {fullname!r}")
            return self.monkey.eval_bytecode(code_object, module=module)

        filename = self.filename
        with open(filename, mode="rb") as file:
            source = importlib.util.decode_source(file.read())

        source, filename = self.monkey.eval_source(source, filename, module=module)
        tree = ast.parse(source, filename, "exec")
        tree = self.monkey.eval_ast(tree, module=module)
        ast.fix_missing_locations(tree)
        code_object = compile(tree, filename, "exec")  # ty: ignore[invalid-argument-type]
        return self.monkey.eval_bytecode(code_object, module=module)


class PostExecLoader(Loader):
    """
    包装非源码 loader 并在其执行前后应用补丁计划

    用于扩展模块、无源码 ``.pyc``、zipimport 等 loader。``create_module`` 与 ``exec_module``
    委托给原 loader, 其他属性 (``get_code``、``get_source``、``is_package``、
    ``get_resource_reader`` 等) 通过属性透传访问。源码、AST 和字节码补丁记录为
    ``skipped:unsupported_loader``。

    模块执行前补丁在原 loader 的 ``create_module`` 之后、``exec_module`` 之前执行。
    单阶段初始化的扩展模块在 ``create_module`` 中已经完成初始化 (其 ``exec_module`` 基本为空操作),
    因此对这类模块, 执行前补丁看到的是已初始化的模块。

    Attributes:
        loader (Loader):
            被包装的原 loader
        monkey (Monkey):
            补丁计划
        meta_path_finder (HookedMetaPathFinder | None):
            创建本 loader 的 finder, 用于递归保护
    """

    def __init__(self, loader: Loader, monkey: Monkey, meta_path_finder: HookedMetaPathFinder | None = None):
        """
        创建包装 loader

        Args:
            loader (Loader):
                被包装的原 loader
            monkey (Monkey):
                补丁计划
            meta_path_finder (HookedMetaPathFinder | None):
                创建本 loader 的 finder
        """

        self.loader = loader
        self.monkey = monkey
        self.meta_path_finder = meta_path_finder

    def __getattr__(self, name: str) -> Any:
        """
        把未定义的属性透传给原 loader

        Args:
            name (str):
                属性名

        Returns:
            Any:
                原 loader 的属性值

        Raises:
            AttributeError:
                原 loader 没有该属性时抛出。
        """

        loader = self.__dict__.get("loader")
        if loader is None:
            raise AttributeError(name)
        return getattr(loader, name)

    def create_module(self, spec: ModuleSpec) -> ModuleType | None:
        """
        委托原 loader 创建模块

        Args:
            spec (ModuleSpec):
                目标模块 spec

        Returns:
            ModuleType | None:
                原 loader 创建的模块, 返回 None 表示交给 import 系统默认创建
        """

        create_module = getattr(self.loader, "create_module", None)
        if create_module is None:
            return None
        return create_module(spec)

    def exec_module(self, module: ModuleType) -> None:
        """
        委托原 loader 执行模块, 并在前后应用补丁计划

        Args:
            module (ModuleType):
                目标模块对象
        """

        loading_context = self.meta_path_finder.currently_loading(module.__name__) if self.meta_path_finder is not None else nullcontext()
        with loading_context:
            self.monkey.skip_code_stages("unsupported_loader")
            self.monkey.eval_premodule(module)
            execution_context = redirect_stdout(StringIO()) if self.monkey.suppress_module_output(module) else nullcontext()
            with execution_context:
                self.monkey.eval_import_injection(module)
                self.loader.exec_module(module)
            self.monkey.eval_function(module)
            self.monkey.eval_module(module)
            self.monkey.eval_prohibit_output(module)


def set_strict_mode(enabled: bool, *, state: HotpatcherState | None = None) -> None:
    """
    设置补丁严格模式

    严格模式下 import 阶段补丁抛出的异常会在记录 ``failed`` 结果后从 import 继续抛出;
    关闭时 (默认) 异常交给 ``capture_exception`` 并继续导入。只影响之后执行的补丁。

    Args:
        enabled (bool):
            是否启用
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
    """

    (state or get_default_state()).strict_mode = bool(enabled)


def is_strict_mode(*, state: HotpatcherState | None = None) -> bool:
    """
    查询补丁严格模式

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        bool:
            严格模式启用时返回 True
    """

    return bool((state or get_default_state()).strict_mode)


def install_import_hook(*, state: HotpatcherState | None = None) -> HookedMetaPathFinder:
    """
    安装 import hook

    重复调用是安全的。进程中只会安装一个 ``HookedMetaPathFinder``,
    并且只会包装一次 ``importlib.util.spec_from_file_location``。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        HookedMetaPathFinder:
            已安装的 finder 实例
    """

    active_state = state or get_default_state()
    zoo = _state_monkey_zoo(active_state)
    if active_state.import_hook_finder is None:
        active_state.import_hook_finder = HookedMetaPathFinder(zoo, state=active_state)

    finder = active_state.import_hook_finder
    if finder not in sys.meta_path:
        sys.meta_path.insert(0, finder)

    if importlib.util.spec_from_file_location is not _spec_from_file_location_wrapper:
        active_state.import_hook_wrapped_spec_from_file_location = importlib.util.spec_from_file_location
        importlib.util.spec_from_file_location = _spec_from_file_location_wrapper  # ty: ignore[invalid-assignment]

    return finder


def uninstall_import_hook(*, state: HotpatcherState | None = None) -> None:
    """
    卸载 import hook

    会从 ``sys.meta_path`` 中移除 finder, 清理 finder 缓存,
    并恢复 ``importlib.util.spec_from_file_location``。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
    """

    active_state = state or get_default_state()
    finder = active_state.import_hook_finder
    if finder is not None:
        while finder in sys.meta_path:
            sys.meta_path.remove(finder)
        finder.invalidate_caches()

    if importlib.util.spec_from_file_location is _spec_from_file_location_wrapper:
        importlib.util.spec_from_file_location = active_state.import_hook_wrapped_spec_from_file_location or _original_spec_from_file_location
        active_state.import_hook_wrapped_spec_from_file_location = None


def is_import_hook_installed(*, state: HotpatcherState | None = None) -> bool:
    """
    检查 import hook 是否已安装

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        bool:
            finder 当前位于 ``sys.meta_path`` 中时返回 True
    """
    active_state = state or get_default_state()
    finder = active_state.import_hook_finder
    return finder is not None and finder in sys.meta_path


def register_hook(
    module: str,
    function: str,
    hooker: Callable[[Any, ModuleType], Any],
    force: bool = False,
    *,
    state: HotpatcherState | None = None,
) -> PatchHandle:
    """
    注册函数级补丁

    Args:
        module (str):
            目标模块名
        function (str):
            目标函数名
        hooker (Callable[[Any, ModuleType], Any]):
            接收原函数和模块对象, 返回替换函数的补丁函数
        force (bool):
            函数不存在时是否仍写入返回值
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        PatchHandle:
            补丁句柄
    """
    zoo = _state_monkey_zoo(state or get_default_state())
    with zoo(module) as monkey:
        handle = monkey.patch_function(function, hooker, add_if_not_exists=force)
    return handle


def register_customize_hook(
    module: str,
    hooker: Callable[[ModuleType], Any],
    *,
    state: HotpatcherState | None = None,
) -> PatchHandle:
    """
    注册模块级补丁

    Args:
        module (str):
            目标模块名
        hooker (Callable[[ModuleType], Any]):
            模块代码执行后调用的补丁函数
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        PatchHandle:
            补丁句柄
    """
    zoo = _state_monkey_zoo(state or get_default_state())
    with zoo(module) as monkey:
        handle = monkey.patch_module(hooker)
    return handle


def _active_hook_targets() -> list[tuple[MonkeyZoo, HotpatcherState, HookedMetaPathFinder | None]]:
    # 按 sys.meta_path 顺序收集已安装 finder 的注册表和状态, 最后回退到默认状态, 保持单状态行为不变。
    targets: list[tuple[MonkeyZoo, HotpatcherState, HookedMetaPathFinder | None]] = []
    seen_zoos: list[MonkeyZoo] = []
    for finder in list(sys.meta_path):
        if isinstance(finder, HookedMetaPathFinder) and not any(finder.zoo is zoo for zoo in seen_zoos):
            seen_zoos.append(finder.zoo)
            targets.append((finder.zoo, finder.state if finder.state is not None else finder.zoo.state, finder))
    default_state = get_default_state()
    default_zoo = _state_monkey_zoo(default_state)
    if not any(default_zoo is zoo for zoo in seen_zoos):
        targets.append((default_zoo, default_state, None))
    return targets


def _spec_from_file_location_wrapper(*args: Any, **kwargs: Any) -> ModuleSpec | None:
    targets = _active_hook_targets()
    wrapped_spec_from_file_location = next(
        (state.import_hook_wrapped_spec_from_file_location for _, state, _ in targets if state.import_hook_wrapped_spec_from_file_location is not None),
        _original_spec_from_file_location,
    )
    spec = wrapped_spec_from_file_location(*args, **kwargs)
    if spec is None:
        return spec
    for zoo, _, _ in targets:
        monkey = zoo[spec.name]
        if monkey is None:
            continue
        monkey._bind(zoo, spec.name)
        wrapped = _wrap_spec(spec.name, spec, monkey, None)
        return wrapped if wrapped is not None else spec
    return spec


def _wrap_spec(fullname: str, spec: ModuleSpec, monkey: Monkey, finder: HookedMetaPathFinder | None) -> ModuleSpec | None:
    live = sys.modules.get(fullname)
    if live is not None and getattr(live, "__spec__", None) is spec:
        # importlib.util.find_spec 对已导入模块返回其 __spec__ (reload 场景), 复制后再替换 loader, 不修改在用的 spec。
        spec = copy.copy(spec)
    original_loader = _unwrap_loader(spec.loader)
    if original_loader is not spec.loader:
        spec.loader = original_loader
    if _is_source_file_spec(spec):
        assert isinstance(spec.loader, SourceFileLoader)
        spec.loader = MonkeySourceFileLoader(
            filename=spec.loader.path,
            meta_path_finder=finder,
            loader=spec.loader,
            monkey=monkey,
        )
        return spec
    if _is_post_exec_spec(spec):
        assert spec.loader is not None
        spec.loader = PostExecLoader(spec.loader, monkey, finder)
        return spec
    return None


def _unwrap_loader(loader: Any) -> Any:
    while isinstance(loader, (MonkeySourceFileLoader, PostExecLoader)):
        loader = loader.loader
    return loader


def _is_source_file_spec(spec: ModuleSpec | None) -> bool:
    return spec is not None and hasattr(spec, "loader") and isinstance(spec.loader, SourceFileLoader) and hasattr(spec.loader, "path") and isinstance(spec.loader.path, (str, bytes, os.PathLike))


def _is_post_exec_spec(spec: ModuleSpec | None) -> bool:
    loader = getattr(spec, "loader", None) if spec is not None else None
    if spec is None or loader is None:
        return False
    if loader in (BuiltinImporter, FrozenImporter) or isinstance(loader, (BuiltinImporter, FrozenImporter, AliasLoader, MonkeySourceFileLoader, PostExecLoader)):
        return False
    if spec.origin in ("built-in", "frozen"):
        return False
    # NamespaceLoader 在 3.11 起才公开, 3.10 为私有的 _NamespaceLoader, 按类名结构化识别。
    if type(loader).__name__ in ("NamespaceLoader", "_NamespaceLoader"):
        return False
    return callable(getattr(loader, "exec_module", None))


def _describe_entry(module_name: str, stage: str, item: Any) -> str:
    try:
        if stage == "function":
            return f"{module_name}:{item[0]}"
        if stage == "output_prohibition":
            return f"{module_name}:{item if item is not None else '*'}"
        if stage == "import_injection":
            package, content, alias = item[0], item[1], item[2]
            return f"{module_name}:{alias if alias is not None else content if content is not None else package}"
    except Exception:
        return module_name
    return module_name


def _namespace_restorer(record: _PatchEntry, namespace: dict[str, Any], name: str, value: Any, previous: Any, token: object) -> Callable[[], Any]:
    def restore() -> Any:
        from .control.handles import PatchStatus
        from .control.journal import NOTSET

        if record.write_tokens.get((id(namespace), name)) is not token:
            return None
        if namespace.get(name, NOTSET) is not value:
            # 命名空间中已是其他对象 (例如之后叠加的补丁), 不覆盖, 如实报告需要重启。
            return PatchStatus.REQUIRES_RESTART
        if previous is NOTSET:
            namespace.pop(name, None)
        else:
            namespace[name] = previous
        return None

    return restore


def _undo_owned_handle(owner: PatchSet, handle: PatchHandle) -> PatchStatus | None:
    # 通过补丁集日志撤销单个句柄 (框架写入 + 移除回调, LIFO); 日志中没有该句柄的条目时返回 None。
    from .control.handles import PatchOutcome, PatchStatus

    report = owner.journal.undo(handle_id=handle.id)
    if not report.results:
        return None
    status = PatchStatus.DEREGISTERED
    for result in report.results:
        if result.error is not None:
            handle.record_outcome(PatchOutcome.failed(result.error, reason="undo_failed"))
            status = _merge_status(status, PatchStatus.FAILED)
        else:
            status = _merge_status(status, _coerce_status(result.result))
    return status


def _coerce_status(value: Any) -> PatchStatus:
    from .control.handles import PatchStatus

    if isinstance(value, PatchStatus) and value.value in _STATUS_PRIORITY:
        return value
    if isinstance(value, str) and value in _STATUS_PRIORITY:
        return PatchStatus(value)
    return PatchStatus.REVERTED


def _merge_status(current: PatchStatus, new: PatchStatus) -> PatchStatus:
    if _STATUS_PRIORITY.get(new.value, 0) > _STATUS_PRIORITY.get(current.value, 0):
        return new
    return current
