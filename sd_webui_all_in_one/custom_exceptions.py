"""自定义异常类"""

import traceback
import os

from sd_webui_all_in_one.ansi_color import ANSIColor


class AggregateError(Exception):
    """
    聚合异常类：用于在多个任务执行完成后，统一抛出所有捕获到的异常。

    Attributes:
        exceptions (List[Exception]): 存储所有捕获到的原始异常对象。
    """

    def __init__(
        self,
        message: str,
        exceptions: list[Exception],
    ) -> None:
        """初始化聚合异常

        Args:
            message (str):
                异常的总体描述信息。
            exceptions(list[Exception]):
                捕获到的异常列表
        """
        super().__init__(message)
        self.exceptions = exceptions

    def __str__(self) -> str:
        """格式化所有子异常的完整堆栈轨迹

        Returns:
            str:
                堆栈日志字符串
        """
        base_message = f"{ANSIColor.BOLD}{ANSIColor.RED}{super().__str__()}{ANSIColor.RESET}"
        output = [base_message]

        for i, exc in enumerate(self.exceptions, start=1):
            location_info = "未知位置"
            tb = exc.__traceback__
            if tb:
                summary = traceback.extract_tb(tb)[-1]
                filename = os.path.basename(summary.filename)
                location_info = f"{ANSIColor.CYAN}文件 `{filename}`, 第 `{summary.lineno}` 行, 在 `{summary.name}` 中{ANSIColor.RESET}"

            exc_summary = f"{ANSIColor.BOLD}{ANSIColor.YELLOW}{type(exc).__name__}: {exc}{ANSIColor.RESET}"
            stack_trace: str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            header = f"{ANSIColor.BOLD}{ANSIColor.RED}[错误 #{i}]{ANSIColor.RESET}"
            output.append(f"\n{header} ({location_info}): {exc_summary}\n{stack_trace}")

        return "".join(output)


class WebUiRuntimeError(Exception):
    """运行 WebUI 进程异常类"""

    pass  # pylint: disable=unnecessary-pass


class RetrySignalError(Exception):
    """仅供装饰器内部使用的重试信号异常"""

    pass  # pylint: disable=unnecessary-pass


class ProcessTreeTerminated(SystemExit):
    """启动器收到终止信号 (例如 SIGTERM / SIGHUP) 时引发的异常

    继承自 SystemExit, 不会被 `except Exception` 捕获, 未被处理时会以 128 + 信号值作为退出代码静默退出。

    Attributes:
        signum (int): 收到的信号值
    """

    def __init__(self, signum: int) -> None:
        """初始化终止信号异常

        Args:
            signum (int):
                收到的信号值
        """
        super().__init__(128 + signum)
        self.signum = signum
