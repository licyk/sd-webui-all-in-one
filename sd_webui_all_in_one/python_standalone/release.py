"""python-build-standalone Release 信息获取与构建文件挑选"""

import json
import re
import time
import urllib.request
from dataclasses import replace
from typing import Any

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.python_standalone.types import (
    DEFAULT_GITHUB_API_URL,
    DEFAULT_SOURCE_REPO,
    PythonAsset,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

ASSET_NAME_PATTERN = re.compile(r"^(?P<implementation>[^-]+)-(?P<version>[^-+]+)\+(?P<build_date>\d{8})-(?P<build_type>.+?)\.(?P<ext>tar\..+)$")
"""python-build-standalone 构建文件名的正则表达式"""

GITHUB_REQUEST_TRIES = 3
"""请求 GitHub 的最大尝试次数"""


def github_get(
    url: str,
    token: str | None = None,
    accept: str = "application/vnd.github+json",
) -> bytes:
    """请求 GitHub, 失败时重试

    Args:
        url (str): 请求地址
        token (str | None): GitHub Token, 用于避免 API 速率限制
        accept (str): Accept 请求头
    Returns:
        bytes: 响应内容
    Raises:
        RuntimeError: 多次请求失败时
    """
    headers = {"Accept": accept, "User-Agent": "sd-webui-all-in-one"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_error: Exception | None = None
    for attempt in range(1, GITHUB_REQUEST_TRIES + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                return response.read()
        except Exception as e:
            last_error = e
            logger.warning("请求 %s 失败 (%s/%s): %s", url, attempt, GITHUB_REQUEST_TRIES, e)
            if attempt < GITHUB_REQUEST_TRIES:
                time.sleep(attempt * 2)
    raise RuntimeError(f"请求 {url} 失败: {last_error}") from last_error


def parse_asset_name(
    name: str,
    url: str = "",
    size: int | None = None,
    sha256: str | None = None,
) -> PythonAsset | None:
    """解析 python-build-standalone 构建文件名

    Args:
        name (str): 文件名, 如 cpython-3.12.8+20250106-x86_64-unknown-linux-gnu-install_only.tar.gz
        url (str): 下载链接
        size (int | None): 文件大小
        sha256 (str | None): 文件 SHA256
    Returns:
        (PythonAsset | None): 解析结果, 不是 CPython 构建文件时返回 None
    """
    match = ASSET_NAME_PATTERN.match(name)
    if match is None or match.group("implementation") != "cpython":
        return None
    return PythonAsset(
        name=name,
        url=url,
        version=match.group("version"),
        build_date=match.group("build_date"),
        build_type=match.group("build_type"),
        size=size,
        sha256=sha256,
    )


def list_releases(
    source_repo: str = DEFAULT_SOURCE_REPO,
    limit: int = 10,
    token: str | None = None,
    api_url: str = DEFAULT_GITHUB_API_URL,
) -> list[dict[str, Any]]:
    """获取 python-build-standalone 最近的 Release 列表

    Args:
        source_repo (str): 发布仓库
        limit (int): 最多返回的 Release 数量 (1 ~ 100)
        token (str | None): GitHub Token
        api_url (str): GitHub API 地址
    Returns:
        list[dict[str, Any]]: Release 信息列表, 包含 tag, name, published_at, prerelease, assets, url
    """
    url = f"{api_url.rstrip('/')}/repos/{source_repo}/releases?per_page={max(1, min(limit, 100))}"
    releases = json.loads(github_get(url, token))
    return [
        {
            "tag": release.get("tag_name"),
            "name": release.get("name"),
            "published_at": release.get("published_at"),
            "prerelease": release.get("prerelease", False),
            "assets": len(release.get("assets", [])),
            "url": release.get("html_url"),
        }
        for release in releases[:limit]
    ]


def fetch_release_assets(
    release_tag: str = "latest",
    source_repo: str = DEFAULT_SOURCE_REPO,
    token: str | None = None,
    api_url: str = DEFAULT_GITHUB_API_URL,
) -> tuple[str, list[PythonAsset]]:
    """获取 python-build-standalone Release 中的 CPython 构建文件列表

    优先使用 GitHub API 提供的 digest 作为 SHA256, 缺失时读取 Release 中的 SHA256SUMS

    Args:
        release_tag (str): Release 标签, latest 表示最新版本
        source_repo (str): 发布仓库
        token (str | None): GitHub Token
        api_url (str): GitHub API 地址
    Returns:
        tuple[str, list[PythonAsset]]: 实际的 Release 标签和构建文件列表
    """
    base = f"{api_url.rstrip('/')}/repos/{source_repo}/releases"
    url = f"{base}/latest" if release_tag == "latest" else f"{base}/tags/{release_tag}"
    logger.info("获取 %s 的 Release 信息: %s", source_repo, url)
    release = json.loads(github_get(url, token))
    raw_assets: list[dict[str, Any]] = release.get("assets", [])

    sha256sums: dict[str, str] | None = None
    assets: list[PythonAsset] = []
    for info in raw_assets:
        digest = info.get("digest") or ""
        sha256 = digest.removeprefix("sha256:") if digest.startswith("sha256:") else None
        asset = parse_asset_name(info["name"], info["browser_download_url"], info.get("size"), sha256)
        if asset is None:
            continue
        if asset.sha256 is None:
            if sha256sums is None:
                sha256sums = _fetch_sha256sums(raw_assets, token)
            asset = replace(asset, sha256=sha256sums.get(asset.name))
        assets.append(asset)

    tag = release.get("tag_name") or release_tag
    logger.info("Release %s 中共有 %s 个 CPython 构建文件", tag, len(assets))
    return tag, assets


def _fetch_sha256sums(
    raw_assets: list[dict[str, Any]],
    token: str | None,
) -> dict[str, str]:
    """读取 Release 中的 SHA256SUMS 文件

    Args:
        raw_assets (list[dict[str, Any]]): GitHub API 返回的 Release 文件列表
        token (str | None): GitHub Token
    Returns:
        dict[str, str]: 文件名到 SHA256 的映射, 没有 SHA256SUMS 时为空
    """
    for info in raw_assets:
        if info["name"] != "SHA256SUMS":
            continue
        text = github_get(info["browser_download_url"], token, accept="application/octet-stream").decode("utf-8")
        return parse_sha256sums(text)
    logger.warning("Release 中没有 SHA256SUMS, 将跳过下载文件校验")
    return {}


def parse_sha256sums(
    text: str,
) -> dict[str, str]:
    """解析 SHA256SUMS 文件内容

    Args:
        text (str): SHA256SUMS 文件内容, 每行为 <sha256> <文件名>
    Returns:
        dict[str, str]: 文件名到 SHA256 的映射
    """
    result: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2:
            result[parts[1].lstrip("*")] = parts[0].lower()
    return result


def select_assets(
    assets: list[PythonAsset],
    versions: list[str],
    platforms: dict[str, str],
    variant: str,
) -> list[tuple[str, PythonAsset]]:
    """按版本和平台挑选构建文件, 每个组合取补丁版本最高的一个

    Args:
        assets (list[PythonAsset]): 构建文件列表
        versions (list[str]): 主次版本号列表, 如 ["3.11", "3.12"]
        platforms (dict[str, str]): 平台到构建目标三元组的映射, 如 {"linux/amd64": "x86_64-unknown-linux-gnu"}
        variant (str): 构建变体, 如 install_only
    Returns:
        list[tuple[str, PythonAsset]]: (平台, 构建文件) 列表
    """
    selected: list[tuple[str, PythonAsset]] = []
    for platform, triple in platforms.items():
        build_type = f"{triple}-{variant}"
        for minor in versions:
            candidates = [a for a in assets if a.minor == minor and a.build_type == build_type]
            if not candidates:
                logger.warning("Release 中没有 Python %s (%s) 的构建, 跳过", minor, build_type)
                continue
            selected.append((platform, max(candidates, key=lambda a: a.version_tuple)))
    return selected
