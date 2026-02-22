"""Python 软件包版本比较器"""

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
        epoch (int): 版本纪元号, 用于处理不兼容的重大更改, 默认为 0
        release (list[int]): 发布版本号段, 主版本号的数字部分, 如 [1, 2, 3]
        pre_l (str | None): 预发布标签, 包括 'a', 'b', 'rc', 'alpha' 等
        pre_n (int | None): 预发布版本编号, 与预发布标签配合使用
        post_n1 (int | None): 后发布版本编号, 格式如 1.0-1 中的数字
        post_l (str | None): 后发布标签, 如 'post', 'rev', 'r' 等
        post_n2 (int | None): 后发布版本编号, 格式如 1.0-post1 中的数字
        dev_l (str | None): 开发版本标签, 通常为 'dev'
        dev_n (int | None): 开发版本编号, 如 dev1 中的数字
        local (str | None): 本地版本标识符, 加号后面的部分
        is_wildcard (bool): 标记是否包含通配符, 用于版本范围匹配
    """

    epoch: int
    """版本纪元号, 用于处理不兼容的重大更改, 默认为 0"""

    release: list[int]
    """发布版本号段, 主版本号的数字部分, 如 [1, 2, 3]"""

    pre_l: str | None
    """预发布标签, 包括 'a', 'b', 'rc', 'alpha' 等"""

    pre_n: int | None
    """预发布版本编号, 与预发布标签配合使用"""

    post_n1: int | None
    """后发布版本编号, 格式如 1.0-1 中的数字"""

    post_l: str | None
    """后发布标签, 如 'post', 'rev', 'r' 等"""

    post_n2: int | None
    """post_n2 (int | None): 后发布版本编号, 格式如 1.0-post1 中的数字"""

    dev_l: str | None
    """开发版本标签, 通常为 'dev'"""

    dev_n: int | None
    """开发版本编号, 如 dev1 中的数字"""

    local: str | None
    """本地版本标识符, 加号后面的部分"""

    is_wildcard: bool
    """标记是否包含通配符, 用于版本范围匹配"""


class PyWhlVersionComparison:
    """Python 版本号比较工具

    使用:
    ```python
    # 常规版本匹配
    PyWhlVersionComparison("2.0.0") < PyWhlVersionComparison("2.3.0+cu118") # True
    PyWhlVersionComparison("2.0") > PyWhlVersionComparison("0.9") # True
    PyWhlVersionComparison("1.3") <= PyWhlVersionComparison("1.2.2") # False

    # 通配符版本匹配, 需要在不包含通配符的版本对象中使用 ~ 符号
    PyWhlVersionComparison("1.0*") == ~PyWhlVersionComparison("1.0a1") # True
    PyWhlVersionComparison("0.9*") == ~PyWhlVersionComparison("1.0") # False
    ```

    Attributes:
        VERSION_PATTERN (str): 提去 Wheel 版本号的正则表达式
        WHL_VERSION_PARSE_REGEX (re.Pattern): 编译后的用于解析 Wheel 版本号的工具
        version (str): 版本号字符串
    """

    def __init__(self, version: str) -> None:
        """初始化 Python 版本号比较工具

        Args:
            version (str): 版本号字符串
        """
        self.version = version

    def __lt__(self, other: object) -> bool:
        """实现 < 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本小于另一个版本
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_lt_v2(self.version, other.version)

    def __gt__(self, other: object) -> bool:
        """实现 > 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本大于另一个版本
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_gt_v2(self.version, other.version)

    def __le__(self, other: object) -> bool:
        """实现 <= 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本小于等于另一个版本
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_le_v2(self.version, other.version)

    def __ge__(self, other: object) -> bool:
        """实现 >= 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本大于等于另一个版本
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_ge_v2(self.version, other.version)

    def __eq__(self, other: object) -> bool:
        """实现 == 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本等于另一个版本
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return self.is_v1_eq_v2(self.version, other.version)

    def __ne__(self, other: object) -> bool:
        """实现 != 符号的版本比较

        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本不等于另一个版本
        """
        if not isinstance(other, PyWhlVersionComparison):
            return NotImplemented
        return not self.is_v1_eq_v2(self.version, other.version)

    def __invert__(self) -> "PyWhlVersionMatcher":
        """使用 ~ 操作符实现兼容性版本匹配 (~= 的语义)

        Returns:
            PyWhlVersionMatcher: 兼容性版本匹配器
        """
        return PyWhlVersionMatcher(self.version)

    # 提取版本标识符组件的正则表达式
    # ref:
    # https://peps.python.org/pep-0440
    # https://packaging.python.org/en/latest/specifications/version-specifiers
    VERSION_PATTERN = r"""
        v?
        (?:
            (?:(?P<epoch>[0-9]+)!)?                           # epoch
            (?P<release>[0-9]+(?:\.[0-9]+)*)                  # release segment
            (?P<pre>                                          # pre-release
                [-_\.]?
                (?P<pre_l>(a|b|c|rc|alpha|beta|pre|preview))
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

    # 编译正则表达式
    WHL_VERSION_PARSE_REGEX = re.compile(
        r"^\s*" + VERSION_PATTERN + r"\s*$",
        re.VERBOSE | re.IGNORECASE,
    )

    def parse_version(self, version_str: str) -> PyWhlVersionComponent:
        """解释 Python 软件包版本号

        Args:
            version_str (str): Python 软件包版本号

        Returns:
            PyWhlVersionComponent: 版本组件的命名元组

        Raises:
            ValueError: 如果 Python 版本号不符合 PEP440 规范
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
        release_segments = [int(seg) for seg in release_str.split(".")]

        # 构建命名元组
        return PyWhlVersionComponent(
            epoch=int(components["epoch"] or 0),
            release=release_segments,
            pre_l=components["pre_l"],
            pre_n=int(components["pre_n"]) if components["pre_n"] else None,
            post_n1=int(components["post_n1"]) if components["post_n1"] else None,
            post_l=components["post_l"],
            post_n2=int(components["post_n2"]) if components["post_n2"] else None,
            dev_l=components["dev_l"],
            dev_n=int(components["dev_n"]) if components["dev_n"] else None,
            local=components["local"],
            is_wildcard=wildcard,
        )

    def compare_version_objects(self, v1: PyWhlVersionComponent, v2: PyWhlVersionComponent) -> int:
        """比较两个版本字符串 Python 软件包版本号

        Args:
            v1 (PyWhlVersionComponent): 第 1 个 Python 版本号标识符组件
            v2 (PyWhlVersionComponent): 第 2 个 Python 版本号标识符组件

        Returns:
            int: 如果版本号 1 大于 版本号 2, 则返回`1`, 小于则返回`-1`, 如果相等则返回`0`
        """

        # 比较 epoch
        if v1.epoch != v2.epoch:
            return v1.epoch - v2.epoch

        # 对其 release 长度, 缺失部分补 0
        if len(v1.release) != len(v2.release):
            for _ in range(abs(len(v1.release) - len(v2.release))):
                if len(v1.release) < len(v2.release):
                    v1.release.append(0)
                else:
                    v2.release.append(0)

        # 比较 release
        for n1, n2 in zip(v1.release, v2.release):
            if n1 != n2:
                return n1 - n2
        # 如果 release 长度不同, 较短的版本号视为较小 ?
        # 但是这样是行不通的! 比如 0.15.0 和 0.15, 处理后就会变成 [0, 15, 0] 和 [0, 15]
        # 计算结果就会变成 len([0, 15, 0]) > len([0, 15])
        # 但 0.15.0 和 0.15 实际上是一样的版本
        # if len(v1.release) != len(v2.release):
        #     return len(v1.release) - len(v2.release)

        # 比较 pre-release
        if v1.pre_l and not v2.pre_l:
            return -1  # pre-release 小于正常版本
        elif not v1.pre_l and v2.pre_l:
            return 1
        elif v1.pre_l and v2.pre_l:
            pre_order = {
                "a": 0,
                "b": 1,
                "c": 2,
                "rc": 3,
                "alpha": 0,
                "beta": 1,
                "pre": 0,
                "preview": 0,
            }
            if pre_order[v1.pre_l] != pre_order[v2.pre_l]:
                return pre_order[v1.pre_l] - pre_order[v2.pre_l]
            elif v1.pre_n is not None and v2.pre_n is not None:
                return v1.pre_n - v2.pre_n
            elif v1.pre_n is None and v2.pre_n is not None:
                return -1
            elif v1.pre_n is not None and v2.pre_n is None:
                return 1

        # 比较 post-release
        if v1.post_n1 is not None:
            post_n1 = v1.post_n1
        elif v1.post_l:
            post_n1 = int(v1.post_n2) if v1.post_n2 else 0
        else:
            post_n1 = 0

        if v2.post_n1 is not None:
            post_n2 = v2.post_n1
        elif v2.post_l:
            post_n2 = int(v2.post_n2) if v2.post_n2 else 0
        else:
            post_n2 = 0

        if post_n1 != post_n2:
            return post_n1 - post_n2

        # 比较 dev-release
        if v1.dev_l and not v2.dev_l:
            return -1  # dev-release 小于 post-release 或正常版本
        elif not v1.dev_l and v2.dev_l:
            return 1
        elif v1.dev_l and v2.dev_l:
            if v1.dev_n is not None and v2.dev_n is not None:
                return v1.dev_n - v2.dev_n
            elif v1.dev_n is None and v2.dev_n is not None:
                return -1
            elif v1.dev_n is not None and v2.dev_n is None:
                return 1

        # 比较 local version
        if v1.local and not v2.local:
            return -1  # local version 小于 dev-release 或正常版本
        elif not v1.local and v2.local:
            return 1
        elif v1.local and v2.local:
            local1 = v1.local.split(".")
            local2 = v2.local.split(".")
            # 和 release 的处理方式一致, 对其 local version 长度, 缺失部分补 0
            if len(local1) != len(local2):
                for _ in range(abs(len(local1) - len(local2))):
                    if len(local1) < len(local2):
                        local1.append(0)
                    else:
                        local2.append(0)
            for l1, l2 in zip(local1, local2):
                if l1.isdigit() and l2.isdigit():
                    l1, l2 = int(l1), int(l2)
                if l1 != l2:
                    return (l1 > l2) - (l1 < l2)
            return len(local1) - len(local2)

        return 0  # 版本相同

    def compare_versions(self, version1: str, version2: str) -> int:
        """比较两个版本字符串 Python 软件包版本号

        Args:
            version1 (str): 版本号 1
            version2 (str): 版本号 2

        Returns:
            int: 如果版本号 1 大于 版本号 2, 则返回`1`, 小于则返回`-1`, 如果相等则返回`0`
        """
        v1 = self.parse_version(version1)
        v2 = self.parse_version(version2)
        return self.compare_version_objects(v1, v2)

    def compatible_version_matcher(self, spec_version: str) -> Callable[[str], bool]:
        """PEP 440 兼容性版本匹配 (~= 操作符)

        Returns:
            (Callable[[str], bool]): 一个接受 version_str (`str`) 参数的判断函数
        """
        # 解析规范版本
        spec = self.parse_version(spec_version)

        # 获取有效 release 段 (去除末尾的零)
        clean_release = []
        for num in spec.release:
            if num != 0 or (clean_release and clean_release[-1] != 0):
                clean_release.append(num)

        # 确定最低版本和前缀匹配规则
        if len(clean_release) == 0:
            logger.debug("解析到错误的兼容性发行版本号")
            raise ValueError("解析到错误的兼容性发行版本号")

        # 生成前缀匹配模板 (忽略后缀)
        prefix_length = len(clean_release) - 1
        if prefix_length == 0:
            # 处理类似 ~= 2 的情况 (实际 PEP 禁止, 但这里做容错)
            prefix_pattern = [spec.release[0]]
            min_version = self.parse_version(f"{spec.release[0]}")
        else:
            prefix_pattern = list(spec.release[:prefix_length])
            min_version = spec

        def _is_compatible(version_str: str) -> bool:
            target = self.parse_version(version_str)

            # 主版本前缀检查
            target_prefix = target.release[: len(prefix_pattern)]
            if target_prefix != prefix_pattern:
                return False

            # 最低版本检查 (自动忽略 pre/post/dev 后缀)
            return self.compare_version_objects(target, min_version) >= 0

        return _is_compatible

    def version_match(self, spec: str, version: str) -> bool:
        """PEP 440 版本前缀匹配

        Args:
            spec (str): 版本匹配表达式 (e.g. '1.1.*')
            version (str): 需要检测的实际版本号 (e.g. '1.1a1')

        Returns:
            bool: 是否匹配
        """
        # 分离通配符和本地版本
        spec_parts = spec.split("+", 1)
        spec_main = spec_parts[0].rstrip(".*")  # 移除通配符
        has_wildcard = spec.endswith(".*") and "+" not in spec

        # 解析规范版本 (不带通配符)
        try:
            spec_ver = self.parse_version(spec_main)
        except ValueError:
            return False

        # 解析目标版本 (忽略本地版本)
        target_ver = self.parse_version(version.split("+", 1)[0])

        # 前缀匹配规则
        if has_wildcard:
            # 生成补零后的 release 段
            spec_release = spec_ver.release.copy()
            while len(spec_release) < len(target_ver.release):
                spec_release.append(0)

            # 比较前 N 个 release 段 (N 为规范版本长度)
            return target_ver.release[: len(spec_ver.release)] == spec_ver.release and target_ver.epoch == spec_ver.epoch
        else:
            # 严格匹配时使用原比较函数
            return self.compare_versions(spec_main, version) == 0

    def is_v1_ge_v2(self, v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否大于或等于 v2

        例如:
        ```
        1.1, 1.0 -> True
        1.0, 1.0 -> True
        0.9, 1.0 -> False
        ```

        Args:
            v1 (str): 第 1 个 Python 软件包版本号

            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号大于或等于 v2 版本号则返回`True`
        """
        return self.compare_versions(v1, v2) >= 0

    def is_v1_gt_v2(self, v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否大于 v2

        例如:
        ```
        1.1, 1.0 -> True
        1.0, 1.0 -> False
        ```

        Args:
            v1 (str): 第 1 个 Python 软件包版本号
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号大于 v2 版本号则返回`True`
        """
        return self.compare_versions(v1, v2) > 0

    def is_v1_eq_v2(self, v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否等于 v2

        例如:
        ```
        1.0, 1.0 -> True
        0.9, 1.0 -> False
        1.1, 1.0 -> False
        ```

        Args:
            v1 (str): 第 1 个 Python 软件包版本号
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            `bool`: 如果 v1 版本号等于 v2 版本号则返回`True`
        """
        return self.compare_versions(v1, v2) == 0

    def is_v1_lt_v2(self, v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否小于 v2

        例如:
        ```
        0.9, 1.0 -> True
        1.0, 1.0 -> False
        ```

        Args:
            v1 (str): 第 1 个 Python 软件包版本号
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号小于 v2 版本号则返回`True`
        """
        return self.compare_versions(v1, v2) < 0

    def is_v1_le_v2(self, v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否小于或等于 v2

        例如:
        ```
        0.9, 1.0 -> True
        1.0, 1.0 -> True
        1.1, 1.0 -> False
        ```

        Args:
            v1 (str): 第 1 个 Python 软件包版本号
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号小于或等于 v2 版本号则返回`True`
        """
        return self.compare_versions(v1, v2) <= 0

    def is_v1_c_eq_v2(self, v1: str, v2: str) -> bool:
        """查看 Python 版本号 v1 是否大于等于 v2, (兼容性版本匹配)

        例如:
        ```
        1.0*, 1.0a1 -> True
        0.9*, 1.0 -> False
        ```

        Args:
            v1 (str): 第 1 个 Python 软件包版本号, 该版本由 ~= 符号指定
            v2 (str): 第 2 个 Python 软件包版本号

        Returns:
            bool: 如果 v1 版本号等于 v2 版本号则返回`True`
        """
        func = self.compatible_version_matcher(v1)
        return func(v2)


class PyWhlVersionMatcher:
    """Python 兼容性版本匹配器, 用于实现 ~= 操作符的语义

    Attributes:
        spec_version (str): 版本号
        comparison (PyWhlVersionComparison): Python 版本号比较工具
        _matcher_func (Callable[[str], bool]): 兼容性版本匹配函数
    """

    def __init__(self, spec_version: str) -> None:
        """初始化 Python 兼容性版本匹配器

        Args:
            spec_version (str): 版本号
        """
        self.spec_version = spec_version
        self.comparison = PyWhlVersionComparison(spec_version)
        self._matcher_func = self.comparison.compatible_version_matcher(spec_version)

    def __eq__(self, other: object) -> bool:
        """实现 ~version == other_version 的语义
        Args:
            other (object): 用于比较的对象
        Returns:
            bool: 如果此版本不等于另一个版本
        """
        if isinstance(other, str):
            return self._matcher_func(other)
        elif isinstance(other, PyWhlVersionComparison):
            return self._matcher_func(other.version)
        elif isinstance(other, PyWhlVersionMatcher):
            # 允许 ~v1 == ~v2 的比较 (比较规范版本)
            return self.spec_version == other.spec_version
        return NotImplemented

    def __repr__(self) -> str:
        return f"~{self.spec_version}"
