"""进度条工具"""

import re
import shutil
import sys
import threading
import time
import unicodedata
from collections.abc import Mapping, Sized
from typing import (
    Any,
    ClassVar,
    Iterable,
    TypeVar,
    Generic,
    Iterator,
    TextIO,
)


T = TypeVar("T")
"""泛型类型变量"""


ANSI_RE = re.compile(r"\033\[[0-?]*[ -/]*[@-~]")
FORMAT_FIELD_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)(?::[^{}]*)?\}")
COLOUR_CODES = {
    "black": "30",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
    "bright_black": "90",
    "bright_red": "91",
    "bright_green": "92",
    "bright_yellow": "93",
    "bright_blue": "94",
    "bright_magenta": "95",
    "bright_cyan": "96",
    "bright_white": "97",
}


class SimpleTqdm(Generic[T]):
    """一个简单的终端进度条工具, 支持多行显示

    Attributes:
        _active_instances (ClassVar[int]):
            当前活跃的 SimpleTqdm 实例数量
        _max_pos (ClassVar[int]):
            所有实例中占据的最大终端行位置
        _instances (ClassVar[list[SimpleTqdm[Any]]]):
            当前活跃的 SimpleTqdm 实例集合
        _lock (ClassVar[Any]):
            保护多进度条输出的锁
        iterable (Iterable[Any] | None):
            可迭代对象
        desc (str):
            进度条前缀描述
        total (int | None):
            总迭代次数
        leave (bool):
            进度条完成后是否保留
        position (int):
            进度条在终端中的行偏移量
        disable (bool):
            是否禁用进度条
        fixed_bar_length (int | None):
            固定进度条长度, 若为 None 则自动填充
        unit (str):
            进度单位
        unit_scale (bool):
            是否缩放进度单位
        unit_divisor (int):
            缩放进度单位时使用的除数
        n (int):
            当前完成的进度
        start_time (float):
            进度条开始时间
    """

    _active_instances: ClassVar[int] = 0
    _max_pos: ClassVar[int] = -1
    _instances: ClassVar[list["SimpleTqdm[Any]"]] = []
    _lock: ClassVar[Any] = threading.RLock()

    def __init__(
        self,
        iterable: Iterable[T] | None = None,
        desc: str = "",
        total: int | None = None,
        leave: bool = True,
        position: int = 0,
        disable: bool = False,
        bar_length: int | None = None,
        unit: str = "it",
        unit_scale: bool = False,
        initial: int = 0,
        unit_divisor: int = 1000,
        file: TextIO | None = None,
        ncols: int | None = None,
        dynamic_ncols: bool = True,
        mininterval: float = 0.1,
        ascii: bool | str = False,
        colour: str | None = None,
        bar_format: str | None = None,
        smoothing: float = 0.3,
    ) -> None:
        """初始化 SimpleTqdm 进度条

        Args:
            iterable (Iterable[T] | None):
                要迭代的对象
            desc (str):
                显示在进度条左侧的描述文字
            total (int | None):
                总迭代次数如果为 None, 则尝试通过 len(iterable) 获取
            leave (bool):
                迭代结束后是否保留在终端显示
            position (int):
                进度条显示的行位置偏移（用于多进度条并行）
            disable (bool):
                是否禁用显示
            bar_length (int | None):
                进度条中“槽”的固定宽度
            unit (str):
                进度单位, 兼容 tqdm 的 unit 参数
            unit_scale (bool):
                是否缩放进度单位, 兼容 tqdm 的 unit_scale 参数
            initial (int):
                初始进度值, 兼容 tqdm 的 initial 参数
            unit_divisor (int):
                单位缩放除数, 下载字节时可使用 1024
            file (TextIO | None):
                输出流, 默认为 sys.stdout
            ncols (int | None):
                固定输出宽度
            dynamic_ncols (bool):
                是否动态读取终端宽度
            mininterval (float):
                最小刷新间隔
            ascii (bool | str):
                是否使用 ASCII 进度条字符
            colour (str | None):
                进度条颜色名
            bar_format (str | None):
                自定义显示格式
            smoothing (float):
                速度指数平滑系数
        """
        self.iterable = iterable
        self.desc = desc
        if total is not None:
            self.total = total
        elif isinstance(iterable, Sized):
            self.total = len(iterable)
        else:
            self.total = None
        self.leave = leave
        self.position = position
        self.disable = disable
        self.fixed_bar_length = bar_length
        self.unit = unit
        self.unit_scale = unit_scale
        self.unit_divisor = unit_divisor
        self.file = file if file is not None else sys.stdout
        self.ncols = ncols
        self.dynamic_ncols = dynamic_ncols
        self.mininterval = mininterval
        self.ascii = ascii
        self.colour = colour
        self.bar_format = bar_format
        self.smoothing = max(0.0, min(float(smoothing), 1.0))
        self.n = initial
        self.start_time = time.time()
        self._last_refresh_t: float = 0
        self._last_rate_t = self.start_time
        self._last_rate_n = self.n
        self._ema_rate: float | None = None
        self._closed = False
        self._postfix = ""

        if not self.disable:
            with SimpleTqdm._lock:
                SimpleTqdm._active_instances += 1
                SimpleTqdm._instances.append(self)
                SimpleTqdm._max_pos = max(SimpleTqdm._max_pos, self.position)

                if self.position > 0:
                    # 在指定位置预留空行
                    self.file.write("\n" * self.position + f"\033[{self.position}A")

                self.file.flush()
                self._render()

    def __iter__(
        self,
    ) -> Iterator[T]:
        """迭代进度条封装的对象

        Yields:
            T: 迭代对象的元素
        """
        try:
            if self.iterable is not None:
                for item in self.iterable:
                    yield item
                    self.update(1)
        finally:
            self.close()

    def __enter__(
        self,
    ) -> "SimpleTqdm[T]":
        """上下文管理器进入"""
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """上下文管理器退出"""
        self.close()

    def update(
        self,
        n: int = 1,
    ) -> None:
        """更新进度

        Args:
            n (int):
                增量进度值
        """
        self.n += n
        if not self.disable:
            curr_t = time.time()
            # 限制刷新率, 避免频繁 I/O (约 30 FPS)
            if n == 0 or curr_t - self._last_refresh_t >= self.mininterval or (self.total and self.n >= self.total):
                self.refresh()

    def refresh(
        self,
    ) -> None:
        """立即刷新进度条显示"""
        if self.disable or self._closed:
            return
        with SimpleTqdm._lock:
            self._render()
            self._last_refresh_t = time.time()

    def clear(
        self,
    ) -> None:
        """清除当前进度条行"""
        if self.disable:
            return
        with SimpleTqdm._lock:
            self._clear_line()

    def _clear_line(
        self,
    ) -> None:
        """清除当前进度条行, 调用方需负责同步"""
        move_down = f"\033[{self.position}B" if self.position > 0 else ""
        move_up = f"\033[{self.position}A" if self.position > 0 else ""
        self.file.write(f"\r{move_down}\r\033[K{move_up}\r")
        self.file.flush()

    def reset(
        self,
        total: int | None = None,
    ) -> None:
        """重置进度条状态

        Args:
            total (int | None):
                新的总进度, 为 None 时保留原 total
        """
        self.n = 0
        if total is not None:
            self.total = total
        self.start_time = time.time()
        self._last_refresh_t = 0
        self._last_rate_t = self.start_time
        self._last_rate_n = self.n
        self._ema_rate = None
        self.refresh()

    def set_description(
        self,
        desc: str | None = None,
        refresh: bool = True,
    ) -> None:
        """设置进度条描述

        Args:
            desc (str | None):
                新描述, 为 None 时使用空字符串
            refresh (bool):
                是否立即刷新
        """
        self.desc = desc or ""
        if refresh:
            self.refresh()

    def set_description_str(
        self,
        desc: str | None = None,
        refresh: bool = True,
    ) -> None:
        """设置进度条描述字符串

        Args:
            desc (str | None):
                新描述, 为 None 时使用空字符串
            refresh (bool):
                是否立即刷新
        """
        self.set_description(desc=desc, refresh=refresh)

    def set_postfix(
        self,
        ordered_dict: Mapping[str, Any] | Iterable[tuple[str, Any]] | None = None,
        refresh: bool = True,
        **kwargs: Any,
    ) -> None:
        """设置进度条后缀

        Args:
            ordered_dict (Mapping[str, Any] | Iterable[tuple[str, Any]] | None):
                后缀键值对
            refresh (bool):
                是否立即刷新
            **kwargs (Any):
                附加后缀键值对
        """
        items: list[tuple[str, Any]] = []
        if ordered_dict is not None:
            if isinstance(ordered_dict, Mapping):
                for key, value in ordered_dict.items():
                    items.append((str(key), value))
            else:
                items.extend(ordered_dict)
        for key, value in kwargs.items():
            items.append((key, value))
        self._postfix = ", ".join(f"{key}={value}" for key, value in items)
        if refresh:
            self.refresh()

    def set_postfix_str(
        self,
        s: str = "",
        refresh: bool = True,
    ) -> None:
        """设置进度条后缀字符串

        Args:
            s (str):
                后缀字符串
            refresh (bool):
                是否立即刷新
        """
        self._postfix = s
        if refresh:
            self.refresh()

    @classmethod
    def write(
        cls,
        msg: str,
        file: TextIO | None = None,
        end: str = "\n",
    ) -> None:
        """写入普通消息

        Args:
            msg (str):
                要写入的消息
            file (TextIO | None):
                输出流, 默认为 sys.stdout
            end (str):
                消息结束字符
        """
        stream = file or sys.stdout
        with cls._lock:
            active_bars = [bar for bar in cls._instances if not bar.disable and not bar._closed and bar.file is stream]
            for bar in sorted(active_bars, key=lambda item: item.position, reverse=True):
                bar._clear_line()

            stream.write(str(msg) + end)
            stream.flush()

            for bar in sorted(active_bars, key=lambda item: item.position):
                bar._render()

    def _format_time(
        self,
        seconds: float,
    ) -> str:
        """将秒数格式化为 MM:SS 格式

        Args:
            seconds (float): 秒数

        Returns:
            str: 格式化后的时间字符串
        """
        m, s = divmod(int(seconds), 60)
        if m >= 60:
            h, m = divmod(m, 60)
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _format_amount(
        self,
        value: int | float,
    ) -> str:
        """格式化进度数量"""
        amount = float(value)
        if not self.unit_scale:
            return f"{amount:g}{self.unit}"

        prefixes = ["", "K", "M", "G", "T", "P"]
        prefix_index = 0
        divisor = self.unit_divisor if self.unit_divisor > 0 else 1000
        while abs(amount) >= divisor and prefix_index < len(prefixes) - 1:
            amount /= divisor
            prefix_index += 1

        if prefix_index == 0:
            amount_text = f"{amount:g}"
        else:
            amount_text = f"{amount:.1f}".rstrip("0").rstrip(".")
        return f"{amount_text}{prefixes[prefix_index]}{self.unit}"

    def _format_rate(
        self,
        rate: float,
    ) -> str:
        """格式化速度"""
        return f"{self._format_amount(rate)}/s"

    def _format_remaining(
        self,
        rate: float,
    ) -> str:
        """格式化剩余时间"""
        if not self.total or rate <= 0:
            return "?"
        remaining = max(self.total - self.n, 0) / rate
        return self._format_time(remaining)

    def _render(
        self,
    ) -> None:
        """渲染进度条并输出到终端"""
        now = time.time()
        elapsed = now - self.start_time
        speed = self._get_display_rate(now, elapsed)
        time_str = self._format_time(elapsed)
        term_width = self._get_terminal_width()

        if self.bar_format is not None:
            msg = self._render_bar_format(elapsed, speed, term_width)
        elif self.total and self.total > 0:
            msg = self._render_known_total(elapsed, speed, term_width)
        else:
            postfix = f", {self._postfix}" if self._postfix else ""
            stats_str = f"[{time_str}, {self._format_rate(speed)}]{postfix}"
            msg = f"{self.desc}: {self._format_amount(self.n)} {stats_str}"

        msg = self._truncate_visible(msg, term_width)

        # ANSI 转义序列：移动光标并清除行
        move_down = f"\033[{self.position}B" if self.position > 0 else ""
        move_up = f"\033[{self.position}A" if self.position > 0 else ""
        self.file.write(f"\r{move_down}\r\033[K{msg}{move_up}\r")
        self.file.flush()

    def _get_display_rate(
        self,
        now: float,
        elapsed: float,
    ) -> float:
        """获取当前展示速度"""
        elapsed = max(elapsed, 0)
        average_rate = self.n / elapsed if elapsed > 0 else 0
        delta_n = self.n - self._last_rate_n
        delta_t = now - self._last_rate_t

        if delta_n > 0 and delta_t > 0:
            instant_rate = delta_n / delta_t
            if self.smoothing <= 0:
                self._ema_rate = average_rate
            elif self._ema_rate is None:
                self._ema_rate = instant_rate
            else:
                self._ema_rate = self.smoothing * instant_rate + (1 - self.smoothing) * self._ema_rate
            self._last_rate_n = self.n
            self._last_rate_t = now
        elif self.smoothing <= 0 and self._ema_rate is None:
            self._ema_rate = average_rate

        if self.smoothing <= 0:
            return average_rate
        return self._ema_rate if self._ema_rate is not None else average_rate

    def _render_known_total(
        self,
        elapsed: float,
        speed: float,
        term_width: int,
    ) -> str:
        """渲染已知总量的默认进度条"""
        percent_str = f"{int(self._progress_ratio() * 100)}%"
        counts_str = f"{self._format_amount(self.n)}/{self._format_amount(self.total or 0)}"
        postfix = f", {self._postfix}" if self._postfix else ""
        stats_str = f"[{self._format_time(elapsed)}, {self._format_rate(speed)}]{postfix}"

        base_text = f"{self.desc}: {percent_str}|| {counts_str} {stats_str}"
        bar_len = self._resolve_bar_length(term_width, base_text)
        bar_str = self._make_bar(bar_len)

        return f"{self.desc}: {percent_str}|{bar_str}| {counts_str} {stats_str}"

    def _render_bar_format(
        self,
        elapsed: float,
        speed: float,
        term_width: int,
    ) -> str:
        """渲染自定义格式进度条"""
        template = self.bar_format or ""
        values = self._format_values(elapsed, speed, "")
        if "{bar}" in template:
            preview = self._replace_format_fields(template, values)
            bar_len = self.fixed_bar_length if self.fixed_bar_length is not None else max(0, term_width - self._visible_len(preview))
            values["bar"] = self._make_bar(bar_len)
        return self._replace_format_fields(template, values)

    def _format_values(
        self,
        elapsed: float,
        speed: float,
        bar: str,
    ) -> dict[str, str]:
        """生成 bar_format 占位符值"""
        return {
            "bar": bar,
            "desc": self.desc,
            "elapsed": self._format_time(elapsed),
            "n_fmt": self._format_amount(self.n),
            "percentage": f"{int(self._progress_ratio() * 100)}%",
            "postfix": self._postfix,
            "rate_fmt": self._format_rate(speed),
            "remaining": self._format_remaining(speed),
            "total_fmt": self._format_amount(self.total or 0) if self.total is not None else "?",
            "unit": self.unit,
        }

    def _replace_format_fields(
        self,
        template: str,
        values: Mapping[str, str],
    ) -> str:
        """替换已支持的 bar_format 字段"""

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            return values.get(name, match.group(0))

        return FORMAT_FIELD_RE.sub(replace, template)

    def _resolve_bar_length(
        self,
        term_width: int,
        base_text: str,
    ) -> int:
        """计算进度条长度"""
        if self.fixed_bar_length is not None:
            return max(0, self.fixed_bar_length)
        return max(2, term_width - self._visible_len(base_text) - 2)

    def _make_bar(
        self,
        bar_len: int,
    ) -> str:
        """生成进度条主体"""
        bar_len = max(0, bar_len)
        if bar_len == 0:
            return ""
        filled_len = int(bar_len * self._progress_ratio())
        filled_char, empty_char = self._bar_chars()
        bar_str = filled_char * filled_len + empty_char * (bar_len - filled_len)
        return self._apply_colour(bar_str)

    def _progress_ratio(
        self,
    ) -> float:
        """获取进度比例"""
        if not self.total or self.total <= 0:
            return 0
        return max(0.0, min(self.n / self.total, 1.0))

    def _apply_colour(
        self,
        text: str,
    ) -> str:
        """给进度条主体添加 ANSI 颜色"""
        if not self.colour or not text:
            return text
        colour_name = str(self.colour).strip().lower().replace("-", "_").replace(" ", "_")
        colour_code = COLOUR_CODES.get(colour_name)
        if colour_code is None:
            return text
        return f"\033[{colour_code}m{text}\033[0m"

    def _get_terminal_width(
        self,
    ) -> int:
        """获取输出宽度"""
        if self.ncols is not None:
            return max(1, self.ncols)
        if self.dynamic_ncols:
            term_width, _ = shutil.get_terminal_size(fallback=(80, 20))
            return max(1, term_width)
        return 80

    def _bar_chars(
        self,
    ) -> tuple[str, str]:
        """获取进度条填充字符"""
        if isinstance(self.ascii, str) and len(self.ascii) >= 2:
            return self.ascii[-1], self.ascii[0]
        if self.ascii:
            return "#", "-"
        return "█", "-"

    @classmethod
    def _visible_len(
        cls,
        text: str,
    ) -> int:
        """计算忽略 ANSI 转义序列后的显示宽度"""
        return sum(cls._char_width(char) for char in ANSI_RE.sub("", text))

    @staticmethod
    def _char_width(
        char: str,
    ) -> int:
        """估算单个字符的终端显示宽度"""
        if unicodedata.combining(char):
            return 0
        if unicodedata.east_asian_width(char) in {"F", "W"}:
            return 2
        return 1

    @classmethod
    def _truncate_visible(
        cls,
        text: str,
        max_width: int,
    ) -> str:
        """按显示宽度截断文本并保留 ANSI 转义序列完整性"""
        if max_width <= 0:
            return ""
        if cls._visible_len(text) <= max_width:
            return text

        suffix = "..." if max_width > 3 else ""
        available_width = max_width - cls._visible_len(suffix)
        result: list[str] = []
        visible_width = 0
        index = 0
        had_ansi = False

        while index < len(text) and visible_width < available_width:
            ansi_match = ANSI_RE.match(text, index)
            if ansi_match is not None:
                result.append(ansi_match.group(0))
                index = ansi_match.end()
                had_ansi = True
                continue

            char = text[index]
            char_width = cls._char_width(char)
            if visible_width + char_width > available_width:
                break
            result.append(char)
            visible_width += char_width
            index += 1

        truncated = "".join(result) + suffix
        if had_ansi and "\033[0m" not in truncated:
            truncated += "\033[0m"
        return truncated

    def close(
        self,
    ) -> None:
        """关闭进度条并清理终端输出"""
        if self._closed:
            return
        self._closed = True

        if self.disable:
            return

        with SimpleTqdm._lock:
            self._render()
            if self in SimpleTqdm._instances:
                SimpleTqdm._instances.remove(self)
            SimpleTqdm._active_instances = max(0, SimpleTqdm._active_instances - 1)

            # 如果不保留, 则清除当前行
            if not self.leave:
                self._clear_line()

            # 最后一个进度条关闭时, 光标跳至最下方
            if SimpleTqdm._active_instances == 0:
                jump_down = SimpleTqdm._max_pos + 1
                self.file.write(f"\033[{jump_down}B\r")
                self.file.flush()
                SimpleTqdm._max_pos = -1
            else:
                if SimpleTqdm._instances:
                    SimpleTqdm._max_pos = max(bar.position for bar in SimpleTqdm._instances)
                self.file.write("\r")
                self.file.flush()
