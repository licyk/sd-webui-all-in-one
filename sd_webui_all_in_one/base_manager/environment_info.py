"""WebUI 环境信息报告。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from sd_webui_all_in_one.base_manager.base import HostEnvironmentInfo, collect_host_environment_info
from sd_webui_all_in_one.base_manager.snapshot import JsonObject, WebUiSnapshot, snapshot_to_dict


ENVIRONMENT_INFO_SCHEMA_VERSION = 1
"""环境信息报告结构版本。"""


@dataclass(frozen=True, slots=True)
class WebUiEnvironmentInfo:
    """包含主机信息和 WebUI 快照的环境信息报告。"""

    schema_version: int
    """环境信息报告结构版本。"""

    created_at: str
    """报告创建时间。"""

    environment: HostEnvironmentInfo
    """与具体 WebUI 无关的主机环境信息。"""

    snapshot: WebUiSnapshot
    """WebUI 环境快照。"""

    def to_dict(self) -> JsonObject:
        """转换为 JSON 可序列化对象。

        Returns:
            JsonObject: 环境信息报告对象。
        """
        return cast(JsonObject, snapshot_to_dict(self))


def build_webui_environment_info(snapshot: WebUiSnapshot) -> WebUiEnvironmentInfo:
    """将 WebUI 快照和当前主机信息组合为环境报告。

    Args:
        snapshot (WebUiSnapshot): 已采集的 WebUI 快照。

    Returns:
        WebUiEnvironmentInfo: 完整环境信息报告。
    """
    return WebUiEnvironmentInfo(
        schema_version=ENVIRONMENT_INFO_SCHEMA_VERSION,
        created_at=snapshot.created_at,
        environment=collect_host_environment_info(),
        snapshot=snapshot,
    )


def save_webui_environment_info(
    info: WebUiEnvironmentInfo,
    output: Path,
    overwrite: bool = False,
) -> Path:
    """保存 WebUI 环境信息报告。

    Args:
        info (WebUiEnvironmentInfo): 要保存的环境信息报告。
        output (Path): 精确输出文件路径。
        overwrite (bool): 是否允许覆盖已有文件。

    Returns:
        Path: 已写入的文件路径。

    Raises:
        FileExistsError: 输出文件已存在且未允许覆盖。
        IsADirectoryError: 输出路径指向目录。
    """
    if output.is_dir():
        raise IsADirectoryError(f"环境信息输出路径不能是目录: {output}")
    if output.exists() and not overwrite:
        raise FileExistsError(f"环境信息文件已存在: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(info.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return output
