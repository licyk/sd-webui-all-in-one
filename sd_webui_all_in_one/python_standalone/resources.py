"""已上传 Python 资源的解析、查询与输出"""

import json
import os
import re
import unicodedata
import urllib.parse
from collections.abc import Iterable

from sd_webui_all_in_one.archive_manager import SUPPORTED_CREATE_ARCHIVE_FORMAT
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.portable_manager import utc_update_time
from sd_webui_all_in_one.python_standalone.types import (
    DEFAULT_PATH_IN_REPO,
    DEFAULT_PLATFORMS,
    RESOURCE_TYPE,
    SOURCE_DISPLAY_NAME,
    PythonStandaloneResource,
    RepoTarget,
    ResourceListData,
    version_tuple,
)
from sd_webui_all_in_one.repo_manager import ApiType, RepoManager

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

RESOURCE_STEM_PATTERN = re.compile(r"^(?P<implementation>[^-]+)-(?P<version>[^-+]+)\+(?P<build_date>\d{8})-(?P<build_type>.+)$")
"""重新打包后的文件名 (不含扩展名) 的正则表达式"""

MS_ENDPOINT = "https://modelscope.cn"
"""ModelScope 下载地址"""

_REPO_TYPE_URL_PREFIX: dict[ApiType, dict[str, str]] = {
    "huggingface": {"model": "", "dataset": "datasets/", "space": "spaces/"},
    "modelscope": {"model": "models/", "dataset": "datasets/", "space": "studios/"},
}
"""各下载源不同仓库类型在下载链接中的路径前缀"""

_DEFAULT_REVISION: dict[ApiType, str] = {
    "huggingface": "main",
    "modelscope": "master",
}
"""各下载源的默认分支"""


def normalize_path_in_repo(
    path_in_repo: str | None = DEFAULT_PATH_IN_REPO,
) -> str:
    """规范化仓库中的目录

    Args:
        path_in_repo (str | None): 仓库中的目录, 为 None 或空字符串时表示仓库根目录
    Returns:
        str: 规范化后的目录, 不含首尾的 /
    Raises:
        ValueError: 路径包含父目录引用时
    """
    parts = []
    for part in (path_in_repo or "").replace("\\", "/").split("/"):
        if part in ["", "."]:
            continue
        if part == "..":
            raise ValueError("仓库目录不能包含 '..'")
        parts.append(part)
    return "/".join(parts)


def build_repo_path(
    path_in_repo: str,
    platform: str,
    archive_name: str,
) -> str:
    """获取 Python 资源在仓库中的路径

    Args:
        path_in_repo (str): 仓库中的 Python 资源目录
        platform (str): 平台, 如 linux/amd64
        archive_name (str): 文件名
    Returns:
        str: 仓库中的路径, 如 python/linux/amd64/<文件名>
    """
    return "/".join(part for part in [normalize_path_in_repo(path_in_repo), platform, archive_name] if part)


def build_download_url(
    target: RepoTarget,
    path: str,
    revision: str | None = None,
) -> str:
    """构建仓库文件的下载链接, 不需要访问网络

    HuggingFace 的地址可通过 HF_ENDPOINT 环境变量修改

    Args:
        target (RepoTarget): 仓库
        path (str): 仓库中的文件路径
        revision (str | None): 仓库分支, 为 None 时使用默认分支
    Returns:
        str: 下载链接
    """
    endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co") if target.source == "huggingface" else MS_ENDPOINT
    prefix = _REPO_TYPE_URL_PREFIX[target.source].get(target.repo_type, "")
    branch = urllib.parse.quote(revision or _DEFAULT_REVISION[target.source], safe="")
    return f"{endpoint.rstrip('/')}/{prefix}{target.repo_id}/resolve/{branch}/{urllib.parse.quote(path, safe='/+')}"


def split_archive_format(
    name: str,
) -> tuple[str, str] | None:
    """把文件名拆分为主体和压缩包格式

    Args:
        name (str): 文件名
    Returns:
        (tuple[str, str] | None): (主体, 压缩包格式), 不是支持的压缩包格式时返回 None
    """
    lower = name.lower()
    for archive_format in sorted(SUPPORTED_CREATE_ARCHIVE_FORMAT, key=len, reverse=True):
        if lower.endswith(archive_format):
            return name[: -len(archive_format)], archive_format
    return None


def parse_resource_path(
    path: str,
    path_in_repo: str | None = DEFAULT_PATH_IN_REPO,
    platforms: dict[str, str] | None = None,
) -> PythonStandaloneResource | None:
    """解析仓库中 Python 资源的路径

    路径格式为 <path_in_repo>/<系统>/<架构>/<实现>-<版本>+<构建日期>-<三元组>-<变体><格式>

    Args:
        path (str): 仓库中的文件路径
        path_in_repo (str | None): 仓库中的 Python 资源目录
        platforms (dict[str, str] | None): 平台到构建目标三元组的映射, 用于拆分三元组和变体
    Returns:
        (PythonStandaloneResource | None): 资源信息 (不含下载链接), 不是 Python 资源时返回 None
    """
    prefix = normalize_path_in_repo(path_in_repo)
    if prefix and not path.startswith(f"{prefix}/"):
        return None
    parts = path[len(prefix) + 1 :].split("/") if prefix else path.split("/")
    if len(parts) != 3:
        return None
    system, arch, name = parts
    split = split_archive_format(name)
    if split is None:
        return None
    stem, archive_format = split
    match = RESOURCE_STEM_PATTERN.match(stem)
    if match is None:
        return None

    build_type = match.group("build_type")
    mapping = {**DEFAULT_PLATFORMS, **(platforms or {})}
    candidates = [mapping[f"{system}/{arch}"]] if f"{system}/{arch}" in mapping else []
    candidates += sorted(set(mapping.values()), key=len, reverse=True)
    triple = next((t for t in candidates if build_type.startswith(f"{t}-")), None)
    variant = build_type[len(triple) + 1 :] if triple else build_type
    version = match.group("version")
    return {
        "type": RESOURCE_TYPE,
        "name": name,
        "implementation": match.group("implementation"),
        "version": version,
        "minor": ".".join(version.split(".")[:2]),
        "build_date": match.group("build_date"),
        "platform": system,
        "arch": arch,
        "triple": triple,
        "variant": variant,
        "archive_format": archive_format,
        "path": path,
        "size": None,
        "sha256": None,
        "urls": {},
    }


def collect_resources(
    manager: RepoManager,
    targets: list[RepoTarget],
    path_in_repo: str | None = DEFAULT_PATH_IN_REPO,
    revision: str | None = None,
    platforms: dict[str, str] | None = None,
) -> list[PythonStandaloneResource]:
    """从仓库中收集已上传的 Python 资源, 同一路径在多个仓库中的资源会合并为一条

    Args:
        manager (RepoManager): 仓库管理器
        targets (list[RepoTarget]): 要查询的仓库
        path_in_repo (str | None): 仓库中的 Python 资源目录
        revision (str | None): 仓库分支
        platforms (dict[str, str] | None): 平台到构建目标三元组的映射
    Returns:
        list[PythonStandaloneResource]: 资源列表
    """
    merged: dict[str, PythonStandaloneResource] = {}
    for target in targets:
        metadata = manager.get_repo_files_metadata(
            api_type=target.source,
            repo_id=target.repo_id,
            repo_type=target.repo_type,
            revision=revision,
        )
        count = 0
        for item in metadata:
            path = str(item.get("path") or "")
            resource = merged.get(path) or parse_resource_path(path, path_in_repo, platforms)
            if resource is None:
                continue
            count += 1
            resource["size"] = resource["size"] or item.get("size")
            resource["sha256"] = resource["sha256"] or item.get("sha256")
            resource["urls"][target.source] = build_download_url(target, path, revision)
            merged[path] = resource
        logger.info("%s 中有 %s 个 Python 资源", target.display_name, count)
    return list(merged.values())


def filter_resources(
    resources: Iterable[PythonStandaloneResource],
    versions: list[str] | None = None,
    platforms: list[str] | None = None,
    variants: list[str] | None = None,
    archive_formats: list[str] | None = None,
    build_date: str | None = None,
    latest_only: bool = True,
) -> list[PythonStandaloneResource]:
    """筛选资源

    Args:
        resources (Iterable[PythonStandaloneResource]): 资源列表
        versions (list[str] | None): 保留的主次版本号或完整版本号, 为 None 时不筛选
        platforms (list[str] | None): 保留的平台 (如 linux/amd64) 或系统 (如 linux), 为 None 时不筛选
        variants (list[str] | None): 保留的构建变体, 为 None 时不筛选
        archive_formats (list[str] | None): 保留的压缩包格式, 为 None 时不筛选
        build_date (str | None): 只保留该构建日期的资源, 为 None 时不筛选
        latest_only (bool): 每个 (平台, 主次版本, 变体, 格式) 组合只保留最新的构建
    Returns:
        list[PythonStandaloneResource]: 筛选并排序后的资源列表
    """
    result = []
    for r in resources:
        if versions and r["minor"] not in versions and r["version"] not in versions:
            continue
        if platforms and f"{r['platform']}/{r['arch']}" not in platforms and r["platform"] not in platforms:
            continue
        if variants and r["variant"] not in variants:
            continue
        if archive_formats and r["archive_format"] not in archive_formats:
            continue
        if build_date and r["build_date"] != build_date:
            continue
        result.append(r)

    if latest_only:
        latest: dict[tuple[str, ...], PythonStandaloneResource] = {}
        for r in result:
            key = (r["implementation"], r["platform"], r["arch"], r["minor"], r["variant"], r["archive_format"])
            current = latest.get(key)
            if current is None or (r["build_date"], version_tuple(r["version"])) > (current["build_date"], version_tuple(current["version"])):
                latest[key] = r
        result = list(latest.values())
    return sort_resources(result)


def sort_resources(
    resources: Iterable[PythonStandaloneResource],
) -> list[PythonStandaloneResource]:
    """按平台、版本 (新到旧)、构建日期 (新到旧) 排序资源

    Args:
        resources (Iterable[PythonStandaloneResource]): 资源列表
    Returns:
        list[PythonStandaloneResource]: 排序后的资源列表
    """
    platform_order = {platform: index for index, platform in enumerate(DEFAULT_PLATFORMS)}
    resources = sorted(resources, key=lambda r: r["name"])
    resources = sorted(resources, key=lambda r: (r["build_date"], version_tuple(r["version"])), reverse=True)
    return sorted(resources, key=lambda r: platform_order.get(f"{r['platform']}/{r['arch']}", len(platform_order)))


def build_resource_list_data(
    resources: list[PythonStandaloneResource],
    targets: list[RepoTarget],
    latest_only: bool,
) -> ResourceListData:
    """构建资源查询结果

    Args:
        resources (list[PythonStandaloneResource]): 资源列表
        targets (list[RepoTarget]): 查询的仓库
        latest_only (bool): 是否只包含最新构建
    Returns:
        ResourceListData: 查询结果
    """
    return {
        "type": RESOURCE_TYPE,
        "generated_at": utc_update_time(),
        "sources": [t.display_name for t in targets],
        "latest_only": latest_only,
        "resources": resources,
    }


def format_size(
    size: int | None,
) -> str:
    """把文件大小格式化为便于阅读的文本

    Args:
        size (int | None): 文件大小 (字节)
    Returns:
        str: 格式化后的文本, 如 45.2 MB, 未知时为 -
    """
    if size is None:
        return "-"
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def display_width(
    text: str,
) -> int:
    """获取文本在终端中的显示宽度, 中文等宽字符按 2 计算

    Args:
        text (str): 文本
    Returns:
        int: 显示宽度
    """
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def render_table(
    headers: list[str],
    rows: list[list[str]],
) -> str:
    """把数据渲染为按显示宽度对齐的文本表格

    Args:
        headers (list[str]): 表头
        rows (list[list[str]]): 数据行
    Returns:
        str: 表格文本
    """
    widths = [max(display_width(str(c)) for c in col) for col in zip(headers, *rows, strict=False)]
    lines = ["  ".join(str(c) + " " * (w - display_width(str(c))) for c, w in zip(row, widths, strict=False)).rstrip() for row in [headers, *rows]]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def render_resources_table(
    resources: list[PythonStandaloneResource],
) -> str:
    """把资源列表渲染为终端表格

    Args:
        resources (list[PythonStandaloneResource]): 资源列表
    Returns:
        str: 表格文本
    """
    rows = [
        [
            r["version"],
            f"{r['platform']}/{r['arch']}",
            r["variant"],
            r["archive_format"],
            r["build_date"],
            format_size(r["size"]),
            ",".join(SOURCE_DISPLAY_NAME.get(s, s) for s in r["urls"]),
        ]
        for r in resources
    ]
    return f"{render_table(['版本', '平台', '变体', '格式', '构建日期', '大小', '下载源'], rows)}\n\n共 {len(resources)} 个资源"


def render_download_links(
    urls: dict[str, str],
) -> str:
    """把下载链接渲染为 Markdown 链接

    Args:
        urls (dict[str, str]): 下载源到下载链接的映射
    Returns:
        str: Markdown 链接文本, 没有链接时为 -
    """
    links = [f"[{SOURCE_DISPLAY_NAME.get(source, source)}]({url})" for source, url in urls.items()]
    return " / ".join(links) or "-"


def render_resources_markdown(
    resources: list[PythonStandaloneResource],
    title: str | None = "Python 资源列表",
) -> str:
    """把资源列表渲染为按平台分组的 Markdown

    Args:
        resources (list[PythonStandaloneResource]): 资源列表
        title (str | None): 标题, 为 None 时不输出标题
    Returns:
        str: Markdown 文本
    """
    lines = [f"## {title}", ""] if title else []
    lines += [f"生成时间: {utc_update_time()}, 共 {len(resources)} 个资源", ""]
    groups: dict[str, list[PythonStandaloneResource]] = {}
    for r in resources:
        groups.setdefault(f"{r['platform']}/{r['arch']}", []).append(r)
    for platform, items in groups.items():
        lines += [f"### {platform}", "", "| 类型 | 名称 | 版本 | 变体 | 构建日期 | 大小 | 下载链接 |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in items:
            lines.append(f"| {r['type']} | `{r['name']}` | {r['version']} | {r['variant']} | {r['build_date']} | {format_size(r['size'])} | {render_download_links(r['urls'])} |")
        lines.append("")
    return "\n".join(lines)


def render_json(
    data: object,
) -> str:
    """把数据渲染为 JSON 文本

    Args:
        data (object): 数据
    Returns:
        str: JSON 文本
    """
    return json.dumps(data, ensure_ascii=False, indent=2)
