"""生成便携包发布说明的脚本

该脚本用于从便携包列表 JSON 数据生成 Markdown 格式的发布说明，
支持 ModelScope 和 HuggingFace 两个下载源的链接展示。
"""

import subprocess
import os
import sys
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
from pathlib import Path
from typing import Any

import requests


UTC_PLUS_8 = timezone(timedelta(hours=8))
"""整合包更新时间显示时区。"""


def fetch_portable_list(
    url: str,
) -> dict[str, Any]:
    """获取便携包列表 JSON 数据

    Args:
        url (str):
            便携包列表 JSON 文件的 URL

    Returns:
        (dict[str, Any]):
            解析后的 JSON 数据字典
    """
    response = requests.get(
        url=url,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_portable_resources(
    data: Mapping[str, Any],
) -> Mapping[str, Any]:
    """获取新版整合包资源节点"""
    resources = data.get("resources")
    if not isinstance(resources, Mapping):
        raise ValueError("整合包列表格式不正确：缺少 resources 字段")
    return resources


def get_update_time(
    data: Mapping[str, Any],
) -> str:
    """获取整合包列表更新时间"""
    update_time = data.get("update_time")
    if not isinstance(update_time, str) or not update_time:
        raise ValueError("整合包列表格式不正确：缺少 update_time 字段")
    return update_time


def format_update_time(
    update_time: str,
) -> str:
    """将 ISO 更新时间格式化为 UTC+8 时间"""
    try:
        normalized_update_time = update_time.removesuffix("Z") + "+00:00" if update_time.endswith("Z") else update_time
        parsed_update_time = datetime.fromisoformat(normalized_update_time)
        if parsed_update_time.tzinfo is None:
            parsed_update_time = parsed_update_time.replace(tzinfo=timezone.utc)

        display_update_time = parsed_update_time.astimezone(UTC_PLUS_8)
        return f"{display_update_time:%Y-%m-%d %H:%M:%S} (UTC+08:00)"
    except ValueError:
        return update_time


def get_source_resources(
    data: Mapping[str, Any],
    source: str,
) -> Mapping[str, Any]:
    """获取指定下载源的资源节点"""
    resources = get_portable_resources(data)
    source_resources = resources.get(source, {})
    if not isinstance(source_resources, Mapping):
        return {}
    return source_resources


def get_resource_node(
    data: Mapping[str, Any],
    source: str,
    project: str,
) -> Mapping[str, Any]:
    """获取指定下载源下的整合包资源节点"""
    project_data = get_source_resources(data, source).get(project, {})
    if not isinstance(project_data, Mapping):
        return {}
    return project_data


def get_project_display_name(
    data: Mapping[str, Any],
    project: str,
) -> str:
    """获取整合包显示名称"""
    for source in ("modelscope", "huggingface"):
        display_name = get_resource_node(data, source, project).get("display_name")
        if isinstance(display_name, str) and display_name:
            return display_name
    return project


def get_projects(
    data: Mapping[str, Any],
    version_type: str,
) -> list[str]:
    """获取指定版本类型下所有整合包资源键"""
    projects: set[str] = set()

    for source_resources in get_portable_resources(data).values():
        if not isinstance(source_resources, Mapping):
            continue
        for project, project_data in source_resources.items():
            if not isinstance(project, str) or not isinstance(project_data, Mapping):
                continue
            version_data = project_data.get(version_type)
            if isinstance(version_data, list) and version_data:
                projects.add(project)

    return sorted(projects, key=lambda name: get_project_display_name(data, name).casefold())


def get_download_link(
    data: Mapping[str, Any],
    source: str,
    version_type: str,
    project: str,
) -> str:
    """获取下载链接

    从便携包列表数据中提取指定项目在下载源和版本类型下的下载链接

    Args:
        data (dict[str, Any]):
            便携包列表数据
        source (str):
            下载源，可选值："modelscope" 或 "huggingface"
        version_type (str):
            版本类型，可选值："stable" 或 "nightly"
        project (str):
            项目名称

    Returns:
        str: Markdown 格式的下载链接，格式为 "[文件名](URL)"；如果不存在则返回"暂无"

    Example:
        >>> get_download_link(data, "modelscope", "stable", "ComfyUI")
        '[comfyui-licyk-v2.2.7z](https://modelscope.cn/...)'
    """
    project_data = get_resource_node(data, source, project)
    version_data = project_data.get(version_type)
    if not isinstance(version_data, list) or not version_data:
        return "暂无"

    latest = version_data[0]
    if not isinstance(latest, Mapping):
        return "暂无"

    filename = latest.get("filename")
    url = latest.get("url")
    if not isinstance(filename, str) or not isinstance(url, str) or not filename or not url:
        return "暂无"
    return f"[{filename}]({url})"


def generate_markdown_table(
    data: Mapping[str, Any],
    version_type: str,
    title: str,
) -> list[str]:
    """生成 Markdown 表格

    根据便携包列表数据生成包含 ModelScope 和 HuggingFace 下载链接的表格

    Args:
        data (dict[str, Any]):
            便携包列表数据
        version_type (str):
            版本类型 ("stable" 或 "nightly")
        title (str):
            表格标题（如 "Stable 版整合包"）

    Returns:
        list[str]:
            Markdown 表格行列表，每行代表表格的一行

    Example:
        >>> table_lines = generate_markdown_table(data, "stable", "Stable 版整合包")
        >>> for line in table_lines:
        ...     print(line)
    """
    lines: list[str] = []

    projects = get_projects(data, version_type)

    if not projects:
        return lines

    # 表格标题
    lines.append(f"|{title}|最新版本 (ModelScope)|最新版本 (HuggingFace)|")
    lines.append("|---|---|---|")

    # 遍历所有项目
    for project in projects:
        project_name = get_project_display_name(data, project)
        ms_link = get_download_link(data, "modelscope", version_type, project)
        hf_link = get_download_link(data, "huggingface", version_type, project)
        lines.append(f"|{project_name}|{ms_link}|{hf_link}|")

    return lines


def main() -> None:
    """主函数

    执行以下操作：
    1. 从远程 URL 下载便携包列表 JSON 数据
    2. 提取更新时间信息
    3. 生成 Stable 和 Nightly 版本的下载链接表格
    4. 将完整的 Markdown 内容写入到发布说明文件
    """
    portable_list_url: str = "https://github.com/licyk/resources/raw/gh-pages/portable_list.json"

    # 获取便携包列表数据
    print("正在下载便携包列表...")
    data: dict[str, Any] = fetch_portable_list(portable_list_url)

    # 获取更新时间
    update_time: str = format_update_time(get_update_time(data))
    print(f"更新时间：{update_time}")

    # 构建 Markdown 内容
    markdown_lines: list[str] = [
        "详细说明与使用请阅读：[AI 绘画 / 训练整合包 · licyk/sd-webui-all-in-one · Discussion #1](https://github.com/licyk/sd-webui-all-in-one/discussions/1)",
        "---",
        f"- 更新时间：`{update_time}`",
        "- 所有历史版本下载：[AI 绘画 / 训练整合包下载列表](https://licyk.github.io/t/#/sd_portable)",
        "- 建议使用 [7-Zip](https://7-zip.org/) / [Bandizip](https://www.bandisoft.com/bandizip/) 解压整合包",
        "- Nightly 整合包相比 Stable 整合包，版本较新，推荐使用",
        "- Windows 用户可使用下载器进行下载，内置高速下载器和解压工具，安装更方便。下载地址：[下载地址 1](https://github.com/licyk/sd-webui-all-in-one/releases/download/portable/sd_portable_downloader.bat) / [下载地址 2](https://gitee.com/licyk/sd-webui-all-in-one/releases/download/portable/sd_portable_downloader.bat)",
        "---",
    ]

    # 生成 Stable 版本表格
    print("正在生成 Stable 版本表格...")
    stable_table: list[str] = generate_markdown_table(data, "stable", "Stable 版整合包")
    markdown_lines.extend(stable_table)
    markdown_lines.append("")

    # 生成 Nightly 版本表格
    print("正在生成 Nightly 版本表格...")
    nightly_table: list[str] = generate_markdown_table(data, "nightly", "Nightly 版整合包")
    markdown_lines.extend(nightly_table)

    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        release_note_file: Path = tmp_dir / "portable_release_note.md"
        os.environ["gitee_owner"] = "licyk"
        os.environ["gitee_repo"] = "sd-webui-all-in-one"
        os.environ["gitee_release_id"] = "portable"
        os.environ["gitee_release_body_file"] = release_note_file.as_posix()

        # 写入文件
        with open(release_note_file, "w", encoding="utf-8") as f:
            f.write("\n".join(markdown_lines))

        subprocess.run(
            [
                "gh",
                "release",
                "edit",
                "portable",
                "--notes-file",
                release_note_file.as_posix(),
                "--repo",
                "licyk/sd-webui-all-in-one",
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        subprocess.run(
            [
                Path(sys.executable).as_posix(),
                (Path(__file__).parent / "gitee_release.py").as_posix(),
            ],
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        print("说明发布完成")


if __name__ == "__main__":
    main()
