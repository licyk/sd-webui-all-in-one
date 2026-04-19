"""版本大小比较器"""

import re
from typing import Any


class CommonVersionComparison:
    """常规版本号比较工具

    使用:
    ```python
    CommonVersionComparison("1.0") != CommonVersionComparison("1.0") # False
    CommonVersionComparison("1.0.1") > CommonVersionComparison("1.0") # True
    CommonVersionComparison("1.0a") < CommonVersionComparison("1.0") # True
    ```

    Attributes:
        version (str | int | float): 版本号字符串
    """

    def __init__(self, version: str | int | float) -> None:
        """常规版本号比较工具初始化

        Args:
            version (str | int | float): 版本号字符串
        """
        self.version = version

    def __lt__(self, other: object) -> bool:
        """实现 < 符号的版本比较

        Returns:
            bool: 如果此版本小于另一个版本
        """
        if not isinstance(other, CommonVersionComparison):
            return NotImplemented
        return self.compare_versions(self.version, other.version) < 0

    def __gt__(self, other: object) -> bool:
        """实现 > 符号的版本比较

        Returns:
            bool: 如果此版本大于另一个版本
        """
        if not isinstance(other, CommonVersionComparison):
            return NotImplemented
        return self.compare_versions(self.version, other.version) > 0

    def __le__(self, other: object) -> bool:
        """实现 <= 符号的版本比较

        Returns:
            bool: 如果此版本小于等于另一个版本
        """
        if not isinstance(other, CommonVersionComparison):
            return NotImplemented
        return self.compare_versions(self.version, other.version) <= 0

    def __ge__(self, other: object) -> bool:
        """实现 >= 符号的版本比较

        Returns:
            bool: 如果此版本大于等于另一个版本
        """
        if not isinstance(other, CommonVersionComparison):
            return NotImplemented
        return self.compare_versions(self.version, other.version) >= 0

    def __eq__(self, other: object) -> bool:
        """实现 == 符号的版本比较

        Returns:
            bool: 如果此版本等于另一个版本
        """
        if not isinstance(other, CommonVersionComparison):
            return NotImplemented
        return self.compare_versions(self.version, other.version) == 0

    def __ne__(self, other: object) -> bool:
        """实现 != 符号的版本比较

        Returns:
            bool: 如果此版本不等于另一个版本
        """
        if not isinstance(other, CommonVersionComparison):
            return NotImplemented
        return self.compare_versions(self.version, other.version) != 0

    def compare_versions(self, version1: str | int | float, version2: str | int | float) -> int:
        """对比两个版本号大小

        Args:
            version1 (str | int | float): 第一个版本号
            version2 (str | int | float): 第二个版本号
        Returns:
            int: 版本对比结果, 1 为第一个版本号大, -1 为第二个版本号大, 0 为两个版本号一样
        """

        def _parse_chunks(v_str: Any) -> list[int | str | Any]:
            # 将字符串拆分为数字和非数字的块
            # 例如 "beta10.v2" -> [10, "beta", 10, "v", 2] 这种逻辑太复杂
            # 简单做法：按 '.' 或 '-' 拆分，然后处理每一段
            return [int(c) if c.isdigit() else c for c in re.split(r"[._-]", v_str) if c]

        def _compare_pre_release(pre1: Any, pre2: Any) -> int:
            # 如果一方没有预发布号，正式版更大
            if not pre1 and pre2:
                return 1
            if pre1 and not pre2:
                return -1
            if not pre1 and not pre2:
                return 0

            # 拆分预发布号段，例如 "beta.1" -> ["beta", 1]
            parts1 = _parse_chunks(pre1)
            parts2 = _parse_chunks(pre2)

            for p1, p2 in zip(parts1, parts2):
                if p1 == p2:
                    continue
                # 类型不同时（一数字一字母）：数字优先级低 (根据 SemVer 规范)
                if isinstance(p1, int) and isinstance(p2, str):
                    return -1
                if isinstance(p1, str) and isinstance(p2, int):
                    return 1
                # 类型相同时：直接比大小
                return 1 if p1 > p2 else -1

            # 长度不一致处理
            if len(parts1) > len(parts2):
                return 1
            if len(parts1) < len(parts2):
                return -1
            return 0

        def _extract_digits(v_str: str) -> list[int]:
            # 使用正则找出所有的数字序列
            # \d+ 匹配一个或多个连续数字
            digits = re.findall(r'\d+', str(v_str))
            return [int(d) for d in digits]

        v1_str, v2_str = str(version1), str(version2)

        # 1. 移除元数据
        v1_main = v1_str.split("+", maxsplit=1)[0]
        v2_main = v2_str.split("+", maxsplit=1)[0]

        # 2. 提取主版本和预发布版本
        # 匹配规则: 第一个字母或连字符出现之前为 release
        match1 = re.match(r"^([0-9.]+)(.*)$", v1_main)
        match2 = re.match(r"^([0-9.]+)(.*)$", v2_main)

        v1_release, v1_pre = match1.groups() if match1 else (v1_main, "")
        v2_release, v2_pre = match2.groups() if match2 else (v2_main, "")

        # 3. 比较主版本数字 (1.2.3)
        nums1 = _extract_digits(v1_release)
        nums2 = _extract_digits(v2_release)

        max_len = max(len(nums1), len(nums2))
        for i in range(max_len):
            n1 = nums1[i] if i < len(nums1) else 0
            n2 = nums2[i] if i < len(nums2) else 0
            if n1 > n2:
                return 1
            if n1 < n2:
                return -1

        # 4. 主版本相同时，比较预发布版本 (alpha, beta, rc)
        # 注意: 预发布版本通常带有前导符号，先去掉
        v1_pre = re.sub(r"^[-._]", "", v1_pre)
        v2_pre = re.sub(r"^[-._]", "", v2_pre)

        return _compare_pre_release(v1_pre, v2_pre)


def version_increment(
    version: str,
) -> str:
    """增加版本号最后一段的数值

    仅对最后一段 +1, 不进行跨段进位 (版本号段没有固定上限).

    Args:
        version (str): 初始版本号
    Returns:
        str: 增加后的版本号
    """
    version = "".join(re.findall(r"\d|\.", version))
    ver_parts = list(map(int, version.split(".")))
    ver_parts[-1] += 1
    return ".".join(map(str, ver_parts))


def version_decrement(
    version: str,
) -> str:
    """减小版本号最后一段的数值

    仅对最后一段 -1, 不进行跨段借位 (版本号段没有固定上限).
    如果最后一段已经是 0, 则结果为负数 (调用者应自行处理边界情况).

    Args:
        version (str): 初始版本号
    Returns:
        str: 减小后的版本号
    """
    version = "".join(re.findall(r"\d|\.", version))
    ver_parts = list(map(int, version.split(".")))
    ver_parts[-1] -= 1
    return ".".join(map(str, ver_parts))
