"""不可变 code object 的定向修改工具"""

from __future__ import annotations

import types
from collections.abc import Callable, Iterator
from typing import Any


class TupleWrapper:
    """
    tuple 字段的可变代理

    主要用于修改 ``code.co_consts`` 这类不可变元组字段。

    属性:
        tup (tuple[Any, ...]):
            原始元组
        field_name (str | None):
            当前元组在父对象上的字段名
        parent (Any):
            父级可变代理对象
    """

    def __init__(self, tup: tuple[Any, ...], field_name: str | None = None, parent: Any = None):
        self.tup = tup
        self.field_name = field_name
        self.parent = parent
        self._overrides: list[Any] | None = None

    def __setitem__(self, key: int, value: Any) -> None:
        if self._overrides is None:
            self._overrides = list(self.tup)
        self._overrides[key] = value
        if self.field_name and self.parent:
            setattr(self.parent, self.field_name, self)

    def __getitem__(self, item: int) -> Any:
        if self._overrides is not None:
            return self._overrides[item]
        return self.tup[item]

    def __iter__(self) -> Iterator[Any]:
        if self._overrides is not None:
            return iter(self._overrides)
        return iter(self.tup)

    def __len__(self) -> int:
        if self._overrides is not None:
            return len(self._overrides)
        return len(self.tup)

    def replace_primitive(self, original: Any, replacement: Any) -> None:
        """
        替换与原始值相等的元素

        参数:
            original (Any):
                要匹配的原始值
            replacement (Any):
                替换后的值
        """

        for i, item in enumerate(self):
            if item == original:
                self[i] = replacement

    def replace(
        self,
        predicate: Callable[[Any], bool],
        replacement: Callable[[Any], Any],
        /,
        only_first: bool = False,
    ) -> None:
        """
        按条件替换元素

        嵌套 tuple 和 code object 会先包装成可变代理, 再传入 ``replacement``。

        参数:
            predicate (Callable[[Any], bool]):
                判断元素是否需要替换的函数
            replacement (Callable[[Any], Any]):
                接收原元素或可变代理, 返回替换结果的函数
            only_first (bool):
                是否只替换第一个匹配项
        """

        for i, item in enumerate(self):
            if not predicate(item):
                continue

            wrapped = CodeWrapper(item) if isinstance(item, types.CodeType) else item
            wrapped = TupleWrapper(wrapped) if isinstance(wrapped, tuple) else wrapped
            result = replacement(wrapped)

            if isinstance(result, TupleWrapper):
                self[i] = result.conclude()
            elif isinstance(result, CodeWrapper):
                self[i] = result.conclude()
            else:
                self[i] = result

            if only_first:
                return

    def replace_method_noop(self, method_name: str, /, only_first: bool = False) -> None:
        """
        把指定名称的嵌套函数替换为空函数

        参数:
            method_name (str):
                需要替换的函数名
            only_first (bool):
                是否只替换第一个匹配项
        """

        for i, item in enumerate(self):
            if isinstance(item, types.CodeType) and item.co_name == method_name:
                generated_module = compile(
                    f"def {method_name}(*args, **kwargs): pass",
                    "<sd_webui_all_in_one_hotpatcher generated>",
                    "exec",
                )
                self[i] = generated_module.co_consts[0]
                if only_first:
                    return

    def operate(self, predicate: Callable[[Any], bool], /, only_first: bool = False):
        """
        遍历匹配的嵌套可变对象

        参数:
            predicate (Callable[[Any], bool]):
                判断元素是否需要暴露为可变代理的函数
            only_first (bool):
                是否只处理第一个匹配项

        Yields:
            TupleWrapper | CodeWrapper:
                匹配元素对应的可变代理
        """

        mutable_types = (types.CodeType, tuple)

        for i, item in enumerate(self):
            if not isinstance(item, mutable_types) or not predicate(item):
                continue

            wrapped = CodeWrapper(item) if isinstance(item, types.CodeType) else TupleWrapper(item)
            try:
                yield wrapped
            finally:
                if isinstance(wrapped, TupleWrapper):
                    self[i] = wrapped.conclude()
                elif isinstance(wrapped, CodeWrapper):
                    self[i] = wrapped.conclude()

            if only_first:
                return

    def conclude(self) -> tuple[Any, ...]:
        """
        生成最终 tuple

        返回:
            tuple[Any, ...]:
                应用所有覆盖值后的 tuple
        """

        if self._overrides is not None:
            return tuple(self._overrides)
        return self.tup


class CodeWrapper:
    """
    code object 的可变代理

    基于 ``types.CodeType.replace`` 暂存字段修改, 最终通过 ``conclude`` 生成新的
    code object。

    属性:
        _code (types.CodeType):
            原始 code object
        _overrides (dict[str, Any]):
            待写入的新字段值
    """

    def __init__(self, code: types.CodeType):
        self._code = code
        self._overrides: dict[str, Any] = {}

    def __setattr__(self, key: str, value: Any) -> None:
        if key in {"_code", "_overrides"}:
            self.__dict__[key] = value
            return
        self._overrides[key] = value

    def __getattr__(self, key: str) -> Any:
        if key in self._overrides:
            return self._overrides[key]

        attr = getattr(self._code, key)
        if isinstance(attr, tuple):
            return TupleWrapper(attr, field_name=key, parent=self)
        return attr

    def conclude(self) -> types.CodeType:
        """
        生成最终 code object

        返回:
            types.CodeType:
                应用所有覆盖字段后的 code object
        """

        if not self._overrides:
            return self._code

        overrides = dict(self._overrides)
        for key, value in overrides.items():
            if isinstance(value, TupleWrapper):
                overrides[key] = value.conclude()
        return self._code.replace(**overrides)
