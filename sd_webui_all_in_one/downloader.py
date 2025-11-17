"""文件下载工具"""
import os
import time
import queue
import shutil
import hashlib
import datetime
import threading
import traceback
from pathlib import Path
from urllib.parse import urlparse
from tempfile import TemporaryDirectory
from typing import Any, Callable, Literal

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR


logger = get_logger(
    name="Downloader",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def aria2(
    url: str,
    path: Path | str | None = None,
    save_name: str | None = None,
) -> Path:
    """Aria2 下载工具

    Args:
        url (str): 文件下载链接
        path (Path | str | None): 下载文件的路径, 为`None`时使用当前路径
        save_name (str | None): 保存的文件名, 为`None`时使用`url`提取保存的文件名
    Returns:
        Path: 下载成功时返回文件路径, 否则返回`None`
    Raises:
        RuntimeError: 下载出现错误
    """
    if path is None:
        path = os.getcwd()

    path = Path(path) if not isinstance(path, Path) and path is not None else path
    if save_name is None:
        parts = urlparse(url)
        save_name = os.path.basename(parts.path)

    save_path = path / save_name
    try:
        logger.info("下载 %s 到 %s 中", os.path.basename(url), save_path)
        run_cmd(
            [
                "aria2c",
                "--console-log-level=error",
                "-c",
                "-x",
                "16",
                "-s",
                "16",
                "-k",
                "1M",
                url,
                "-d",
                path.as_posix(),
                "-o",
                save_name,
            ]
        )
        return save_path
    except Exception as e:
        logger.error("下载 %s 时发生错误: %s", url, e)
        raise RuntimeError(e) from e


def load_file_from_url(
    url: str,
    *,
    model_dir: Path | str | None = None,
    progress: bool | None = False,
    file_name: str | None = None,
    hash_prefix: str | None = None,
    re_download: bool | None = False,
):
    """使用 requrests 库下载文件

    Args:
        url (str): 下载链接
        model_dir (Path | str | None): 下载路径
        progress (bool | None): 是否启用下载进度条
        file_name (str | None): 保存的文件名, 如果为`None`则从`url`中提取文件
        hash_prefix (str | None): sha256 十六进制字符串, 如果提供, 将检查下载文件的哈希值是否与此前缀匹配, 当不匹配时引发`ValueError`
        re_download (bool): 强制重新下载文件
    Returns:
        Path: 下载的文件路径
    Raises:
        ValueError: 当提供了 hash_prefix 但文件哈希值不匹配时
    """
    import requests
    from tqdm import tqdm

    if model_dir is None:
        model_dir = os.getcwd()

    model_dir = Path(model_dir) if not isinstance(model_dir, Path) and model_dir is not None else model_dir

    if not file_name:
        parts = urlparse(url)
        file_name = os.path.basename(parts.path)

    cached_file = model_dir.resolve() / file_name

    if re_download or not cached_file.exists():
        model_dir.mkdir(parents=True, exist_ok=True)
        temp_file = model_dir / f"{file_name}.tmp"
        logger.info("下载 %s 到 %s 中", file_name, cached_file)
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        with tqdm(
            total=total_size,
            unit="B",
            unit_scale=True,
            desc=file_name,
            disable=not progress,
        ) as progress_bar:
            with open(temp_file, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        progress_bar.update(len(chunk))

        if hash_prefix and not compare_sha256(temp_file, hash_prefix):
            logger.error("%s 的哈希值不匹配, 正在删除临时文件", temp_file)
            temp_file.unlink()
            raise ValueError(f"文件哈希值与预期的哈希前缀不匹配: {hash_prefix}")

        temp_file.rename(cached_file)
        logger.info("%s 下载完成", file_name)
    else:
        logger.info("%s 已存在于 %s 中", file_name, cached_file)
    return cached_file


def compare_sha256(file_path: str | Path, hash_prefix: str) -> bool:
    """检查文件的 sha256 哈希值是否与给定的前缀匹配

    Args:
        file_path (str | Path): 文件路径
        hash_prefix (str): 哈希前缀
    Returns:
        bool: 匹配结果
    """
    hash_sha256 = hashlib.sha256()
    blksize = 1024 * 1024

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(blksize), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest().startswith(hash_prefix.strip().lower())


def download_file(
    url: str,
    path: str | Path = None,
    save_name: str | None = None,
    tool: Literal["aria2", "requests"] = "aria2",
    retry: int | None = 3,
) -> Path | None:
    """下载文件工具

    Args:
        url (str): 文件下载链接
        path (Path | str): 文件下载路径
        save_name (str | None): 文件保存名称, 当为`None`时从`url`中解析文件名
        tool (Literal["aria2", "requests"]): 下载工具
        retry (int | None): 重试下载的次数
    Returns:
        (Path | None): 保存的文件路径
    """
    if tool == "aria2" and shutil.which("aria2c") is None:
        logger.warning("未安装 Aria2, 无法使用 Aria2 进行下载, 将切换到 requests 进行下载任务")
        tool = "requests"
    count = 0
    while count < retry:
        count += 1
        try:
            if tool == "aria2":
                output = aria2(
                    url=url,
                    path=path,
                    save_name=save_name,
                )
                if output is None:
                    continue
                return output
            elif tool == "requests":
                output = load_file_from_url(
                    url=url,
                    model_dir=path,
                    file_name=save_name,
                )
                if output is None:
                    continue
                return output
            else:
                logger.error("未知下载工具: %s", tool)
                return None
        except Exception as e:
            logger.error("[%s/%s] 下载 %s 出现错误: %s", count, retry, url, e)

        if count < retry:
            logger.warning("[%s/%s] 重试下载 %s 中", count, retry, url)
        else:
            return None


def download_archive_and_unpack(url: str, local_dir: Path | str, name: str | None = None, retry: int | None = 3) -> Path | None:
    """下载压缩包并解压到指定路径

    Args:
        url (str): 压缩包下载链接, 压缩包只支持`zip`,`7z`,`tar`格式
        local_dir (Path | str): 下载路径
        name (str | None): 下载文件保存的名称, 为`None`时从`url`解析文件名
        retry (int | None): 重试下载的次数
    Returns:
        (Path | None): 下载成功并解压成功时返回路径
    """
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        local_dir = Path(local_dir) if not isinstance(local_dir, Path) and local_dir is not None else local_dir
        if name is None:
            parts = urlparse(url)
            name = os.path.basename(parts.path)

        archive_format = Path(name).suffix  # 压缩包格式
        origin_file_path = download_file(  # 下载文件
            url=url, path=path, save_name=name, retry=retry
        )

        if origin_file_path is not None:
            # 解压文件
            logger.info("解压 %s 到 %s 中", name, local_dir)
            try:
                if archive_format == ".7z":
                    run_cmd(
                        [
                            "7z",
                            "x",
                            origin_file_path.as_posix(),
                            f"-o{local_dir.as_posix()}",
                        ]
                    )
                    logger.info("%s 解压完成, 路径: %s", name, local_dir)
                    return local_dir
                elif archive_format == ".zip":
                    run_cmd(
                        [
                            "unzip",
                            origin_file_path.as_posix(),
                            "-d",
                            local_dir.as_posix(),
                        ]
                    )
                    logger.info("%s 解压完成, 路径: %s", name, local_dir)
                    return local_dir
                elif archive_format == ".tar":
                    run_cmd(
                        [
                            "tar",
                            "-xvf",
                            origin_file_path.as_posix(),
                            "-C",
                            local_dir.as_posix(),
                        ]
                    )
                    logger.info("%s 解压完成, 路径: %s", name, local_dir)
                    return local_dir
                else:
                    logger.error("%s 的格式不支持解压", name)
                    return None
            except Exception as e:
                logger.error("解压 %s 时发生错误: %s", name, e)
                traceback.print_exc()
                return None
        else:
            logger.error("%s 下载失败", name)
            return None


class MultiThreadDownloader:
    """通用多线程下载器

    Attributes:
        download_func (Callable): 执行下载任务的函数
        download_args_list (list[Any]): 传入下载函数的位置参数列表
        download_kwargs_list (list[dict[str, Any]]): 传入下载函数的关键字参数列表
        queue (queue.Queue): 任务队列, 用于存储待执行的下载任务
        total_tasks (int): 总的下载任务数
        completed_count (int): 已完成的任务数
        lock (threading.Lock): 线程锁, 用于保护对计数器的访问
        retry (int | None): 重试次数
        start_time (datetime.datetime | None): 下载开始时间
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
        self.retry = None
        self.start_time = None

    def worker(self) -> None:
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
                    traceback.print_exc()
                    logger.error(
                        "[%s/%s] 执行 %s 时发生错误: %s",
                        count,
                        self.retry,
                        self.download_func,
                        e,
                    )
                    if count < self.retry:
                        logger.warning("[%s/%s] 重试执行中", count, self.retry)

            self.queue.task_done()
            with self.lock:  # 访问共享资源时加锁
                self.completed_count += 1
                self.print_progress()  # 打印进度

    def print_progress(self) -> None:
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

        logger.info(
            "下载进度: %.2f%% | %d/%d [%s<%s, %.2f it/s]",
            progress,
            self.completed_count,
            self.total_tasks,
            formatted_time,
            formatted_estimated_time,
            speed,
        )

    def start(
        self,
        num_threads: int | None = 16,
        retry: int | None = 3,
    ) -> None:
        """启动多线程下载器

        Args:
            num_threads (int): 下载线程数, 默认为 16
            retry (int): 重试次数, 默认为 3
        """

        # 将重试次数作为属性传递给下载函数
        self.retry = retry

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
