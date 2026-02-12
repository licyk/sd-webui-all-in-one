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
from typing import Any, Callable, Literal, TypeAlias, get_args

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, RETRY_TIMES, LOGGER_NAME
from sd_webui_all_in_one.retry_decorator import retryable
from sd_webui_all_in_one.file_operations.archive_manager import extract_archive
from sd_webui_all_in_one.custom_exceptions import AggregateError


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

DownloadToolType: TypeAlias = Literal["aria2", "requests", "urllib"]
"""可用的下载器类型"""

DOWNLOAD_TOOL_TYPE_LIST: list[str] = list(get_args(DownloadToolType))
"""可用的下载器类型列表"""


def aria2(
    url: str,
    path: Path | None = None,
    save_name: str | None = None,
    progress: bool | None = True,
) -> Path:
    """Aria2 下载工具

    Args:
        url (str):
            文件下载链接
        path (Path | None):
            下载文件的路径, 为`None`时使用当前路径
        save_name (str | None):
            保存的文件名, 为`None`时使用`url`提取保存的文件名
        progress (bool | None):
            是否启用下载进度条

    Returns:
        Path: 下载成功时返回文件路径

    Raises:
        RuntimeError: 下载出现错误
    """
    if path is None:
        path = Path().cwd()

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
                "--file-allocation=none",
                "--console-log-level=error",
                "--summary-interval=20",
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
            ],
            live=progress,
        )
        return save_path
    except RuntimeError as e:
        logger.error("下载 %s 时发生错误: %s", url, e)
        raise RuntimeError(e) from e


def download_file_from_url(
    url: str,
    save_path: Path | None = None,
    file_name: str | None = None,
    progress: bool | None = True,
    hash_prefix: str | None = None,
    re_download: bool | None = False,
) -> Path:
    """使用 requrests 库下载文件

    Args:
        url (str):
            下载链接
        save_path (Path | None):
            下载路径
        file_name (str | None):
            保存的文件名, 如果为`None`则从`url`中提取文件
        progress (bool | None):
            是否启用下载进度条
        hash_prefix (str | None):
            sha256 十六进制字符串, 如果提供, 将检查下载文件的哈希值是否与此前缀匹配, 当不匹配时引发`ValueError`
        re_download (bool):
            强制重新下载文件

    Returns:
        Path: 下载的文件路径

    Raises:
        ValueError: 当提供了 hash_prefix 但文件哈希值不匹配时
    """
    import requests

    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    if save_path is None:
        save_path = Path.cwd()

    if not file_name:
        parts = urlparse(url)
        file_name = Path(parts.path).name

    cached_file = save_path.resolve() / file_name

    if re_download or not cached_file.exists():
        save_path.mkdir(parents=True, exist_ok=True)
        temp_file = save_path / f"{file_name}.tmp"
        logger.info("下载 '%s' 到 '%s' 中", file_name, cached_file)
        response = requests.get(url, stream=True, timeout=60)
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
            logger.error("'%s' 的哈希值不匹配, 正在删除临时文件", temp_file)
            temp_file.unlink()
            raise ValueError(f"文件哈希值与预期的哈希前缀不匹配: {hash_prefix}")

        temp_file.rename(cached_file)
        logger.info("'%s' 下载完成", file_name)
    else:
        logger.info("'%s' 已存在于 '%s' 中", file_name, cached_file)
    return cached_file


def download_file_from_url_urllib(
    url: str,
    save_path: Path | None = None,
    file_name: str | None = None,
    progress: bool | None = True,
    hash_prefix: str | None = None,
    re_download: bool | None = False,
) -> Path:
    """使用 urllib 库下载文件

    Args:
        url (str):
            下载链接
        save_path (Path | None):
            下载路径
        file_name (str | None):
            保存的文件名, 如果为`None`则从`url`中提取文件
        progress (bool | None):
            是否启用下载进度条
        hash_prefix (str | None):
            sha256 十六进制字符串, 如果提供, 将检查下载文件的哈希值是否与此前缀匹配, 当不匹配时引发`ValueError`
        re_download (bool):
            强制重新下载文件

    Returns:
        Path: 下载的文件路径

    Raises:
        ValueError: 当提供了 hash_prefix 但文件哈希值不匹配时
    """
    import urllib.request

    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    if save_path is None:
        save_path = Path.cwd()

    if not file_name:
        parts = urlparse(url)
        file_name = Path(parts.path).name

    cached_file = save_path.resolve() / file_name

    if re_download or not cached_file.exists():
        save_path.mkdir(parents=True, exist_ok=True)
        temp_file = save_path / f"{file_name}.tmp"
        logger.info("下载 '%s' 到 '%s' 中", file_name, cached_file)

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as response:
            total_size = int(response.getheader("Content-Length", 0))
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                desc=file_name,
                disable=not progress,
            ) as progress_bar:
                with open(temp_file, "wb") as file:
                    while True:
                        chunk = response.read(1024)
                        if not chunk:
                            break
                        file.write(chunk)
                        progress_bar.update(len(chunk))

        if hash_prefix and not compare_sha256(temp_file, hash_prefix):
            logger.error("'%s' 的哈希值不匹配, 正在删除临时文件", temp_file)
            temp_file.unlink()
            raise ValueError(f"文件哈希值与预期的哈希前缀不匹配: {hash_prefix}")

        temp_file.rename(cached_file)
        logger.info("'%s' 下载完成", file_name)
    else:
        logger.info("'%s' 已存在于 '%s' 中", file_name, cached_file)
    return cached_file


def compare_sha256(
    file_path: str | Path,
    hash_prefix: str,
) -> bool:
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


@retryable(
    times=RETRY_TIMES,
    describe="执行下载器",
    catch_exceptions=(IOError, RuntimeError, ValueError),
    raise_exception=(RuntimeError),
    retry_on_none=False,
)
def download_executer(
    url: str,
    path: Path,
    save_name: str | None,
    tool: DownloadToolType,
    progress: bool,
) -> Path:
    """底层下载执行器

    Args:
        url (str):
            下载链接
        path (Path):
            保存路径
        save_name (str | None):
            保存名称
        tool (DownloadToolType):
            工具名称
        progress (bool):
            是否显示进度

    Returns:
        Path:
            成功返回路径
    """
    if tool == "aria2":
        return aria2(url=url, path=path, save_name=save_name, progress=progress)
    elif tool == "requests":
        return download_file_from_url(url=url, save_path=path, file_name=save_name, progress=progress)
    elif tool == "urllib":
        return download_file_from_url_urllib(url=url, save_path=path, file_name=save_name, progress=progress)
    return None


def download_file(
    url: str,
    path: Path | None = None,
    save_name: str | None = None,
    tool: DownloadToolType | None = "aria2",
    progress: bool = True,
) -> Path:
    """下载文件工具

    Args:
        url (str):
            文件下载链接
        path (Path | None):
            文件下载路径
        save_name (str | None):
            文件保存名称
        tool (DownloadToolType | None):
            下载工具
        progress (bool):
            是否启用下载进度条

    Returns:
        Path: 保存的文件路径
    """
    download_path = Path(path)
    download_path.mkdir(parents=True, exist_ok=True)

    selected_tool = str(tool)
    if selected_tool == "aria2" and shutil.which("aria2c") is None:
        logger.warning("未安装 Aria2, 将切换到 requests 进行下载")
        selected_tool = "requests"

    try:
        if selected_tool == "requests":
            import requests

            _ = requests
    except ImportError:
        logger.warning("未安装 requests, 将切换到 urllib 进行下载")
        selected_tool = "urllib"

    return download_executer(url=url, path=download_path, save_name=save_name, tool=selected_tool, progress=progress)


def download_archive_and_unpack(
    url: str,
    local_dir: Path,
    name: str | None = None,
) -> None:
    """下载压缩包并解压到指定路径

    Args:
        url (str):
            压缩包下载链接, 压缩包支持的格式: .zip, .7z, .rar, .tar, .tar.Z, .tar.lz, .tar.lzma, .tar.bz2, .tar.7z, .tar.gz, .tar.xz, .tar.zst
        local_dir (Path):
            下载路径
        name (str | None):
            下载文件保存的名称, 为`None`时从`url`解析文件名

    Raises:
        RuntimeError:
            下载并解压压缩包时发生错误时
    """
    with TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir)
        if name is None:
            parts = urlparse(url)
            name = os.path.basename(parts.path)

        try:
            origin_file_path = download_file(
                url=url,
                path=path,
                save_name=name,
            )
            logger.info("解压 %s 到 %s 中", name, local_dir)
            extract_archive(
                archive_path=origin_file_path,
                extract_to=local_dir,
            )
            logger.info("%s 解压完成, 路径: %s", name, local_dir)
        except Exception as e:
            logger.error("解压 %s 时发生错误: %s", name, e)
            raise RuntimeError(f"下载 {name} 并解压压缩包时发生错误: {e}") from e


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
