"""ANSI 转义码, 用于显示彩色文字"""

from dataclasses import dataclass


@dataclass
class ANSIColor:
    """ANSI 转义码, 用于在终端中显示彩色文本"""

    BLUE = "\033[94m"
    """蓝色"""

    GOLD = "\033[33m"
    """金色"""

    WHITE = "\033[97m"
    """白色"""

    GREEN = "\033[92m"
    """绿色"""

    RED = "\033[91m"
    """红色"""

    YELLOW = "\033[33m"
    """黄色"""

    CYAN = "\033[36m"
    """青色"""

    BOLD = "\033[1m"
    """字体加粗"""

    RESET = "\033[0m"
    """重置颜色"""
