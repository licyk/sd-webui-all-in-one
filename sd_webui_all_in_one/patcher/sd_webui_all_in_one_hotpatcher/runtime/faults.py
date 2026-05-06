"""faulthandler 原始通道转发工具"""

from __future__ import annotations

import faulthandler
import socket
from dataclasses import dataclass

from .client import RuntimeClient
from .protocol import encode_message


@dataclass
class FaultChannel:
    """
    faulthandler 原始输出通道

    Attributes:
        sock (socket.socket):
            与宿主连接的 TCP socket
        file (object | None):
            交给 faulthandler 使用的二进制文件对象
        enabled (bool):
            faulthandler 是否由当前对象启用
    """

    sock: socket.socket
    file: object | None
    enabled: bool

    def close(self) -> None:
        """关闭 fault 通道并按需禁用 faulthandler"""

        if self.enabled:
            faulthandler.disable()
            self.enabled = False
        if self.file is not None:
            self.file.close()
        self.sock.close()


def install_faulthandler(
    client: RuntimeClient,
    *,
    timeout: float = 5.0,
    all_threads: bool = False,
    enable: bool = True,
) -> FaultChannel:
    """
    安装 faulthandler 原始通道

    Args:
        client (RuntimeClient):
            已连接的运行时客户端
        timeout (float):
            fault 通道连接超时时间
        all_threads (bool):
            是否让 faulthandler 输出所有线程
        enable (bool):
            是否立即调用 ``faulthandler.enable``

    Returns:
        FaultChannel:
            已打开的 fault 通道
    """

    sock = socket.create_connection((client.host, client.port), timeout=timeout)
    sock.sendall(
        encode_message(
            {
                "type": "channel.open",
                "channel": "fault",
                "token": client.token,
            }
        )
    )
    file = sock.makefile("wb", buffering=0)
    if enable:
        faulthandler.enable(file=file, all_threads=all_threads)
    return FaultChannel(sock=sock, file=file, enabled=enable)
