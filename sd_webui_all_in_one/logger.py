"""日志工具"""

import sys
import copy
import inspect
import logging


class LoggingColoredFormatter(logging.Formatter):
    """Logging 格式化类

    Attributes:
        color (bool): 是否启用日志颜色
        COLORS (dict[str, str]): 颜色类型字典
    """

    COLORS = {
        "DEBUG": "\033[0;36m",  # CYAN
        "INFO": "\033[0;32m",  # GREEN
        "WARNING": "\033[0;33m",  # YELLOW
        "ERROR": "\033[0;31m",  # RED
        "CRITICAL": "\033[0;37;41m",  # WHITE ON RED
        "RESET": "\033[0m",  # RESET COLOR
    }

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        color: bool | None = True,
    ) -> None:
        """Logging 初始化

        Args:
            fmt (str | None): 日志消息的格式字符串
            datefmt (str | None): 日期 / 时间的显示格式
            color (bool | None): 是否启用彩色日志输出. 默认为 True
        """
        super().__init__(fmt, datefmt)
        self.color = color

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        colored_record = copy.copy(record)
        levelname = colored_record.levelname

        if self.color:
            seq = self.COLORS.get(levelname, self.COLORS["RESET"])
            colored_record.levelname = f"{seq}{levelname}{self.COLORS['RESET']}"

        return super().format(colored_record)


def get_logger(
    name: str | None = None,
    level: int | None = logging.INFO,
    color: bool | None = True,
) -> logging.Logger:
    """获取 Loging 对象

    Args:
        name (str | None): Logging 名称
        level (int | None): 日志级别
        color (bool | None): 是否启用彩色日志
    Returns:
        logging.Logger: Logging 对象
    """
    if name is not None:
        log_format = "[%(name)s]-|%(asctime)s|-%(levelname)s: %(message)s"
        logger_name = name
    else:
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)
        logger_name = module.__name__ if module else "root"
        log_format = "[%(name)s:%(funcName)s:%(lineno)d]-|%(asctime)s|-%(levelname)s: %(message)s"

    logger = logging.getLogger(logger_name)
    logger.propagate = False

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            LoggingColoredFormatter(
                fmt=log_format,
                datefmt=r"%H:%M:%S",
                color=color,
            )
        )
        logger.addHandler(handler)

    logger.setLevel(level)
    fn, lno, func, _ = logger.findCaller(stack_info=False, stacklevel=2)
    logger.debug("Logger 初始化完成, 位置: %s:%s in %s", fn, lno, func)
    return logger
