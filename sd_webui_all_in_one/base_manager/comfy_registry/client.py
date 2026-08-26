"""Implementation grouped from the former ``comfy_registry.py`` module."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)

from sd_webui_all_in_one.base_manager.comfy_registry.models import (
    COMFY_REGISTRY_ACTIVE_VERSION_STATUSES,
    COMFY_REGISTRY_BASE_URL,
    COMFY_REGISTRY_CACHE_TTL_SECONDS,
    COMFY_REGISTRY_DEFAULT_PAGE_SIZE,
    ComfyRegistryInstallUnavailableError,
    ComfyRegistryNode,
    ComfyRegistryNodeVersion,
    ComfyRegistryProgressCallback,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

_COMFY_REGISTRY_NODE_CACHE: dict[tuple[str, int | None], tuple[float, tuple["ComfyRegistryNode", ...]]] = {}


def _api_url(path: str, query: dict[str, object] | None = None) -> str:
    url = f"{COMFY_REGISTRY_BASE_URL.rstrip('/')}/{path.lstrip('/')}"
    if query:
        encoded = urllib.parse.urlencode(query, doseq=True)
        if encoded:
            url = f"{url}?{encoded}"
    return url


def _fetch_json(url: str, timeout: int | None = 20) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "SD-WebUI-All-In-One"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_node_version(data: Any) -> ComfyRegistryNodeVersion | None:
    if not isinstance(data, dict):
        return None
    node_id = data.get("node_id") or data.get("nodeId") or data.get("id")
    version = data.get("version")
    if not isinstance(node_id, str) or not isinstance(version, str):
        return None
    dependencies = data.get("dependencies") or []
    return ComfyRegistryNodeVersion(
        node_id=node_id,
        version=version,
        download_url=str(data.get("downloadUrl") or data.get("download_url") or ""),
        dependencies=[str(item) for item in dependencies if isinstance(item, str)],
        status=str(data.get("status") or ""),
        created_at=str(data.get("createdAt") or data.get("created_at") or ""),
        raw=dict(data),
    )


def _repository_owner(repository: str) -> str:
    parsed = urllib.parse.urlparse(repository)
    path_parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc.endswith("github.com") and path_parts:
        return path_parts[0]
    return ""


def _parse_node_author(data: dict[str, Any]) -> str:
    raw_author = data.get("author")
    if isinstance(raw_author, str) and raw_author.strip():
        return raw_author.strip()

    publisher = data.get("publisher")
    if isinstance(publisher, dict):
        raw_publisher_name = publisher.get("name")
        if isinstance(raw_publisher_name, str):
            publisher_name = raw_publisher_name.strip()
            if publisher_name and publisher_name.casefold() != "unclaimed":
                return publisher_name

    raw_repository = data.get("repository")
    if isinstance(raw_repository, str) and raw_repository.strip():
        return _repository_owner(raw_repository.strip())
    return ""


def _parse_node(data: Any) -> ComfyRegistryNode | None:
    if not isinstance(data, dict):
        return None
    node_id = data.get("id")
    name = data.get("name") or node_id
    if not isinstance(node_id, str) or not isinstance(name, str):
        return None
    tags = data.get("tags") or []
    latest_version = _parse_node_version(data.get("latest_version") or data.get("latestVersion"))
    return ComfyRegistryNode(
        id=node_id,
        name=name,
        author=_parse_node_author(data),
        description=str(data.get("description") or ""),
        repository=str(data.get("repository") or ""),
        tags=tuple(str(item) for item in tags if isinstance(item, str)),
        latest_version=latest_version,
        raw=dict(data),
    )


def _parse_total(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None
    total = payload.get("total")
    if isinstance(total, int):
        return total
    if isinstance(total, str) and total.isdecimal():
        return int(total)
    return None


def _fetch_comfy_registry_node_page(
    search: str | None = None,
    page: int = 1,
    limit: int = COMFY_REGISTRY_DEFAULT_PAGE_SIZE,
    timeout: int | None = 20,
) -> tuple[list[ComfyRegistryNode], int | None]:
    query: dict[str, object] = {"page": page, "limit": limit}
    if search:
        query["search"] = search
    payload = _fetch_json(_api_url("/nodes", query), timeout=timeout)
    raw_nodes = payload.get("nodes") if isinstance(payload, dict) else payload
    if not isinstance(raw_nodes, list):
        return [], _parse_total(payload)
    return [node for raw_node in raw_nodes if (node := _parse_node(raw_node)) is not None], _parse_total(payload)


def clear_comfy_registry_cache() -> None:
    """清空 Comfy Registry 节点内存缓存。"""
    _COMFY_REGISTRY_NODE_CACHE.clear()


def fetch_comfy_registry_nodes(
    search: str | None = None,
    page: int = 1,
    limit: int = 200,
    timeout: int | None = 20,
) -> list[ComfyRegistryNode]:
    """获取 Comfy Registry 节点列表。

    Args:
        search (str | None):
            搜索关键字，未指定时返回默认列表。
        page (int):
            Registry 分页页码。
        limit (int):
            单页节点数量。
        timeout (int | None):
            请求超时时间。

    Returns:
        list[ComfyRegistryNode]:
            Registry 节点列表。
    """
    nodes, _total = _fetch_comfy_registry_node_page(search=search, page=page, limit=limit, timeout=timeout)
    return nodes


def fetch_all_comfy_registry_nodes(
    search: str | None = None,
    page_size: int = COMFY_REGISTRY_DEFAULT_PAGE_SIZE,
    max_items: int | None = None,
    timeout: int | None = 20,
    cache_ttl_seconds: int = COMFY_REGISTRY_CACHE_TTL_SECONDS,
    force_refresh: bool = False,
    progress_callback: ComfyRegistryProgressCallback | None = None,
) -> list[ComfyRegistryNode]:
    """分页读取全部 Registry 节点并使用内存缓存。

    Args:
        search (str | None):
            搜索关键字，传给 Registry API。当前 Registry API 可能忽略该参数。
        page_size (int):
            单页节点数量。
        max_items (int | None):
            最多返回节点数量，未指定时读取 API 返回的全部节点。
        timeout (int | None):
            单次请求超时时间。
        cache_ttl_seconds (int):
            内存缓存有效期，单位为秒。
        force_refresh (bool):
            是否忽略缓存并重新请求 Registry。
        progress_callback (ComfyRegistryProgressCallback | None):
            每页读取后调用，参数为已加载数量和 Registry 返回的总量。

    Returns:
        list[ComfyRegistryNode]:
            Registry 节点列表。
    """
    if max_items is not None and max_items <= 0:
        return []
    page_size = max(1, page_size)
    if max_items is not None:
        page_size = min(page_size, max_items)
    cache_key = ((search or "").strip(), max_items)
    now = time.monotonic()
    cached = _COMFY_REGISTRY_NODE_CACHE.get(cache_key)
    if not force_refresh and cached is not None and now - cached[0] <= cache_ttl_seconds:
        return list(cached[1])

    result: list[ComfyRegistryNode] = []
    seen_ids: set[str] = set()
    fetched_count = 0
    total: int | None = None
    page = 1
    while True:
        page_nodes, total = _fetch_comfy_registry_node_page(search=search, page=page, limit=page_size, timeout=timeout)
        if not page_nodes:
            break
        fetched_count += len(page_nodes)
        for node in page_nodes:
            if node.id in seen_ids:
                continue
            seen_ids.add(node.id)
            result.append(node)
            if max_items is not None and len(result) >= max_items:
                break
        if progress_callback is not None:
            progress_callback(len(result), total)
        if max_items is not None and len(result) >= max_items:
            break
        if total is not None and fetched_count >= total:
            break
        if len(page_nodes) < page_size:
            break
        page += 1

    _COMFY_REGISTRY_NODE_CACHE[cache_key] = (time.monotonic(), tuple(result))
    return list(result)


def fetch_comfy_registry_versions(
    node_id: str,
    timeout: int | None = 20,
) -> list[ComfyRegistryNodeVersion]:
    """获取 Registry 节点可安装版本。

    Args:
        node_id (str):
            Comfy Registry 节点 ID。
        timeout (int | None):
            请求超时时间。

    Returns:
        list[ComfyRegistryNodeVersion]:
            可安装版本列表。
    """
    payload = _fetch_json(
        _api_url(
            f"/nodes/{urllib.parse.quote(node_id, safe='')}/versions",
            {"statuses": list(COMFY_REGISTRY_ACTIVE_VERSION_STATUSES)},
        ),
        timeout=timeout,
    )
    if not isinstance(payload, list):
        return []
    return [version for raw_version in payload if (version := _parse_node_version(raw_version)) is not None]


def fetch_comfy_registry_install_info(
    node_id: str,
    version: str | None = None,
    timeout: int | None = 20,
) -> ComfyRegistryNodeVersion:
    """获取 Registry 节点安装元数据。

    Args:
        node_id (str):
            Comfy Registry 节点 ID。
        version (str | None):
            指定安装版本，未指定时由 Registry 返回默认版本。
        timeout (int | None):
            请求超时时间。

    Returns:
        ComfyRegistryNodeVersion:
            节点安装版本信息。

    Raises:
        ComfyRegistryInstallUnavailableError:
            Registry install 接口返回 404 时抛出。
        urllib.error.HTTPError:
            Registry install 接口返回其他 HTTP 错误时抛出。
        ValueError:
            Registry 返回内容无法解析为安装版本信息时抛出。
    """
    query: dict[str, object] | None = {"version": version} if version else None
    try:
        payload = _fetch_json(_api_url(f"/nodes/{urllib.parse.quote(node_id, safe='')}/install", query), timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ComfyRegistryInstallUnavailableError(
                node_id=node_id,
                version=version,
                reason="请求 install 返回 404",
                http_status=e.code,
            ) from e
        raise
    info = _parse_node_version(payload)
    if info is None:
        raise ValueError(f"Comfy Registry 未返回有效安装信息: {node_id}@{version or 'latest'}")
    return info
