"""Implementation grouped from the former ``comfy_registry.py`` module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

COMFY_REGISTRY_BASE_URL = "https://api.comfy.org"

COMFY_REGISTRY_ACTIVE_VERSION_STATUSES = ("NodeVersionStatusActive", "NodeVersionStatusPending")

COMFY_REGISTRY_UNAVAILABLE_STATUS = "Registry 无可安装版本"

COMFY_REGISTRY_DEFAULT_PAGE_SIZE = 500

COMFY_REGISTRY_CACHE_TTL_SECONDS = 6 * 60 * 60

ComfyRegistryProgressCallback = Callable[[int, int | None], object]


class ComfyRegistryInstallUnavailableError(ValueError):
    """Comfy Registry 节点没有可安装 CNR 版本。"""

    def __init__(
        self,
        node_id: str,
        version: str | None = None,
        reason: str = COMFY_REGISTRY_UNAVAILABLE_STATUS,
        http_status: int | None = None,
    ) -> None:
        self.node_id = node_id
        self.version = version
        self.reason = reason
        self.http_status = http_status
        status_text = f"HTTP {http_status}, " if http_status is not None else ""
        super().__init__(f"Comfy Registry 节点不可安装: {node_id}@{version or 'latest'}; {status_text}{reason}。Registry 中存在节点记录，但没有可安装 CNR 版本。")


@dataclass(slots=True)
class ComfyRegistryNodeVersion:
    """Comfy Registry 节点版本元数据。"""

    node_id: str
    version: str
    download_url: str = ""
    dependencies: list[str] = field(default_factory=list)
    status: str = ""
    created_at: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ComfyRegistryNode:
    """Comfy Registry 节点元数据。"""

    id: str
    name: str
    author: str = ""
    description: str = ""
    repository: str = ""
    tags: tuple[str, ...] = ()
    latest_version: ComfyRegistryNodeVersion | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ComfyRegistryLocalInfo:
    """本地已安装的 Comfy Registry 节点元数据。"""

    registry_id: str
    original_name: str
    version: str
    repository: str | None = None
