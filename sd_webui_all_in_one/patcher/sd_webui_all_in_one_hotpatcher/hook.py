"""import 阶段热补丁框架"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import os
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager, nullcontext, redirect_stdout
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec, SourceFileLoader
from io import StringIO
from types import CodeType, ModuleType
from typing import Any

from .exceptions import capture_exception
from .mutable import CodeWrapper
from .state import HotpatcherState, get_default_state

_PACKAGE_NAME = __name__.split(".", 1)[0]
_original_spec_from_file_location = importlib.util.spec_from_file_location


class Monkey:
    """
    单个目标模块的补丁计划

    保存源码、AST、字节码、模块对象和函数级补丁, 在目标模块第一次导入时由
    ``MonkeySourceFileLoader`` 按固定顺序执行。

    属性:
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

    @property
    def active(self) -> bool:
        """
        是否存在有效补丁

        返回:
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

        返回:
            bool:
                存在源码或 AST 补丁时返回 True
        """

        return bool(self.source_patches or self.ast_patches)

    def patch_function(
        self,
        function_name: str,
        hooker: Callable[[Any, ModuleType], Any],
        priority: int = 100,
        add_if_not_exists: bool = False,
    ) -> None:
        """
        注册函数替换补丁

        参数:
            function_name (str):
                目标函数名
            hooker (Callable[[Any, ModuleType], Any]):
                接收原函数和模块对象, 返回替换对象的补丁函数
            priority (int):
                执行优先级, 数字越小越早执行
            add_if_not_exists (bool):
                函数不存在时是否仍写入补丁返回值
        """

        self.function_patches.append((function_name, hooker, priority, add_if_not_exists))

    def patch_premodule(self, hooker: Callable[[ModuleType], Any], priority: int = 100) -> None:
        """
        注册模块代码执行前补丁

        参数:
            hooker (Callable[[ModuleType], Any]):
                接收模块对象的补丁函数
            priority (int):
                执行优先级, 数字越小越早执行
        """

        self.premodule_patches.append((hooker, priority))

    def patch_module(self, hooker: Callable[[ModuleType], Any], priority: int = 100) -> None:
        """
        注册模块代码执行后补丁

        参数:
            hooker (Callable[[ModuleType], Any]):
                接收模块对象的补丁函数
            priority (int):
                执行优先级, 数字越小越早执行
        """

        self.module_patches.append((hooker, priority))

    def patch_sources(
        self,
        hooker: Callable[[str, str], str | tuple[str] | tuple[str, str]],
        priority: int = 100,
    ) -> None:
        """
        注册源码补丁

        参数:
            hooker (Callable[[str, str], str | tuple[str] | tuple[str, str]]):
                接收源码和文件名, 返回新源码或新源码加新文件名的函数
            priority (int):
                执行优先级, 数字越小越早执行
        """

        self.source_patches.append((hooker, priority))

    def patch_ast(
        self,
        hooker: ast.NodeTransformer | ast.NodeVisitor | Callable[[ast.AST], ast.AST],
        priority: int = 100,
    ) -> None:
        """
        注册 AST 补丁

        参数:
            hooker (ast.NodeTransformer | ast.NodeVisitor | Callable[[ast.AST], ast.AST]):
                AST visitor、transformer 或接收 AST 并返回 AST 的函数
            priority (int):
                执行优先级, 数字越小越早执行
        """

        self.ast_patches.append((hooker, priority))

    def patch_bytecode(self, hooker: Callable[[CodeWrapper], Any], priority: int = 100) -> None:
        """
        注册字节码补丁

        参数:
            hooker (Callable[[CodeWrapper], Any]):
                接收 code object 可变代理的补丁函数
            priority (int):
                执行优先级, 数字越小越早执行
        """

        self.bytecode_patches.append((hooker, priority))

    def prohibit_output(self, method: str | None = None) -> None:
        """
        注册 stdout 输出抑制

        参数:
            method (str | None):
                需要抑制输出的方法名。为 None 时抑制整个模块执行阶段输出。
        """

        self.output_prohibition.append(method)

    def inject_import(
        self,
        package: str,
        content: str | None = None,
        alias: str | None = None,
        priority: int = 100,
    ) -> None:
        """
        注册 import 注入

        参数:
            package (str):
                需要导入的包或模块名
            content (str | None):
                从模块中取出的成员名
            alias (str | None):
                注入到目标模块时使用的名称
            priority (int):
                执行优先级, 数字越小越早执行
        """

        self.import_injections.append((package, content, alias, priority))

    def eval_source(self, source: str, filename: str) -> tuple[str, str]:
        """
        执行源码补丁链

        参数:
            source (str):
                原始源码
            filename (str):
                原始文件名

        返回:
            tuple[str, str]:
                补丁后的源码和文件名

        抛出:
            TypeError:
                源码补丁返回值类型不受支持时抛出。
            ValueError:
                源码补丁返回的元组长度不受支持时抛出。
        """

        for hooker, _ in sorted(self.source_patches, key=lambda x: x[1]):
            try:
                result = hooker(source, filename)
                if isinstance(result, str):
                    source = result
                elif isinstance(result, tuple):
                    if len(result) == 1:
                        source = result[0]
                    elif len(result) == 2:
                        source, filename = result
                    else:
                        raise ValueError("Invalid source patch return value")
                else:
                    raise TypeError("Source patch must return str, tuple[str], or tuple[str, str]")
            except Exception:
                capture_exception()
        return source, filename

    def eval_ast(self, tree: ast.AST) -> ast.AST:
        """
        执行 AST 补丁链

        参数:
            tree (ast.AST):
                原始 AST

        返回:
            ast.AST:
                补丁后的 AST
        """

        for hooker, _ in sorted(self.ast_patches, key=lambda x: x[1]):
            try:
                if isinstance(hooker, ast.NodeTransformer):
                    tree = hooker.visit(tree)
                elif isinstance(hooker, ast.NodeVisitor):
                    hooker.visit(tree)
                else:
                    tree = hooker(tree)
            except Exception:
                capture_exception()
        return tree

    def eval_bytecode(self, code_object: CodeType) -> CodeType:
        """
        执行字节码补丁链

        参数:
            code_object (CodeType):
                原始 code object

        返回:
            CodeType:
                补丁后的 code object
        """

        code_wrapper = CodeWrapper(code_object)
        for hooker, _ in sorted(self.bytecode_patches, key=lambda x: x[1]):
            try:
                hooker(code_wrapper)
            except Exception:
                capture_exception()
        return code_wrapper.conclude()

    def eval_premodule(self, module: ModuleType) -> None:
        """
        执行模块代码前补丁链

        参数:
            module (ModuleType):
                正在导入的模块对象
        """

        for hooker, _ in sorted(self.premodule_patches, key=lambda x: x[1]):
            try:
                hooker(module)
            except Exception:
                capture_exception()

    def eval_module(self, module: ModuleType) -> None:
        """
        执行模块代码后补丁链

        参数:
            module (ModuleType):
                已执行代码的模块对象
        """

        for hooker, _ in sorted(self.module_patches, key=lambda x: x[1]):
            try:
                hooker(module)
            except Exception:
                capture_exception()

    def eval_function(self, module: ModuleType) -> None:
        """
        执行函数替换补丁链

        参数:
            module (ModuleType):
                已执行代码的模块对象
        """

        for function_name, hooker, _, add_if_not_exists in sorted(self.function_patches, key=lambda x: x[2]):
            try:
                if add_if_not_exists or function_name in module.__dict__:
                    original = module.__dict__.get(function_name)
                    replacement = hooker(original, module)
                    if replacement is not None:
                        module.__dict__[function_name] = replacement
            except Exception:
                capture_exception()

    def eval_prohibit_output(self, module: ModuleType) -> None:
        """
        执行方法级输出抑制补丁

        参数:
            module (ModuleType):
                已执行代码的模块对象
        """

        for method in self.output_prohibition:
            if method is None or method not in module.__dict__:
                continue

            original = module.__dict__[method]

            def wrapper(*args: Any, _original: Callable[..., Any] = original, **kwargs: Any) -> Any:
                with redirect_stdout(StringIO()):
                    return _original(*args, **kwargs)

            module.__dict__[method] = wrapper

    def eval_import_injection(self, module: ModuleType) -> None:
        """
        执行 import 注入补丁链

        参数:
            module (ModuleType):
                正在导入的模块对象
        """

        for package, content, alias, _ in sorted(self.import_injections, key=lambda x: x[3]):
            try:
                if content is None and alias is None and "." in package:
                    module_parts = package.split(".")
                    constructed_name = ""
                    constructed_tree = module.__dict__
                    for part in module_parts:
                        constructed_name += part if constructed_name == "" else "." + part
                        if part not in constructed_tree:
                            component = importlib.import_module(constructed_name)
                            constructed_tree[part] = component
                        constructed_tree = constructed_tree[part].__dict__
                    continue

                injected = importlib.import_module(package)
                if content is not None:
                    injected = getattr(injected, content)
                alias_name = alias if alias is not None else content if content is not None else package
                module.__dict__[alias_name] = injected
            except Exception:
                capture_exception()


class MonkeyZoo:
    """
    模块名到补丁计划的注册表

    ``MonkeyZoo`` 通过上下文管理器暴露单个模块的 ``Monkey``。退出上下文时,
    只有包含有效补丁的计划会保留。

    属性:
        monkeys (dict[str, Monkey]):
            按小写模块名索引的补丁计划
        aliases_fallback (dict[str, str]):
            找不到目标模块时使用的别名模块映射
    """

    def __init__(self) -> None:
        self.monkeys: dict[str, Monkey] = {}
        self.aliases_fallback: dict[str, str] = {}

    def __getitem__(self, module: str | ModuleType) -> Monkey | None:
        fullname = module.__name__ if isinstance(module, ModuleType) else module
        return self.monkeys.get(fullname.casefold())

    def __contains__(self, item: str) -> bool:
        return item.casefold() in self.monkeys

    @contextmanager
    def __call__(self, module: str | ModuleType) -> Iterator[Monkey]:
        fullname = module.__name__ if isinstance(module, ModuleType) else module
        key = fullname.casefold()
        monkey = self.monkeys.get(key, Monkey())
        yield monkey
        if monkey.active:
            self.monkeys[key] = monkey
        else:
            self.monkeys.pop(key, None)

    def alias_if_not_exists(self, module: str, alias: str) -> None:
        """
        注册模块不存在时使用的别名

        参数:
            module (str):
                原模块名
            alias (str):
                回退使用的模块名
        """

        self.aliases_fallback[module.casefold()] = alias

    def clear(self) -> None:
        """清空全部补丁计划和别名映射"""

        self.monkeys.clear()
        self.aliases_fallback.clear()


def _state_monkey_zoo(state: HotpatcherState) -> MonkeyZoo:
    if state.monkey_zoo is None:
        state.monkey_zoo = MonkeyZoo()
    return state.monkey_zoo


monkey_zoo = _state_monkey_zoo(get_default_state())
"""补丁计划的注册表实例"""


class LoadingSkipper:
    """记录当前正在导入的模块以避免递归 hook。"""

    def __init__(self) -> None:
        self.currently_loading: list[str] = []

    def __contains__(self, module: str | ModuleType) -> bool:
        fullname = module.__name__ if isinstance(module, ModuleType) else module
        return fullname in self.currently_loading

    @contextmanager
    def __call__(self, module: str | ModuleType) -> Iterator[None]:
        fullname = module.__name__ if isinstance(module, ModuleType) else module
        self.currently_loading.append(fullname)
        try:
            yield
        finally:
            self.currently_loading.pop()


class AliasLoader(Loader):
    """将缺失模块名代理到真实模块的加载器。"""

    def __init__(self, alias: str):
        self.alias = alias

    def create_module(self, spec: ModuleSpec) -> ModuleType:
        """
        创建别名模块对象

        参数:
            spec (ModuleSpec):
                目标模块 spec

        返回:
            ModuleType:
                别名模块导入结果
        """

        return importlib.import_module(self.alias)

    def exec_module(self, module: ModuleType) -> None:
        """
        执行别名模块

        参数:
            module (ModuleType):
                已创建的模块对象
        """

        return None


class HookedMetaPathFinder(MetaPathFinder):
    """按补丁计划查找并包装模块 spec 的 finder。"""

    def __init__(self, zoo: MonkeyZoo):
        self.cache: dict[str, ModuleSpec] = {}
        self.currently_loading = LoadingSkipper()
        self.zoo = zoo

    def find_spec(
        self,
        fullname: str,
        path: Sequence[bytes | str] | None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        """
        查找并按需包装目标模块 spec

        参数:
            fullname (str):
                完整模块名
            path (Sequence[bytes | str] | None):
                包路径
            target (ModuleType | None):
                reload 目标模块

        返回:
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
        self.cache.clear()

    def _wrap_and_cache(
        self,
        fullname: str,
        spec: ModuleSpec | None,
        monkey: Monkey | None,
    ) -> ModuleSpec | None:
        if monkey is None or not _is_source_file_spec(spec):
            return None

        assert spec is not None
        assert isinstance(spec.loader, SourceFileLoader)
        spec.loader = MonkeySourceFileLoader(
            filename=spec.loader.path,
            meta_path_finder=self,
            loader=spec.loader,
            monkey=monkey,
        )
        self.cache[fullname] = spec
        return spec


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

        参数:
            spec (ModuleSpec):
                目标模块 spec

        返回:
            ModuleType | None:
                返回 None 表示交给 import 系统默认创建
        """

        return None

    def get_code(self, fullname: str | None = None) -> CodeType:
        """
        读取、补丁并编译模块代码

        参数:
            fullname (str | None):
                完整模块名

        返回:
            CodeType:
                补丁后的 code object

        抛出:
            ImportError:
                缺少模块名或无法加载 code object 时抛出。
        """

        if fullname is None:
            raise ImportError("Missing module name for patched loader")

        if not self.monkey.has_cache_side_effect:
            code_object = self.loader.get_code(fullname)
            if code_object is None:
                raise ImportError(f"Could not load code object for {fullname!r}")
            return self.monkey.eval_bytecode(code_object)

        filename = self.filename
        with open(filename, mode="rb") as file:
            source = importlib.util.decode_source(file.read())

        source, filename = self.monkey.eval_source(source, filename)
        tree = ast.parse(source, filename, "exec")
        tree = self.monkey.eval_ast(tree)
        ast.fix_missing_locations(tree)
        code_object = compile(tree, filename, "exec")  # ty: ignore[invalid-argument-type]
        return self.monkey.eval_bytecode(code_object)

    def exec_module(self, module: ModuleType) -> None:
        """
        执行补丁后的模块代码

        参数:
            module (ModuleType):
                目标模块对象
        """

        code_object = self.get_code(module.__name__)
        loading_context = self.meta_path_finder.currently_loading(module.__name__) if self.meta_path_finder is not None else nullcontext()
        with loading_context:
            self.monkey.eval_premodule(module)
            execution_context = redirect_stdout(StringIO()) if None in self.monkey.output_prohibition else nullcontext()
            with execution_context:
                self.monkey.eval_import_injection(module)
                exec(code_object, module.__dict__)
            self.monkey.eval_function(module)
            self.monkey.eval_module(module)
            self.monkey.eval_prohibit_output(module)


def install_import_hook(*, state: HotpatcherState | None = None) -> HookedMetaPathFinder:
    """
    安装 import hook

    重复调用是安全的。进程中只会安装一个 ``HookedMetaPathFinder``,
    并且只会包装一次 ``importlib.util.spec_from_file_location``。

    参数:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    返回:
        HookedMetaPathFinder:
            已安装的 finder 实例
    """

    active_state = state or get_default_state()
    zoo = _state_monkey_zoo(active_state)
    if active_state.import_hook_finder is None:
        active_state.import_hook_finder = HookedMetaPathFinder(zoo)

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

    参数:
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

    参数:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    返回:
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
) -> None:
    """
    注册函数级补丁

    参数:
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
    """
    zoo = _state_monkey_zoo(state or get_default_state())
    with zoo(module) as monkey:
        monkey.patch_function(function, hooker, add_if_not_exists=force)


def register_customize_hook(
    module: str,
    hooker: Callable[[ModuleType], Any],
    *,
    state: HotpatcherState | None = None,
) -> None:
    """
    注册模块级补丁

    参数:
        module (str):
            目标模块名
        hooker (Callable[[ModuleType], Any]):
            模块代码执行后调用的补丁函数
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
    """
    zoo = _state_monkey_zoo(state or get_default_state())
    with zoo(module) as monkey:
        monkey.patch_module(hooker)


def _spec_from_file_location_wrapper(*args: Any, **kwargs: Any) -> ModuleSpec | None:
    active_state = get_default_state()
    wrapped_spec_from_file_location = active_state.import_hook_wrapped_spec_from_file_location
    assert wrapped_spec_from_file_location is not None
    spec = wrapped_spec_from_file_location(*args, **kwargs)
    zoo = _state_monkey_zoo(active_state)
    if spec is None or spec.name not in zoo or not _is_source_file_spec(spec):
        return spec

    assert isinstance(spec.loader, SourceFileLoader)
    spec.loader = MonkeySourceFileLoader(
        filename=spec.loader.path,
        meta_path_finder=None,
        loader=spec.loader,
        monkey=zoo[spec.name],  # ty: ignore[invalid-argument-type]
    )
    return spec


def _is_source_file_spec(spec: ModuleSpec | None) -> bool:
    return spec is not None and hasattr(spec, "loader") and isinstance(spec.loader, SourceFileLoader) and hasattr(spec.loader, "path") and isinstance(spec.loader.path, (str, bytes, os.PathLike))
