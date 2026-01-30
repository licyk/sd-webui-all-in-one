import traceback


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
        base_message: str = super().__str__()
        output: list[str] = [base_message]

        for i, exc in enumerate(self.exceptions, start=1):
            stack_trace: str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            output.append(f"\n[错误 #{i}]\n{stack_trace}")

        return "".join(output)
