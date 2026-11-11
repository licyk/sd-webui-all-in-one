"""faulthandler 原始通道转发工具"""

from __future__ import annotations

import faulthandler
import socket
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .client import RuntimeClient
from .protocol import encode_message

if TYPE_CHECKING:
    from ..state import HotpatcherState


@dataclass
class FaultChannel:
    """
    faulthandler 原始输出通道

    Attributes:
        sock (socket.socket):
            与宿主连接的 TCP socket
        file (Any | None):
            交给 faulthandler 使用的二进制文件对象
        enabled (bool):
            faulthandler 是否由当前对象启用
        client (Any):
            打开该通道的运行时客户端, 连接管理器据此判断切换连接时是否需要重新打开
        all_threads (bool):
            faulthandler 是否输出所有线程
        timeout (float):
            fault 通道连接超时时间
        closed (bool):
            通道是否已关闭
    """

    sock: socket.socket
    file: Any | None
    enabled: bool
    client: Any = None
    all_threads: bool = False
    timeout: float = 5.0
    closed: bool = False

    def close(self) -> None:
        """关闭 fault 通道并按需禁用 faulthandler"""

        self.closed = True
        if self.enabled:
            faulthandler.disable()
            self.enabled = False
        if self.file is not None:
            self.file.close()
        if self.sock is not None:
            self.sock.close()


def open_fault_channel(
    host: str,
    port: int,
    token: str,
    *,
    timeout: float = 5.0,
    all_threads: bool = False,
    enable: bool = True,
    client: Any = None,
) -> FaultChannel:
    """
    连接指定宿主并打开 faulthandler 原始通道

    Args:
        host (str):
            宿主地址
        port (int):
            宿主端口
        token (str):
            通道握手 token
        timeout (float):
            fault 通道连接超时时间
        all_threads (bool):
            是否让 faulthandler 输出所有线程
        enable (bool):
            是否立即调用 ``faulthandler.enable``
        client (Any):
            记录到通道上的运行时客户端

    Returns:
        FaultChannel:
            已打开的 fault 通道
    """

    sock = socket.create_connection((host, port), timeout=timeout)
    sock.sendall(
        encode_message(
            {
                "type": "channel.open",
                "channel": "fault",
                "token": token,
            }
        )
    )
    file = sock.makefile("wb", buffering=0)
    if enable:
        faulthandler.enable(file=file, all_threads=all_threads)
    return FaultChannel(sock=sock, file=file, enabled=enable, client=client, all_threads=all_threads, timeout=timeout)


def install_faulthandler(
    client: RuntimeClient,
    *,
    timeout: float = 5.0,
    all_threads: bool = False,
    enable: bool = True,
    state: HotpatcherState | None = None,
) -> FaultChannel:
    """
    安装 faulthandler 原始通道

    通道记录到 ``state.fault_channel``, 连接管理器切换连接时会在新宿主上重新打开它。

    Args:
        client (RuntimeClient):
            已连接的运行时客户端
        timeout (float):
            fault 通道连接超时时间
        all_threads (bool):
            是否让 faulthandler 输出所有线程
        enable (bool):
            是否立即调用 ``faulthandler.enable``
        state (HotpatcherState | None):
            记录通道的状态对象。为 None 时使用默认状态。

    Returns:
        FaultChannel:
            已打开的 fault 通道
    """

    from ..state import get_default_state

    channel = open_fault_channel(
        client.host,
        client.port,
        client.token,
        timeout=timeout,
        all_threads=all_threads,
        enable=enable,
        client=client,
    )
    (state or get_default_state()).fault_channel = channel
    return channel
