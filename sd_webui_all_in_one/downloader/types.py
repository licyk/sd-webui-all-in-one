from typing import (
    Literal,
    TypeAlias,
    get_args,
)

DownloadToolType: TypeAlias = Literal["aria2", "requests", "urllib"]
"""可用的下载器类型"""

DOWNLOAD_TOOL_TYPE_LIST: list[str] = list(get_args(DownloadToolType))
"""可用的下载器类型列表"""

DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
"""默认 User-Agent 配置"""
