"""下载器类型定义"""

from pathlib import PureWindowsPath
from typing import (
    Literal,
    TypeAlias,
    get_args,
)

DownloadToolType: TypeAlias = Literal["aria2", "requests", "urllib"]
"""可用的下载器类型"""

ExistingFilePolicy: TypeAlias = Literal["reuse", "verify", "resume", "overwrite", "rename"]
"""正式目标文件已存在时的处理策略"""

DOWNLOAD_TOOL_TYPE_LIST: list[str] = list(get_args(DownloadToolType))
"""可用的下载器类型列表"""

EXISTING_FILE_POLICY_LIST: list[str] = list(get_args(ExistingFilePolicy))
"""已有文件处理策略列表"""

_WINDOWS_RESERVED_FILE_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def validate_download_file_name(file_name: str) -> str:
    """校验下载文件名；统一入口只允许单个文件名，不允许相对子目录"""
    if not isinstance(file_name, str) or not file_name or "\0" in file_name:
        raise ValueError("下载文件名不能为空或包含 NUL")
    if file_name in {".", ".."} or "/" in file_name or "\\" in file_name:
        raise ValueError("下载文件名必须是单个文件名，不能包含路径")

    windows_path = PureWindowsPath(file_name)
    if windows_path.drive or windows_path.root or windows_path.is_absolute():
        raise ValueError("下载文件名不能是绝对路径、驱动器路径或 UNC 路径")
    if file_name.endswith((" ", ".")):
        raise ValueError("下载文件名不能以空格或点结尾")
    reserved_stem = file_name.split(".", maxsplit=1)[0].rstrip(" .").upper()
    if reserved_stem in _WINDOWS_RESERVED_FILE_NAMES:
        raise ValueError(f"下载文件名使用了 Windows 保留名称: {file_name}")
    return file_name


DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
"""默认 User-Agent 配置"""
