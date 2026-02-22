import shutil
import sys
import time
from typing import (
    Any,
    Iterable,
    TypeVar,
    Generic,
    Iterator,
)


T = TypeVar("T")


class SimpleTqdm(Generic[T]):
    """一个简单的终端进度条工具, 支持多行显示

    Attributes:
        _active_instances (int):
            当前活跃的 SimpleTqdm 实例数量
        _max_pos (int):
            所有实例中占据的最大终端行位置
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
        n (int):
            当前完成的进度
        start_time (float):
            进度条开始时间
    """

    _active_instances: int = 0
    _max_pos: int = -1

    def __init__(
        self,
        iterable: Iterable[T] | None = None,
        desc: str = "",
        total: int | None = None,
        leave: bool = True,
        position: int = 0,
        disable: bool = False,
        bar_length: int | None = None,
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
        """
        self.iterable = iterable
        self.desc = desc
        self.total = total if total is not None else (len(iterable) if iterable and hasattr(iterable, "__len__") else None)
        self.leave = leave
        self.position = position
        self.disable = disable
        self.fixed_bar_length = bar_length
        self.n = 0
        self.start_time = time.time()
        self._last_refresh_t: float = 0

        if not self.disable:
            SimpleTqdm._active_instances += 1
            SimpleTqdm._max_pos = max(SimpleTqdm._max_pos, self.position)

            if self.position > 0:
                # 在指定位置预留空行
                sys.stdout.write("\n" * self.position + f"\033[{self.position}A")

            sys.stdout.flush()
            self._render()

    def __iter__(
        self,
    ) -> Iterator[T]:
        """迭代进度条封装的对象

        Yields:
            T: 迭代对象的元素
        """
        if self.disable:
            if self.iterable:
                for item in self.iterable:
                    yield item
            return

        if self.iterable:
            for item in self.iterable:
                yield item
                self.update(1)
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
        if n == 0:
            return
        self.n += n
        if not self.disable:
            curr_t = time.time()
            # 限制刷新率, 避免频繁 I/O (约 30 FPS)
            if curr_t - self._last_refresh_t > 0.033 or (self.total and self.n >= self.total):
                self._render()
                self._last_refresh_t = curr_t

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
        return f"{m:02d}:{s:02d}"

    def _render(
        self,
    ) -> None:
        """渲染进度条并输出到终端"""
        elapsed = time.time() - self.start_time
        speed = self.n / elapsed if elapsed > 0 else 0
        time_str = self._format_time(elapsed)
        term_width, _ = shutil.get_terminal_size(fallback=(80, 20))

        if self.total and self.total > 0:
            percent_str = f"{int(min(self.n / self.total, 1.0) * 100)}%"
            counts_str = f"{self.n}/{self.total}"
            stats_str = f"[{time_str}, {speed:.2f}it/s]"

            # 基础文本用于计算剩余可用空间
            base_text = f"{self.desc}: {percent_str}|" + "|" + f" {counts_str} {stats_str}"

            # 计算进度条长度
            bar_len = self.fixed_bar_length if self.fixed_bar_length else max(2, term_width - len(base_text) - 2)
            progress = min(self.n / self.total, 1.0)
            filled_len = int(bar_len * progress)
            bar_str = "█" * filled_len + "-" * (bar_len - filled_len)

            msg = f"{self.desc}: {percent_str}|{bar_str}| {counts_str} {stats_str}"
        else:
            msg = f"{self.desc}: {self.n}it [{time_str}, {speed:.2f}it/s]"

        # 截断过长的消息
        if len(msg) > term_width:
            msg = msg[: term_width - 3] + "..."

        # ANSI 转义序列：移动光标并清除行
        move_down = f"\033[{self.position}B" if self.position > 0 else ""
        move_up = f"\033[{self.position}A" if self.position > 0 else ""
        sys.stdout.write(f"\r{move_down}\r\033[K{msg}{move_up}\r")
        sys.stdout.flush()

    def close(
        self,
    ) -> None:
        """关闭进度条并清理终端输出"""
        if self.disable:
            return

        self._render()
        SimpleTqdm._active_instances -= 1

        # 如果不保留, 则清除当前行
        if not self.leave:
            move_down = f"\033[{self.position}B" if self.position > 0 else ""
            move_up = f"\033[{self.position}A" if self.position > 0 else ""
            sys.stdout.write(f"\r{move_down}\r\033[K{move_up}\r")

        # 最后一个进度条关闭时, 光标跳至最下方
        if SimpleTqdm._active_instances == 0:
            jump_down = SimpleTqdm._max_pos + 1
            sys.stdout.write(f"\033[{jump_down}B\r")
            sys.stdout.flush()
            SimpleTqdm._max_pos = -1
        else:
            sys.stdout.write("\r")
            sys.stdout.flush()
