"""SSH 隧道基类"""

import queue
import re
import subprocess
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

from sd_webui_all_in_one.cmd import preprocess_command
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.tunnel.base import BaseTunnel
from sd_webui_all_in_one.tunnel.utils import gen_ssh_key


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class SSHTunnel(BaseTunnel):
    """SSH 隧道基类

    提供基于 SSH 的内网穿透通用实现. 子类需要提供具体的 SSH 参数和 URL 匹配模式.

    Attributes:
        ssh_args (list[str]):
            SSH 连接参数（不包括基础的 ssh 命令和密钥参数）
        url_pattern (re.Pattern[str]):
            用于匹配内网穿透地址的正则表达式
        line_limit (int):
            内网穿透地址所在的输出行数限制
    """

    def __init__(
        self,
        port: int,
        workspace: Path,
        ssh_args: list[str],
        url_pattern: re.Pattern[str],
        line_limit: int = 30,
    ) -> None:
        """初始化 SSH 隧道

        Args:
            port (int):
                要进行端口映射的端口
            workspace (Path):
                工作区路径
            ssh_args (list[str]):
                SSH 连接参数
            url_pattern (re.Pattern[str]):
                用于匹配内网穿透地址的正则表达式
            line_limit (int):
                内网穿透地址所在的输出行数限制, 默认 30
        """
        super().__init__(port, workspace)
        self.ssh_args = ssh_args
        self.url_pattern = url_pattern
        self.line_limit = line_limit
        self._ssh_key_path: Optional[Path] = None
        self._temp_dir: Optional[TemporaryDirectory] = None

    def _get_or_create_ssh_key(
        self,
    ) -> Path:
        """获取或创建 SSH 密钥

        Returns:
            Path: SSH 密钥路径
        """
        ssh_name = "id_rsa"
        ssh_path = self.workspace / ssh_name

        if not ssh_path.exists():
            if not gen_ssh_key(ssh_path):
                # 如果在工作区创建失败, 使用临时目录
                self._temp_dir = TemporaryDirectory()
                ssh_path = Path(self._temp_dir.name) / ssh_name
                gen_ssh_key(ssh_path)

        self._ssh_key_path = ssh_path
        return ssh_path

    def start(
        self,
    ) -> str:
        """启动 SSH 隧道

        Returns:
            str: 内网穿透地址

        Raises:
            RuntimeError: 启动内网穿透失败时
        """
        ssh_path = self._get_or_create_ssh_key()

        # 构建完整的 SSH 命令
        command = [
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-i",
            ssh_path.as_posix(),
        ] + self.ssh_args

        command_to_exec = preprocess_command(command, shell=True)

        # 启动 SSH 进程
        self._process = subprocess.Popen(
            command_to_exec,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            encoding="utf-8",
        )

        # 读取输出并提取 URL
        output_queue = queue.Queue()
        lines = []

        def _read_output():
            for line in iter(self._process.stdout.readline, ""):
                output_queue.put(line)
            self._process.stdout.close()

        thread = threading.Thread(target=_read_output)
        thread.daemon = True
        thread.start()

        # 尝试从输出中提取 URL
        for _ in range(self.line_limit):
            try:
                line = output_queue.get(timeout=10)
                lines.append(line)

                # 打印警告信息
                if line.startswith("Warning"):
                    print(line, end="")

                # 尝试匹配 URL
                url_match = self.url_pattern.search(line)
                if url_match:
                    self._url = url_match.group("url")
                    logger.info("%s 内网穿透启动完成", self.__class__.__name__)
                    return self._url
            except queue.Empty as e:
                logger.error("未捕获到指定输出, 输出内容列表: %s", lines)
                raise RuntimeError("运行 SSH 进程时未捕获到输出") from e
            except Exception as e:
                logger.error("运行 SSH 进程时发生错误: %s", e)
                raise RuntimeError(f"运行 SSH 进程时发生错误: {e}") from e

        raise RuntimeError("未捕获到内网穿透地址")

    def stop(
        self,
    ) -> None:
        """停止 SSH 隧道

        终止 SSH 进程并清理临时目录.
        """
        super().stop()

        # 清理临时目录
        if self._temp_dir:
            try:
                self._temp_dir.cleanup()
            except Exception as e:
                logger.error("清理临时目录失败: %s", e)
