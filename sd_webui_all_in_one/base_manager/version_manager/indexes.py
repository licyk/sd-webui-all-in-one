"""扩展索引和 PyPI 版本查询。"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,too-many-locals

import json
import urllib.request
from typing import (
    Any,
    Iterable,
    Literal,
)

from sd_webui_all_in_one.base_manager.base import (
    get_repo_name_from_url,
)
from sd_webui_all_in_one.base_manager.repository_inspector import (
    RepositoryState,  # noqa: F401
)
from sd_webui_all_in_one.package_analyzer import CommonVersionComparison, PyWhlVersionComparison, get_package_version_from_library, is_prerelease_version, parse_version_component

from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


DEFAULT_EXTENSION_INDEX_URL = "https://raw.githubusercontent.com/AUTOMATIC1111/stable-diffusion-webui-extensions/master/index.json"
"""AUTOMATIC1111 扩展源地址"""


ExtensionSourceType = Literal["git", "comfy-registry", "file", "unknown"]
"""扩展安装来源类型"""


from sd_webui_all_in_one.base_manager.version_manager.models import ExtensionIndexItem, PackageVersionInfo


def _pick_extension_name(item: dict[str, Any]) -> str:
    for key in ("name", "title", "extension_name"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    url = item.get("url") or item.get("link") or item.get("git")
    if isinstance(url, str) and url.strip():
        return get_repo_name_from_url(url)
    return "unknown"


def _pick_extension_url(item: dict[str, Any]) -> str:
    for key in ("url", "link", "git", "repo"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _pick_extension_description(item: dict[str, Any]) -> str:
    for key in ("description", "desc", "summary", "info"):
        value = item.get(key)
        if isinstance(value, str):
            return value.strip()
    return ""


def _pick_extension_tags(item: dict[str, Any]) -> tuple[str, ...]:
    value = item.get("tags") or item.get("tag")
    if isinstance(value, str):
        return tuple(x.strip() for x in value.split(",") if x.strip())
    if isinstance(value, list):
        return tuple(str(x).strip() for x in value if str(x).strip())
    return ()


def _pick_extension_files(item: dict[str, Any]) -> tuple[str, ...]:
    value = item.get("files")
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(x).strip() for x in value if str(x).strip())
    url = _pick_extension_url(item)
    return (url,) if url else ()


def parse_extension_index(data: Any) -> list[ExtensionIndexItem]:
    """
    解析 A1111 扩展源 JSON

    Args:
        data (Any):
            已反序列化的扩展源数据

    Returns:
        list[ExtensionIndexItem]: 扩展源条目列表
    """
    if isinstance(data, dict):
        raw_extensions = data.get("extensions", [])
    elif isinstance(data, list):
        raw_extensions = data
    else:
        raw_extensions = []
        logger.warning("扩展源数据类型异常, 返回空列表")

    logger.debug("解析扩展源数据, 共 %s 条原始条目", len(raw_extensions))
    items: list[ExtensionIndexItem] = []
    for raw_item in raw_extensions:
        if not isinstance(raw_item, dict):
            logger.warning("跳过非字典类型的扩展源条目")
            continue
        url = _pick_extension_url(raw_item)
        if not url:
            logger.warning("跳过缺少下载地址的扩展源条目")
            continue
        items.append(
            ExtensionIndexItem(
                name=_pick_extension_name(raw_item),
                url=url,
                description=_pick_extension_description(raw_item),
                tags=_pick_extension_tags(raw_item),
                install_type=str(raw_item.get("install_type") or "git-clone"),
                files=_pick_extension_files(raw_item),
                reference=str(raw_item.get("reference") or ""),
            )
        )
    logger.info("解析扩展源完成, 共 %s 个条目", len(items))
    return items


def parse_comfyui_custom_node_index(data: Any) -> list[ExtensionIndexItem]:
    """
    解析 ComfyUI-Manager 自定义节点列表

    Args:
        data (Any):
            已反序列化的自定义节点列表

    Returns:
        list[ExtensionIndexItem]: 扩展源条目列表
    """
    if isinstance(data, dict):
        raw_extensions = data.get("custom_nodes", [])
    elif isinstance(data, list):
        raw_extensions = data
    else:
        raw_extensions = []
        logger.warning("自定义节点数据类型异常, 返回空列表")

    logger.debug("解析自定义节点列表, 共 %s 条原始数据", len(raw_extensions))
    items: list[ExtensionIndexItem] = []
    for raw_item in raw_extensions:
        if not isinstance(raw_item, dict):
            logger.warning("跳过非字典类型的自定义节点条目")
            continue
        files = _pick_extension_files(raw_item)
        reference = str(raw_item.get("reference") or "")
        url = files[0] if files else reference
        if not url:
            logger.warning("跳过缺少下载地址的自定义节点条目")
            continue
        title = raw_item.get("title") or raw_item.get("name") or raw_item.get("id")
        name = str(title).strip() if title else get_repo_name_from_url(reference or url)
        tags = _pick_extension_tags(raw_item)
        author = raw_item.get("author")
        author_name = author.strip() if isinstance(author, str) and author.strip() else ""
        if author_name:
            tags = (*tags, author_name)
        install_type = str(raw_item.get("install_type") or "git-clone")
        items.append(
            ExtensionIndexItem(
                name=name,
                url=url,
                description=_pick_extension_description(raw_item),
                tags=tags,
                install_type=install_type,
                files=files,
                reference=reference,
                author=author_name,
            )
        )
    logger.info("解析自定义节点列表完成, 共 %s 个条目", len(items))
    return items


def fetch_extension_index(
    index_url: str = DEFAULT_EXTENSION_INDEX_URL,
    timeout: int | None = 20,
) -> list[ExtensionIndexItem]:
    """
    下载并解析扩展源列表

    Args:
        index_url (str):
            扩展源地址
        timeout (int | None):
            网络请求超时时间

    Returns:
        list[ExtensionIndexItem]: 扩展源条目列表
    """
    logger.info("获取扩展源列表中: %s", index_url)
    req = urllib.request.Request(index_url, headers={"User-Agent": "SD-WebUI-All-In-One"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    items = parse_extension_index(json.loads(payload))
    logger.info("获取扩展源列表完成, 共 %s 个条目", len(items))
    return items


def fetch_comfyui_custom_node_index(index_url: str, timeout: int | None = 20) -> list[ExtensionIndexItem]:
    """
    下载并解析 ComfyUI-Manager 扩展源

    Args:
        index_url (str):
            扩展源地址
        timeout (int | None):
            网络请求超时时间

    Returns:
        list[ExtensionIndexItem]: 扩展源条目列表
    """
    logger.info("获取自定义节点列表中: %s", index_url)
    req = urllib.request.Request(index_url, headers={"User-Agent": "SD-WebUI-All-In-One"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    items = parse_comfyui_custom_node_index(json.loads(payload))
    logger.info("获取自定义节点列表完成, 共 %s 个条目", len(items))
    return items


def _pypi_version_sort_key(
    version: str,
) -> tuple[int, PyWhlVersionComparison | CommonVersionComparison]:
    """构造 PyPI 版本号排序键

    PyPI 发布的版本号遵循 PEP 440, 用 PEP 440 比较器排序才能把 ``1.0.post1`` 排在
    ``1.0`` 之后、把 ``1.0rc1`` 排在 ``1.0`` 之前; 通用比较器无法正确处理这两种后缀.
    镜像源可能返回不符合 PEP 440 的版本号, 这类版本号回退到通用比较器, 并统一排在
    可解析版本号之后, 避免解析异常中断整个版本列表.

    Args:
        version (str):
            版本号字符串

    Returns:
        tuple[int, PyWhlVersionComparison | CommonVersionComparison]:
            排序键. 第 1 项区分可解析与不可解析版本号, 保证两类版本号之间不会
            跨比较器比较.
    """
    if parse_version_component(version) is None:
        logger.debug("版本号 '%s' 不符合 PEP 440, 使用通用比较器排序", version)
        return (0, CommonVersionComparison(version))
    return (1, PyWhlVersionComparison(version))


def fetch_pypi_versions(
    package_name: str,
    current_version: str | None = None,
    index_url: str = "https://pypi.org/pypi",
    timeout: int | None = 20,
) -> list[PackageVersionInfo]:
    """
    从 PyPI JSON API 获取软件包版本列表

    Args:
        package_name (str):
            PyPI 软件包名称
        current_version (str | None):
            当前安装版本; 为 None 时从当前运行环境解析已安装版本
        index_url (str):
            PyPI 或 PyPI 镜像源地址
        timeout (int | None):
            网络请求超时时间

    Returns:
        list[PackageVersionInfo]: 软件包版本信息列表, 按版本号从新到旧排序.
            每项的 ``is_prerelease`` 标记该版本是预发布版本还是正式发布版本,
            调用方据此区分发布通道, 无需自行解析版本号字符串.
    """
    # 未显式传入当前版本时按运行环境解析, 否则调用方无法得到 is_current 标记。
    if current_version is None:
        current_version = get_package_version_from_library(package_name)
    logger.debug("获取软件包版本列表: %s, 当前版本: %s", package_name, current_version)
    base_url = index_url.rstrip("/")
    if base_url.endswith("/simple"):
        base_url = base_url.removesuffix("/simple")
    if "pypi.org/simple" in base_url:
        base_url = base_url.replace("pypi.org/simple", "pypi.org/pypi")
    if base_url.endswith("/pypi"):
        url = f"{base_url}/{package_name}/json"
    elif base_url.endswith("/json"):
        url = base_url
    else:
        url = f"{base_url}/pypi/{package_name}/json"
    logger.debug("PyPI API 地址: %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "SD-WebUI-All-In-One"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))

    summary = ""
    info = payload.get("info")
    if isinstance(info, dict):
        summary = str(info.get("summary") or "")

    releases = payload.get("releases", {})
    if not isinstance(releases, dict):
        logger.warning("PyPI 返回的 releases 字段格式异常, 返回空版本列表: %s", package_name)
        return []

    versions: list[PackageVersionInfo] = []
    for version, files in releases.items():
        upload_time = ""
        if isinstance(files, list) and files:
            first_file = files[0]
            if isinstance(first_file, dict):
                upload_time = str(first_file.get("upload_time") or first_file.get("upload_time_iso_8601") or "")
        versions.append(
            PackageVersionInfo(
                version=str(version),
                upload_time=upload_time,
                summary=summary,
                is_current=version == current_version,
                is_prerelease=is_prerelease_version(str(version)),
            )
        )

    logger.info("获取软件包版本列表完成: %s, 共 %s 个版本", package_name, len(versions))
    return sorted(versions, key=lambda item: _pypi_version_sort_key(item.version), reverse=True)


def filter_extension_index(
    items: Iterable[ExtensionIndexItem],
    keyword: str,
    tags: Iterable[str] | None = None,
) -> list[ExtensionIndexItem]:
    """
    按关键字和标签过滤扩展源条目

    Args:
        items (Iterable[ExtensionIndexItem]):
            扩展源条目列表
        keyword (str):
            搜索关键字
        tags (Iterable[str] | None):
            标签过滤条件

    Returns:
        list[ExtensionIndexItem]: 过滤后的扩展源条目列表
    """
    keyword = keyword.strip().lower()
    selected_tags = {tag.lower() for tag in tags or []}
    logger.debug("过滤扩展源条目, 关键字: %s, 标签: %s", keyword, sorted(selected_tags))
    result: list[ExtensionIndexItem] = []
    for item in items:
        haystack = " ".join(
            [
                item.name,
                item.description,
                item.url,
                item.registry_id or "",
                item.registry_version or "",
                item.repository or "",
                item.author,
                " ".join(item.tags),
            ]
        ).lower()
        if keyword and keyword not in haystack:
            continue
        if selected_tags and not selected_tags.intersection({tag.lower() for tag in item.tags}):
            continue
        result.append(item)
    logger.debug("过滤扩展源条目完成, 共 %s 个条目", len(result))
    return result
