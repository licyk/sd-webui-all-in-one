"""可配置的 traceback 文件名隐藏工具"""

from __future__ import annotations

import importlib.util
import os
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec, SourceFileLoader
from types import CodeType, ModuleType
from typing import Any
from zipimport import zipimporter

from .exceptions import capture_exception
from .state import HotpatcherState, get_default_state

DEFAULT_FILENAME_TEMPLATE = "<hidden {name}>"


class LoadingSkipper:
    """记录当前正在加载的模块以避免重复查找。"""

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


class StackShadowFinder(MetaPathFinder):
    """
    为目标模块替换 traceback 文件名的 finder

    finder 会拦截匹配前缀的模块导入, 读取源码并用合成文件名重新 compile,
    从而让异常栈中的文件名不暴露真实路径。

    Attributes:
        prefixes (tuple[str, ...]):
            需要隐藏的模块名前缀
        filename_template (str):
            合成文件名模板
        include_source_loaders (bool):
            是否处理普通源码 loader
        cache (dict[str, ModuleSpec]):
            已包装的模块 spec 缓存
    """

    def __init__(
        self,
        prefixes: Iterable[str],
        filename_template: str = DEFAULT_FILENAME_TEMPLATE,
        include_source_loaders: bool = True,
    ):
        self.prefixes = _normalize_prefixes(prefixes)
        self.filename_template = filename_template
        self.include_source_loaders = include_source_loaders
        self.cache: dict[str, ModuleSpec] = {}
        self.currently_loading = LoadingSkipper()

    def configure(
        self,
        prefixes: Iterable[str],
        filename_template: str = DEFAULT_FILENAME_TEMPLATE,
        include_source_loaders: bool = True,
    ) -> None:
        """
        重新配置栈隐藏规则

        Args:
            prefixes (Iterable[str]):
                需要隐藏的模块名前缀
            filename_template (str):
                合成文件名模板
            include_source_loaders (bool):
                是否处理普通源码 loader
        """

        self.prefixes = _normalize_prefixes(prefixes)
        self.filename_template = filename_template
        self.include_source_loaders = include_source_loaders
        self.invalidate_caches()

    def find_spec(  # ty: ignore[invalid-method-override]
        self,
        fullname: str,
        path: list[str] | None,
        target: ModuleType | None = None,
    ) -> ModuleSpec | None:
        """
        查找并包装需要隐藏的模块 spec

        Args:
            fullname (str):
                完整模块名
            path (list[str] | None):
                包路径
            target (ModuleType | None):
                reload 目标模块

        Returns:
            ModuleSpec | None:
                已替换 loader 的 spec, 或不处理时返回 None
        """

        if fullname in self.currently_loading or not _matches_prefix(fullname, self.prefixes):
            return None

        if fullname in self.cache:
            return self.cache[fullname]

        with self.currently_loading(fullname):
            spec = importlib.util.find_spec(fullname)

        if spec is None or spec.loader is None:
            return None

        if not _can_shadow_loader(spec.loader, self.include_source_loaders):
            return None

        try:
            source = spec.loader.get_source(fullname)  # ty: ignore[unresolved-attribute]
        except Exception:
            capture_exception()
            return None

        if source is None:
            return None

        spec.loader = StackShadowSourceLoader(
            fullname=fullname,
            source=source,
            meta_path_finder=self,
            filename_template=self.filename_template,
        )
        self.cache[fullname] = spec
        return spec

    def invalidate_caches(self) -> None:
        """清空 finder 缓存"""

        self.cache.clear()


class StackShadowSourceLoader(Loader):
    """使用隐藏文件名执行替换源码的加载器。"""

    def __init__(
        self,
        fullname: str,
        source: str | bytes,
        meta_path_finder: StackShadowFinder,
        filename_template: str,
    ):
        self.fullname = fullname
        self.source = source
        self.meta_path_finder = meta_path_finder
        self.filename_template = filename_template

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
        使用合成文件名编译源码

        Args:
            fullname (str | None):
                完整模块名

        Returns:
            CodeType:
                带隐藏文件名的 code object
        """

        fullname = fullname or self.fullname
        filename = _format_filename(self.filename_template, fullname)
        source = _normalize_line_endings(self.source)
        return compile(source, filename, "exec", optimize=2, dont_inherit=True)

    def exec_module(self, module: ModuleType) -> None:
        """
        执行隐藏文件名后的模块代码

        Args:
            module (ModuleType):
                目标模块对象
        """

        code_object = self.get_code(module.__name__)
        with self.meta_path_finder.currently_loading(module.__name__):
            exec(code_object, module.__dict__)


def install_stack_shadower(
    prefixes: Iterable[str] | str,
    filename_template: str = DEFAULT_FILENAME_TEMPLATE,
    include_source_loaders: bool = True,
    *,
    state: HotpatcherState | None = None,
) -> StackShadowFinder:
    """
    安装或重新配置栈隐藏 finder

    Args:
        prefixes (Iterable[str] | str):
            需要隐藏的模块名前缀。字符串会按逗号拆分。
        filename_template (str):
            合成文件名模板, 支持 ``{name}``、``{fullname}``、``{module}``。
        include_source_loaders (bool):
            是否处理普通源码 loader。zipimporter 始终按源码能力判断。
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        StackShadowFinder:
            已安装或已重新配置的 finder
    """

    active_state = state or get_default_state()
    normalized_prefixes = _normalize_prefixes(prefixes)
    if active_state.stack_shadow_finder is None:
        active_state.stack_shadow_finder = StackShadowFinder(
            normalized_prefixes,
            filename_template=filename_template,
            include_source_loaders=include_source_loaders,
        )
    else:
        active_state.stack_shadow_finder.configure(
            normalized_prefixes,
            filename_template=filename_template,
            include_source_loaders=include_source_loaders,
        )

    finder = active_state.stack_shadow_finder
    if finder not in sys.meta_path:
        sys.meta_path.insert(0, finder)  # ty: ignore[invalid-argument-type]

    return finder


def uninstall_stack_shadower(*, state: HotpatcherState | None = None) -> None:
    """
    卸载栈隐藏 finder

    会从 ``sys.meta_path`` 中移除 finder 并清空缓存。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。
    """

    active_state = state or get_default_state()
    finder = active_state.stack_shadow_finder
    if finder is None:
        return

    while finder in sys.meta_path:
        sys.meta_path.remove(finder)
    finder.invalidate_caches()


def is_stack_shadower_installed(*, state: HotpatcherState | None = None) -> bool:
    """
    检查栈隐藏 finder 是否已安装

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        bool:
            finder 当前位于 ``sys.meta_path`` 中时返回 True
    """

    active_state = state or get_default_state()
    finder = active_state.stack_shadow_finder
    return finder is not None and finder in sys.meta_path


def configure_stack_shadower_from_env(*, state: HotpatcherState | None = None) -> StackShadowFinder | None:
    """
    根据环境变量安装栈隐藏 finder

    只有 ``SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW=1`` 时才会安装。

    Args:
        state (HotpatcherState | None):
            可选状态对象。为 None 时使用默认状态。

    Returns:
        StackShadowFinder | None:
            已安装的 finder。未启用时返回 None。
    """

    if os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW") != "1":
        return None

    prefixes = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_PREFIXES", "sd_webui_all_in_one_hotpatcher")
    template = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_TEMPLATE", DEFAULT_FILENAME_TEMPLATE)
    include_source_loaders = os.getenv("SD_WEBUI_ALL_IN_ONE_HOTPATCHER_SHADOW_SOURCE_LOADERS", "1") != "0"
    return install_stack_shadower(
        prefixes,
        filename_template=template,
        include_source_loaders=include_source_loaders,
        state=state,
    )


def _normalize_prefixes(prefixes: Iterable[str] | str) -> tuple[str, ...]:
    if isinstance(prefixes, str):
        raw_prefixes = prefixes.split(",")
    else:
        raw_prefixes = list(prefixes)
    return tuple(prefix.strip() for prefix in raw_prefixes if prefix and prefix.strip())


def _matches_prefix(fullname: str, prefixes: tuple[str, ...]) -> bool:
    return any(fullname == prefix or fullname.startswith(f"{prefix}.") for prefix in prefixes)


def _can_shadow_loader(loader: Any, include_source_loaders: bool) -> bool:
    if isinstance(loader, zipimporter):
        return hasattr(loader, "get_source")
    if include_source_loaders and isinstance(loader, SourceFileLoader):
        return hasattr(loader, "get_source")
    return False


def _normalize_line_endings(source: str | bytes) -> str | bytes:
    if isinstance(source, bytes):
        return source.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return source.replace("\r\n", "\n").replace("\r", "\n")


def _format_filename(template: str, fullname: str) -> str:
    try:
        return template.format(name=fullname, fullname=fullname, module=fullname)
    except Exception:
        capture_exception()
        return DEFAULT_FILENAME_TEMPLATE.format(name=fullname)
