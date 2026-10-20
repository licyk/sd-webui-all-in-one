"""HuggingFace / ModelScope 仓库管理类型定义"""

from typing import Any, Literal, TypeAlias


ApiType: TypeAlias = Literal["huggingface", "modelscope"]
"""API 类型"""

RepoType: TypeAlias = Literal["model", "dataset", "space"]
"""HuggingFace / ModelScope 仓库类型"""

RepoFileType: TypeAlias = Literal["file", "directory"]
"""仓库条目类型"""

RepoFileMetadata: TypeAlias = dict[str, Any]
"""归一化后的仓库文件元数据"""

MirrorGroupTask: TypeAlias = tuple[str, int | None]
"""分组镜像任务, 格式为 (仓库文件路径, 文件大小), 文件大小未知时为`None`"""
