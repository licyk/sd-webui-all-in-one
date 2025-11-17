"""版本大小比较器"""

import re


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
        version1 = str(version1)
        version2 = str(version2)

        # 移除构建元数据（+之后的部分）
        v1_main = version1.split("+", maxsplit=1)[0]
        v2_main = version2.split("+", maxsplit=1)[0]

        # 分离主版本号和预发布版本（支持多种分隔符）
        def _split_version(v):
            # 先尝试用 -, _, . 分割预发布版本
            # 匹配主版本号部分和预发布部分
            match = re.match(r"^([0-9]+(?:\.[0-9]+)*)([-_.].*)?$", v)
            if match:
                release = match.group(1)
                pre = match.group(2)[1:] if match.group(2) else ""  # 去掉分隔符
                return release, pre
            return v, ""

        v1_release, v1_pre = _split_version(v1_main)
        v2_release, v2_pre = _split_version(v2_main)

        # 将版本号拆分成数字列表
        try:
            nums1 = [int(x) for x in v1_release.split(".") if x]
            nums2 = [int(x) for x in v2_release.split(".") if x]
        except Exception as _:
            return 0

        # 补齐版本号长度
        max_len = max(len(nums1), len(nums2))
        nums1 += [0] * (max_len - len(nums1))
        nums2 += [0] * (max_len - len(nums2))

        # 比较版本号
        for i in range(max_len):
            if nums1[i] > nums2[i]:
                return 1
            elif nums1[i] < nums2[i]:
                return -1

        # 如果主版本号相同, 比较预发布版本
        if v1_pre and not v2_pre:
            return -1  # 预发布版本 < 正式版本
        elif not v1_pre and v2_pre:
            return 1  # 正式版本 > 预发布版本
        elif v1_pre and v2_pre:
            if v1_pre > v2_pre:
                return 1
            elif v1_pre < v2_pre:
                return -1
            else:
                return 0
        else:
            return 0  # 版本号相同


def version_increment(version: str) -> str:
    """增加版本号大小

    Args:
        version (str): 初始版本号
    Returns:
        str: 增加后的版本号
    """
    version = "".join(re.findall(r"\d|\.", version))
    ver_parts = list(map(int, version.split(".")))
    ver_parts[-1] += 1

    for i in range(len(ver_parts) - 1, 0, -1):
        if ver_parts[i] == 10:
            ver_parts[i] = 0
            ver_parts[i - 1] += 1

    return ".".join(map(str, ver_parts))


def version_decrement(version: str) -> str:
    """减小版本号大小

    Args:
        version (str): 初始版本号
    Returns:
        str: 减小后的版本号
    """
    version = "".join(re.findall(r"\d|\.", version))
    ver_parts = list(map(int, version.split(".")))
    ver_parts[-1] -= 1

    for i in range(len(ver_parts) - 1, 0, -1):
        if ver_parts[i] == -1:
            ver_parts[i] = 9
            ver_parts[i - 1] -= 1

    while len(ver_parts) > 1 and ver_parts[0] == 0:
        ver_parts.pop(0)

    return ".".join(map(str, ver_parts))
