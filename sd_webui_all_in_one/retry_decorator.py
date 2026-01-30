import time
from functools import wraps
from typing import Any, Callable, TypeVar, cast

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR

logger = get_logger(
    name="Retry Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

T = TypeVar("T")


def retry(
    times: int = 3,
    delay: float = 1.0,
    describe: str | None = None,
    catch_exceptions: type[Exception] | tuple[type[Exception], ...] | None = Exception,
    raise_exception: type[Exception] | None = RuntimeError,
) -> Callable[[Callable[..., T | None]], Callable[..., T]]:
    """通用的重试装饰器

    Args:
        times (int):
            最大重试次数
        delay (float):
            失败后的延迟时间 (秒)
        describe (str):
            日志中显示的描述文字
        catch_exceptions (type[Exception] | tuple[type[Exception], ...] | None):
            需要捕获并触发重试的异常类型
        raise_exception (type[Exception] | None):
            超过重试次数后抛出的异常类型

    Returns:
        Callable: 装饰器函数
    """

    def decorator(func: Callable[..., T | None]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            count = 0
            err = None
            target_info = describe if describe is not None else func.__name__

            while count < times:
                count += 1
                try:
                    return func(*args, **kwargs)
                except catch_exceptions as e:
                    # 仅捕获指定的异常进行重试
                    err = e
                    logger.error("[%s/%s] %s 出现错误: %s", count, times, target_info, e)

                    if count < times:
                        logger.warning("[%s/%s] 重试 %s 中", count, times, target_info)
                        if delay > 0:
                            time.sleep(delay)
                    else:
                        # 达到重试上限, 抛出指定的异常
                        raise raise_exception(f"执行 '{target_info}' 时发生错误: {err}") from err

                except Exception as e:  # pylint: disable=duplicate-except
                    # 如果出现了不在 catch_exceptions 列表中的异常, 立即抛出, 不重试
                    logger.critical("[%s/%s] 遇到不可重试的致命错误: %s", count, times, e)
                    raise

            # 正常情况下逻辑在循环内结束, 这里作为兜底抛出
            raise raise_exception(f"执行 '{target_info}' 最终失败")

        return cast(Callable[..., T], wrapper)

    return decorator
