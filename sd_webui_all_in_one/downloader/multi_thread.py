"""多线程下载类"""

import datetime
import queue
import threading
import time
import traceback
from typing import (
    Any,
    Callable,
)

from sd_webui_all_in_one.custom_exceptions import AggregateError
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


class MultiThreadDownloader:
    """通用多线程下载器

    Attributes:
        download_func (Callable):
            执行下载任务的函数
        download_args_list (list[Any]):
            传入下载函数的位置参数列表
        download_kwargs_list (list[dict[str, Any]]):
            传入下载函数的关键字参数列表
        queue (queue.Queue):
            任务队列, 用于存储待执行的下载任务
        total_tasks (int):
            总的下载任务数
        completed_count (int):
            已完成的任务数
        lock (threading.Lock):
            线程锁, 用于保护对计数器的访问
        retry (int | None):
            重试次数
        start_time (datetime.datetime | None):
            下载开始时间
        error_list (list[Exception]):
            错误列表
    """

    def __init__(
        self,
        download_func: Callable,
        download_args_list: list[Any] | None = None,
        download_kwargs_list: list[dict[str, Any]] | None = None,
    ) -> None:
        """多线程下载器初始化

        下载参数列表, 每个元素是一个子列表或字典, 包含传递给下载函数的参数

        格式示例:
        ```python
        # 仅使用位置参数
        download_args_list = [
            [arg1, arg2, arg3, ...],  # 第一个下载任务的参数
            [arg1, arg2, arg3, ...],  # 第二个下载任务的参数
            [arg1, arg2, arg3, ...],  # 第三个下载任务的参数
        ]

        # 仅使用关键字参数
        download_kwargs_list = [
            {"param1": value1, "param2": value2},  # 第一个下载任务的参数
            {"param1": value3, "param2": value4},  # 第二个下载任务的参数
            {"param1": value5, "param2": value6},  # 第三个下载任务的参数
        ]

        # 混合使用位置参数和关键字参数
        download_args_list = [
            [arg1, arg2],
            [arg3, arg4],
            [arg5, arg6],
        ]
        download_kwargs_list = [
            {"param1": value1, "param2": value2},
            {"param1": value3, "param2": value4},
            {"param1": value5, "param2": value6},
        ]
        ```
        Args:
            download_func (Callable): 执行下载任务的函数
            download_args_list (list[Any]): 传入下载函数的参数列表
            download_kwargs_list (list[dict[str, Any]]): 传入下载函数的参数字典列表
        """
        self.download_func = download_func
        self.download_args_list = download_args_list or []
        self.download_kwargs_list = download_kwargs_list or []
        self.queue = queue.Queue()
        self.total_tasks = max(len(download_args_list or []), len(download_kwargs_list or []))  # 记录总的下载任务数 (以参数列表长度为准)
        self.completed_count = 0  # 记录已完成的任务数
        self.lock = threading.Lock()  # 创建锁以保护对计数器的访问
        self.retry: int | None = None
        self.start_time: datetime.datetime | None = None
        self.error_list: list[Exception] = []

    def worker(
        self,
    ) -> None:
        """工作线程函数, 执行下载任务"""
        while True:
            task = self.queue.get()
            if task is None:
                break

            args, kwargs = task
            count = 0
            while count < self.retry:
                count += 1
                try:
                    self.download_func(*args, **kwargs)
                    break
                except Exception as e:
                    self.error_list.append(e)
                    traceback.print_exc()
                    logger.error("[%s/%s] 执行 %s 时发生错误: %s", count, self.retry, self.download_func, e)
                    if count < self.retry:
                        logger.warning("[%s/%s] 重试执行中", count, self.retry)
                    else:
                        logger.error("[%s/%s] %s 已达到最大重试次数", count, self.retry, self.download_func)

            self.queue.task_done()
            with self.lock:  # 访问共享资源时加锁
                self.completed_count += 1
                self.print_progress()  # 打印进度

    def print_progress(
        self,
    ) -> None:
        """进度条显示"""
        progress = (self.completed_count / self.total_tasks) * 100
        current_time = datetime.datetime.now()
        time_interval = current_time - self.start_time
        hours = time_interval.seconds // 3600
        minutes = (time_interval.seconds // 60) % 60
        seconds = time_interval.seconds % 60
        formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"

        if self.completed_count > 0:
            speed = self.completed_count / time_interval.total_seconds()
        else:
            speed = 0

        remaining_tasks = self.total_tasks - self.completed_count

        if speed > 0:
            estimated_remaining_time_seconds = remaining_tasks / speed
            estimated_remaining_time = datetime.timedelta(seconds=estimated_remaining_time_seconds)
            estimated_hours = estimated_remaining_time.seconds // 3600
            estimated_minutes = (estimated_remaining_time.seconds // 60) % 60
            estimated_seconds = estimated_remaining_time.seconds % 60
            formatted_estimated_time = f"{estimated_hours:02}:{estimated_minutes:02}:{estimated_seconds:02}"
        else:
            formatted_estimated_time = "N/A"

        logger.info("下载进度: %.2f%% | %d/%d [%s<%s, %.2f it/s]", progress, self.completed_count, self.total_tasks, formatted_time, formatted_estimated_time, speed)

    def start(
        self,
        num_threads: int | None = 16,
        retry_count: int | None = 3,
    ) -> None:
        """启动多线程下载器

        Args:
            num_threads (int): 下载线程数, 默认为 16
            retry (int): 重试次数, 默认为 3

        Raises:
            AggregateError:
                下载任务出现错误时
        """

        # 将重试次数作为属性传递给下载函数
        self.retry = retry_count

        threads: list[threading.Thread] = []
        self.start_time = datetime.datetime.now()
        time.sleep(0.1)  # 避免 print_progress() 计算时间时出现 division by zero

        # 启动工作线程
        for _ in range(num_threads):
            thread = threading.Thread(target=self.worker)
            thread.start()
            threads.append(thread)

        # 准备下载任务参数
        max_tasks = max(len(self.download_args_list), len(self.download_kwargs_list))

        # 将下载任务添加到队列
        for i in range(max_tasks):
            # 获取位置参数
            args = self.download_args_list[i] if i < len(self.download_args_list) else []

            # 获取关键字参数
            kwargs = self.download_kwargs_list[i] if i < len(self.download_kwargs_list) else {}

            # 将任务参数打包
            self.queue.put((args, kwargs))

        # 等待所有任务完成
        self.queue.join()

        # 停止所有工作线程
        for _ in range(num_threads):
            self.queue.put(None)

        for thread in threads:
            thread.join()

        if self.error_list:
            raise AggregateError("执行多线程下载任务时发生了错误", self.error_list)
        else:
            logger.info("多线程下载任务运行结束")
