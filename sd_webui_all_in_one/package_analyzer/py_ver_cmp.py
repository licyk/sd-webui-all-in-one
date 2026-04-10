"""Python 软件包版本比较器

基于 PEP 440 规范实现版本号解析和比较.

参考:
    - https://peps.python.org/pep-0440/
    - https://packaging.python.org/en/latest/specifications/version-specifiers
"""

from __future__ import annotations

import re
from typing import (
    Callable,
    NamedTuple,
)

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class PyWhlVersionComponent(NamedTuple):
    """Python 版本号组件

    参考: https://peps.python.org/pep-0440

    Attributes:
        epoch (int):
            版本纪元号, 用于处理不兼容的重大更改, 默认为 0
        release (tuple[int, ...]):
            发布版本号段, 主版本号的数字部分, 如 ``(1, 2, 3)``, 使用不可变元组
        pre_l (str | None):
            规范化后的预发布标签, 只有 ``'a'``, ``'b'``, ``'rc'`` 三种
        pre_n (int | None):
            预发布版本编号, 与预发布标签配合使用
        post_n (int | None):
            后发布版本编号, 如 ``1.0.post1`` 中的 ``1``, 或 ``1.0-1`` 中的 ``1``
        dev_n (int | None):
            开发版本编号, 如 ``dev1`` 中的数字
        local (str | None):
            本地版本标识符, 加号后面的部分
        is_wildcard (bool):
            标记是否包含通配符, 用于版本范围匹配
    """

    epoch: int
    release: tuple[int, ...]
    pre_l: str | None
    pre_n: int | None
    post_n: int | None
    dev_n: int | None
    local: str | None
    is_wildcard: bool


# Pre-release 标签规范化映射 (PEP 440)
# alpha -> a, beta -> b, c/pre/preview -> rc
_PRE_RELEASE_NORMALIZATION: dict[str, str] = {
    "alpha": "a",
    "beta": "b",
    "c": "rc",
    "pre": "rc",
    "preview": "rc",
}

# Pre-release 标签排序
_PRE_RELEASE_ORDER: dict[str, int] = {
    "a": 0,
    "b": 1,
    "rc": 2,
}


class PyWhlVersionComparison:
    """Python 版本号比较工具

    基于 PEP 440 规范实现版本号的解析、比较和兼容性匹配.

    使用示例:
        ```python
        # 常规版本匹配
        PyWhlVersionComparison("2.0.0") < PyWhlVersionComparison("2.3.0+cu118")  # True
        PyWhlVersionComparison("2.0") > PyWhlVersionComparison("0.9")  # True
        PyWhlVersionComparison("1.3") <= PyWhlVersionComparison("1.2.2")  # False

        # 兼容性版本匹配 (~= 语义), 使用 ~ 操作符
        PyWhlVersionComparison("1.0*") == ~PyWhlVersionComparison("1.0a1")  # True
        PyWhlVersionComparison("0.9*") == ~PyWhlVersionComparison("1.0")  # False
        ```

    Attributes:
        version (str):
            版本号字符串
    """

    def __init__(
        self,
        version: str,
    ) -> None:
        """初始化 Python 版本号比较工具

        Args:
            version (str):
                版本号字符串
        """
        self.version = version

    def __lt__(
        self,
        other: object,
    ) -> bool:
        """实现 ``<`` 符号的版本比较

        Args:
            other (object):
                用于比较的对象

        Returns:
            bool: 如果此版本小于另一个版本则返回 ``True``
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_lt_v2(self.version, other.version)

    def __gt__(
        self,
        other: object,
    ) -> bool:
        """实现 ``>`` 符号的版本比较

        Args:
            other (object):
                用于比较的对象

        Returns:
            bool: 如果此版本大于另一个版本则返回 ``True``
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_gt_v2(self.version, other.version)

    def __le__(
        self,
        other: object,
    ) -> bool:
        """实现 ``<=`` 符号的版本比较

        Args:
            other (object):
                用于比较的对象

        Returns:
            bool: 如果此版本小于等于另一个版本则返回 ``True``
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_le_v2(self.version, other.version)

    def __ge__(
        self,
        other: object,
    ) -> bool:
        """实现 ``>=`` 符号的版本比较

        Args:
            other (object):
                用于比较的对象

        Returns:
            bool: 如果此版本大于等于另一个版本则返回 ``True``
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_ge_v2(self.version, other.version)

    def __eq__(
        self,
        other: object,
    ) -> bool:
        """实现 ``==`` 符号的版本比较

        Args:
            other (object):
                用于比较的对象

        Returns:
            bool: 如果此版本等于另一个版本则返回 ``True``
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_eq_v2(self.version, other.version)

    def __ne__(
        self,
        other: object,
    ) -> bool:
        """实现 ``!=`` 符号的版本比较

        Args:
            other (object):
                用于比较的对象

        Returns:
            bool: 如果此版本不等于另一个版本则返回 ``True``
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return not self.is_v1_eq_v2(self.version, other.version)

    def __invert__(self) -> PyWhlVersionMatcher:
        """使用 ``~`` 操作符实现兼容性版本匹配 (``~=`` 的语义)

        Returns:
            PyWhlVersionMatcher: 兼容性版本匹配器
        """
        return PyWhlVersionMatcher(self.version)

    # 提取版本标识符组件的正则表达式
    # ref: https://peps.python.org/pep-0440/#appendix-b-parsing-version-strings-with-regular-expressions
    VERSION_PATTERN = r"""
        v?
        (?:
            (?:(?P<epoch>[0-9]+)!)?                           # epoch
            (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
            (?P<pre>                                          # pre-release
                [-_\.]?
                (?P<pre_l>alpha|a|beta|b|preview|pre|c|rc)
                [-_\.]?
                (?P<pre_n>[0-9]+)?
            )?
            (?P<post>                                         # post release
                (?:-(?P<post_n1>[0-9]+))
                |
                (?:
                    [-_\.]?
                    (?P<post_l>post|rev|r)
                    [-_\.]?
                    (?P<post_n2>[0-9]+)?
                )
            )?
            (?P<dev>                                          # dev release
                [-_\.]?
                (?P<dev_l>dev)
                [-_\.]?
                (?P<dev_n>[0-9]+)?
            )?
        )
        (?:\+(?P<local>[a-z0-9]+(?:[-_\.][a-z0-9]+)*))?       # local version
    """

    WHL_VERSION_PARSE_REGEX = re.compile(
        r"^\s*" + VERSION_PATTERN + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    )
    """编译后的 PEP 440 版本号解析正则表达式"""

    def parse_version(
        self,
        version_str: str,
    ) -> PyWhlVersionComponent:
        """解析 Python 软件包版本号

        将版本号字符串解析为 ``PyWhlVersionComponent`` 命名元组, 自动进行 PEP 440 规范化:
        - Pre-release 标签: ``alpha`` → ``a``, ``beta`` → ``b``, ``c``/``pre``/``preview`` → ``rc``
        - 隐式编号: ``1.0a`` → ``1.0a0``, ``1.0.post`` → ``1.0.post0``, ``1.0.dev`` → ``1.0.dev0``
        - 隐式 post: ``1.0-1`` → ``1.0.post1``
        - Local version: ``-`` 和 ``_`` 转换为 ``.``

        Args:
            version_str (str):
                Python 软件包版本号字符串

        Returns:
            PyWhlVersionComponent: 版本组件的命名元组

        Raises:
            ValueError: 如果 Python 版本号不符合 PEP 440 规范
        """
        # 检测并剥离通配符
        wildcard = version_str.endswith(".*") or version_str.endswith("*")
        clean_str = version_str.rstrip("*").rstrip(".") if wildcard else version_str

        match = self.WHL_VERSION_PARSE_REGEX.match(clean_str)
        if not match:
            logger.debug("未知的版本号字符串: %s", version_str)
            raise ValueError(f"未知的版本号字符串: {version_str}")

        components = match.groupdict()

        # 处理 release 段 (允许空字符串)
        release_str = components["release"] or "0"
        release_segments = tuple(int(seg) for seg in release_str.split("."))

        # 规范化 pre-release 标签
        pre_l: str | None = None
        pre_n: int | None = None
        if components["pre_l"]:
            raw_label = components["pre_l"].lower()
            pre_l = _PRE_RELEASE_NORMALIZATION.get(raw_label, raw_label)
            pre_n = int(components["pre_n"]) if components["pre_n"] else 0

        # 规范化 post-release
        post_n: int | None = None
        if components["post_n1"]:
            post_n = int(components["post_n1"])
        elif components["post_l"]:
            post_n = int(components["post_n2"]) if components["post_n2"] else 0

        # 规范化 dev-release
        dev_n: int | None = None
        if components["dev_l"]:
            dev_n = int(components["dev_n"]) if components["dev_n"] else 0

        # 规范化 local version
        local = components["local"]
        if local:
            local = local.replace("-", ".").replace("_", ".")

        return PyWhlVersionComponent(
            epoch=int(components["epoch"] or 0),
            release=release_segments,
            pre_l=pre_l,
            pre_n=pre_n,
            post_n=post_n,
            dev_n=dev_n,
            local=local,
            is_wildcard=wildcard,
        )

    def compare_version_objects(
        self,
        v1: PyWhlVersionComponent,
        v2: PyWhlVersionComponent,
    ) -> int:
        """比较两个已解析的版本号组件

        PEP 440 排序规则::

            .devN < aN < bN < rcN < <no suffix> < .postN

        对于 local version::

            无 local < 有 local

        Args:
            v1 (PyWhlVersionComponent):
                第 1 个 Python 版本号标识符组件
            v2 (PyWhlVersionComponent):
                第 2 个 Python 版本号标识符组件

        Returns:
            int: 如果 v1 > v2 则返回正数, v1 < v2 则返回负数, v1 == v2 则返回 ``0``
        """
        # 1. 比较 epoch
        if v1.epoch != v2.epoch:
            return v1.epoch - v2.epoch

        # 2. 比较 release segment (自动填充零, 使用不可变元组操作)
        max_len = max(len(v1.release), len(v2.release))
        r1 = v1.release + (0,) * (max_len - len(v1.release))
        r2 = v2.release + (0,) * (max_len - len(v2.release))

        for n1, n2 in zip(r1, r2):
            if n1 != n2:
                return n1 - n2

        # 3. 比较 suffix 部分 (使用排序键方法)
        key1 = self._version_suffix_key(v1)
        key2 = self._version_suffix_key(v2)

        if key1 < key2:
            return -1
        elif key1 > key2:
            return 1

        # 4. 比较 local version
        return self._compare_local_version(v1, v2)

    @staticmethod
    def _version_suffix_key(
        v: PyWhlVersionComponent,
    ) -> tuple[int, int, int, int, int, int]:
        """生成版本后缀的排序键

        PEP 440 排序规则 (在同一 release segment 内)::

            .devN < aN < bN < rcN < <no suffix> < .postN

        每个后缀组合都可以附带 ``.devN``, 例如::

            1.0a1.dev1 < 1.0a1 < 1.0a1.post1.dev1 < 1.0a1.post1

        排序键结构: ``(pre_key, pre_n, post_key, post_n, dev_key, dev_n)``

        Args:
            v (PyWhlVersionComponent):
                版本号组件

        Returns:
            tuple[int, int, int, int, int, int]: 排序键元组
        """
        if v.pre_l is not None:
            pre_key = _PRE_RELEASE_ORDER[v.pre_l]
            pre_n = v.pre_n if v.pre_n is not None else 0
        elif v.dev_n is not None and v.post_n is None:
            pre_key = -1
            pre_n = 0
        else:
            pre_key = 3
            pre_n = 0

        if v.post_n is not None:
            post_key = 1
            post_n = v.post_n
        else:
            post_key = 0
            post_n = 0

        if v.dev_n is not None:
            dev_key = 0
            dev_n = v.dev_n
        else:
            dev_key = 1
            dev_n = 0

        return (pre_key, pre_n, post_key, post_n, dev_key, dev_n)

    @staticmethod
    def _compare_local_version(
        v1: PyWhlVersionComponent,
        v2: PyWhlVersionComponent,
    ) -> int:
        """比较 local version 部分

        PEP 440 规则:
        - 无 local < 有 local (local version 大于对应的公共版本)
        - 按 ``.`` 分割成段
        - 纯数字段按数值比较
        - 包含字母的段按字典序比较 (不区分大小写)
        - 数字段 > 字母段
        - 段数多的 > 段数少的 (前提是前面的段都相同)

        Args:
            v1 (PyWhlVersionComponent):
                第 1 个版本号组件
            v2 (PyWhlVersionComponent):
                第 2 个版本号组件

        Returns:
            int: 比较结果
        """
        if v1.local is None and v2.local is None:
            return 0
        elif v1.local is None:
            return -1
        elif v2.local is None:
            return 1
        else:
            parts1 = v1.local.split(".")
            parts2 = v2.local.split(".")

            for p1, p2 in zip(parts1, parts2):
                is_num1 = p1.isdigit()
                is_num2 = p2.isdigit()

                if is_num1 and is_num2:
                    cmp = int(p1) - int(p2)
                    if cmp != 0:
                        return cmp
                elif is_num1:
                    return 1
                elif is_num2:
                    return -1
                else:
                    p1_lower = p1.lower()
                    p2_lower = p2.lower()
                    if p1_lower < p2_lower:
                        return -1
                    elif p1_lower > p2_lower:
                        return 1

            return len(parts1) - len(parts2)

    def compare_versions(
        self,
        version1: str,
        version2: str,
    ) -> int:
        """比较两个版本字符串

        Args:
            version1 (str):
                版本号 1
            version2 (str):
                版本号 2

        Returns:
            int: 如果 version1 > version2 则返回正数, 小于则返回负数, 相等则返回 ``0``
        """
        v1 = self.parse_version(version1)
        v2 = self.parse_version(version2)
        return self.compare_version_objects(v1, v2)

    def compatible_version_matcher(
        self,
        spec_version: str,
    ) -> Callable[[str], bool]:
        """PEP 440 兼容性版本匹配 (``~=`` 操作符)

        PEP 440 规则::

            ~= X.Y   等价于 >= X.Y, == X.*
            ~= X.Y.Z 等价于 >= X.Y.Z, == X.Y.*

        注意: ``~=`` 不能用于单段版本号 (如 ``~=1``)

        Args:
            spec_version (str):
                规范版本号字符串

        Returns:
            Callable[[str], bool]: 一个接受版本号字符串参数的判断函数

        Raises:
            ValueError: 如果版本号只有单段 (如 ``1``)
        """
        spec = self.parse_version(spec_version)

        if len(spec.release) < 2:
            logger.debug("~= 操作符不能用于单段版本号: %s", spec_version)
            raise ValueError(f"~= 操作符不能用于单段版本号: {spec_version}")

        prefix_length = len(spec.release) - 1
        prefix_pattern = spec.release[:prefix_length]

        def _is_compatible(version_str: str) -> bool:
            target = self.parse_version(version_str)
            target_prefix = target.release[:prefix_length]
            if len(target_prefix) < prefix_length:
                target_prefix = target_prefix + (0,) * (prefix_length - len(target_prefix))
            if target_prefix != prefix_pattern:
                return False
            return self.compare_version_objects(target, spec) >= 0

        return _is_compatible

    def version_match(
        self,
        spec: str,
        version: str,
    ) -> bool:
        """PEP 440 版本前缀匹配

        Args:
            spec (str):
                版本匹配表达式, 如 ``'1.1.*'``
            version (str):
                需要检测的实际版本号, 如 ``'1.1a1'``

        Returns:
            bool: 是否匹配
        """
        spec_parts = spec.split("+", 1)
        spec_main = spec_parts[0].rstrip(".*")
        has_wildcard = spec.endswith(".*") and "+" not in spec

        try:
            spec_ver = self.parse_version(spec_main)
        except ValueError:
            return False

        target_ver = self.parse_version(version.split("+", 1)[0])

        if has_wildcard:
            return (
                target_ver.release[: len(spec_ver.release)] == spec_ver.release
                and target_ver.epoch == spec_ver.epoch
            )
        else:
            return self.compare_versions(spec_main, version) == 0

    def is_v1_ge_v2(
        self,
        v1: str,
        v2: str,
    ) -> bool:
        """查看 Python 版本号 v1 是否大于或等于 v2

        使用示例:
            ```python
            cmp = PyWhlVersionComparison("1.0")
            cmp.is_v1_ge_v2("1.1", "1.0")  # True
            cmp.is_v1_ge_v2("1.0", "1.0")  # True
            cmp.is_v1_ge_v2("0.9", "1.0")  # False
            ```

        Args:
            v1 (str):
                第 1 个 Python 软件包版本号
            v2 (str):
                第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 >= v2 则返回 ``True``
        """
        return self.compare_versions(v1, v2) >= 0

    def is_v1_gt_v2(
        self,
        v1: str,
        v2: str,
    ) -> bool:
        """查看 Python 版本号 v1 是否大于 v2

        Args:
            v1 (str):
                第 1 个 Python 软件包版本号
            v2 (str):
                第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 > v2 则返回 ``True``
        """
        return self.compare_versions(v1, v2) > 0

    def is_v1_eq_v2(
        self,
        v1: str,
        v2: str,
    ) -> bool:
        """查看 Python 版本号 v1 是否等于 v2

        Args:
            v1 (str):
                第 1 个 Python 软件包版本号
            v2 (str):
                第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 == v2 则返回 ``True``
        """
        return self.compare_versions(v1, v2) == 0

    def is_v1_lt_v2(
        self,
        v1: str,
        v2: str,
    ) -> bool:
        """查看 Python 版本号 v1 是否小于 v2

        Args:
            v1 (str):
                第 1 个 Python 软件包版本号
            v2 (str):
                第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 < v2 则返回 ``True``
        """
        return self.compare_versions(v1, v2) < 0

    def is_v1_le_v2(
        self,
        v1: str,
        v2: str,
    ) -> bool:
        """查看 Python 版本号 v1 是否小于或等于 v2

        Args:
            v1 (str):
                第 1 个 Python 软件包版本号
            v2 (str):
                第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 <= v2 则返回 ``True``
        """
        return self.compare_versions(v1, v2) <= 0

    def is_v1_c_eq_v2(
        self,
        v1: str,
        v2: str,
    ) -> bool:
        """查看 Python 版本号 v2 是否与 v1 兼容 (``~=`` 兼容性版本匹配)

        使用示例:
            ```python
            cmp = PyWhlVersionComparison("1.0")
            cmp.is_v1_c_eq_v2("1.4.5", "1.4.6")  # True  (>= 1.4.5 且 == 1.4.*)
            cmp.is_v1_c_eq_v2("1.4.5", "1.5.0")  # False (不满足 == 1.4.*)
            ```

        Args:
            v1 (str):
                规范版本号, 由 ``~=`` 符号指定
            v2 (str):
                待检查的版本号

        Returns:
            bool: 如果 v2 与 v1 兼容则返回 ``True``
        """
        func = self.compatible_version_matcher(v1)
        return func(v2)


class PyWhlVersionMatcher:
    """Python 兼容性版本匹配器, 用于实现 ``~=`` 操作符的语义

    Attributes:
        spec_version (str):
            规范版本号
        comparison (PyWhlVersionComparison):
            Python 版本号比较工具实例
    """

    def __init__(
        self,
        spec_version: str,
    ) -> None:
        """初始化 Python 兼容性版本匹配器

        Args:
            spec_version (str):
                规范版本号
        """
        self.spec_version = spec_version
        self.comparison = PyWhlVersionComparison(spec_version)
        self._matcher_func = self.comparison.compatible_version_matcher(spec_version)

    def __eq__(
        self,
        other: object,
    ) -> bool:
        """实现 ``~version == other_version`` 的语义

        Args:
            other (object):
                用于比较的对象, 支持 ``str``, ``PyWhlVersionComparison``, ``PyWhlVersionMatcher``

        Returns:
            bool: 如果版本兼容则返回 ``True``
        """
        if isinstance(other, str):
            return self._matcher_func(other)
        elif isinstance(other, PyWhlVersionComparison):
            return self._matcher_func(other.version)
        elif isinstance(other, PyWhlVersionMatcher):
            return self.spec_version == other.spec_version
        return NotImplemented

    def __repr__(self) -> str:
        return f"~{self.spec_version}"
