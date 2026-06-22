"""Comfy Registry / CNR 集成工具。"""

from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    from sd_webui_all_in_one import toml_parser as tomllib

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.downloader import download_file
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)

if TYPE_CHECKING:
    from sd_webui_all_in_one.base_manager.version_manager import ExtensionIndexItem


COMFY_REGISTRY_BASE_URL = "https://api.comfy.org"
"""Comfy Registry API 基础地址。"""

COMFY_REGISTRY_ACTIVE_VERSION_STATUSES = ("NodeVersionStatusActive", "NodeVersionStatusPending")
"""ComfyUI-Manager 视为可安装的 Registry 版本状态。"""

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


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
        description=str(data.get("description") or ""),
        repository=str(data.get("repository") or ""),
        tags=tuple(str(item) for item in tags if isinstance(item, str)),
        latest_version=latest_version,
        raw=dict(data),
    )


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
    query: dict[str, object] = {"page": page, "limit": limit}
    if search:
        query["search"] = search
    payload = _fetch_json(_api_url("/nodes", query), timeout=timeout)
    raw_nodes = payload.get("nodes") if isinstance(payload, dict) else payload
    if not isinstance(raw_nodes, list):
        return []
    return [node for raw_node in raw_nodes if (node := _parse_node(raw_node)) is not None]


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
        ValueError:
            Registry 返回内容无法解析为安装版本信息时抛出。
    """
    query: dict[str, object] | None = {"version": version} if version else None
    payload = _fetch_json(_api_url(f"/nodes/{urllib.parse.quote(node_id, safe='')}/install", query), timeout=timeout)
    info = _parse_node_version(payload)
    if info is None:
        raise ValueError(f"Comfy Registry 未返回有效安装信息: {node_id}@{version or 'latest'}")
    return info


def read_comfy_registry_info(path: Path) -> ComfyRegistryLocalInfo | None:
    """读取本地 Registry 节点元数据。

    Args:
        path (Path):
            自定义节点目录。

    Returns:
        ComfyRegistryLocalInfo | None:
            本地 Registry 节点信息；不是有效 Registry 节点时返回 None。
    """
    pyproject_path = path / "pyproject.toml"
    tracking_path = path / ".tracking"
    if not pyproject_path.is_file() or not tracking_path.is_file():
        return None
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data.get("project", {})
        if not isinstance(project, dict):
            return None
        raw_name = project.get("name")
        raw_version = project.get("version")
        if not isinstance(raw_name, str) or not raw_name.strip() or raw_version is None:
            return None
        urls = project.get("urls", {})
        repository = urls.get("Repository") if isinstance(urls, dict) else None
        return ComfyRegistryLocalInfo(
            registry_id=raw_name.strip().lower(),
            original_name=raw_name.strip(),
            version=str(raw_version),
            repository=repository if isinstance(repository, str) and repository.strip() else None,
        )
    except Exception:
        return None


def read_comfy_registry_nightly_id(path: Path) -> str | None:
    """读取 Git nightly 节点的 Registry ID 标记。

    Args:
        path (Path):
            Git 自定义节点目录。

    Returns:
        str | None:
            `.git/.cnr-id` 中记录的 Registry ID，不存在时返回 None。
    """
    marker = path / ".git" / ".cnr-id"
    if not marker.is_file():
        return None
    value = marker.read_text(encoding="utf-8").strip()
    return value or None


def _safe_zip_members(archive_path: Path) -> list[zipfile.ZipInfo]:
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        members = zip_ref.infolist()
    safe_members: list[zipfile.ZipInfo] = []
    for member in members:
        target = Path(member.filename)
        if target.is_absolute() or ".." in target.parts:
            raise ValueError(f"Registry 压缩包包含不安全路径: {member.filename}")
        safe_members.append(member)
    return safe_members


def _extract_registry_zip(archive_path: Path, target_path: Path) -> list[str]:
    target_path.mkdir(parents=True, exist_ok=True)
    members = _safe_zip_members(archive_path)
    extracted: list[str] = []
    with zipfile.ZipFile(archive_path, "r") as zip_ref:
        for member in members:
            relative_name = member.filename.rstrip("/")
            if not relative_name:
                continue
            target = target_path / relative_name
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zip_ref.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            extracted.append(relative_name)
    (target_path / ".tracking").write_text("\n".join(extracted), encoding="utf-8")
    return extracted


def _run_postinstall(path: Path, node_id: str, use_uv: bool, custom_env: dict[str, str] | None) -> None:
    requirements_path = path / "requirements.txt"
    if requirements_path.is_file():
        install_requirements(requirements_path, use_uv=use_uv, custom_env=custom_env, cwd=path)
    install_script = path / "install.py"
    if install_script.is_file():
        logger.info("执行 Comfy Registry 节点安装脚本: %s", node_id)
        run_cmd([Path(sys.executable).as_posix(), install_script.as_posix()], custom_env=custom_env, cwd=path)


def install_comfy_registry_node(
    comfyui_path: Path,
    node_id: str,
    version: str | None = None,
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
    run_postinstall: bool = True,
) -> ComfyRegistryNodeVersion:
    """安装 Comfy Registry 节点。

    Args:
        comfyui_path (Path):
            ComfyUI 根目录。
        node_id (str):
            Comfy Registry 节点 ID。
        version (str | None):
            指定安装版本，未指定时安装 Registry 默认版本。
        use_uv (bool):
            是否使用 uv 安装 Python 依赖。
        custom_env (dict[str, str] | None):
            自定义安装环境变量。
        run_postinstall (bool):
            是否执行节点内 requirements.txt 和 install.py。

    Returns:
        ComfyRegistryNodeVersion:
            已安装的 Registry 版本信息。

    Raises:
        ValueError:
            节点 ID 为空或 Registry 节点不可安装时抛出。
        FileExistsError:
            目标节点已安装时抛出。
    """
    node_id = node_id.strip()
    if not node_id:
        raise ValueError("Comfy Registry 节点 ID 不能为空")
    info = fetch_comfy_registry_install_info(node_id, version=version)
    if not info.download_url:
        raise ValueError(f"Comfy Registry 节点不可安装: {node_id}@{version or 'latest'}")

    custom_nodes_path = comfyui_path / "custom_nodes"
    install_path = custom_nodes_path / node_id
    disabled_path = custom_nodes_path / ".disabled" / node_id
    if install_path.exists() or disabled_path.exists():
        raise FileExistsError(f"'{node_id}' Registry 节点已安装")

    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        archive_path = download_file(url=info.download_url, path=tmp_path, save_name=f"{node_id}.zip", progress=False)
        staging_path = tmp_path / node_id
        _extract_registry_zip(archive_path, staging_path)
        custom_nodes_path.mkdir(parents=True, exist_ok=True)
        shutil.move(staging_path.as_posix(), install_path.as_posix())

    if run_postinstall:
        _run_postinstall(install_path, node_id, use_uv=use_uv, custom_env=custom_env)
    return info


def _read_tracking(path: Path) -> list[str]:
    tracking_path = path / ".tracking"
    if not tracking_path.is_file():
        return []
    return [line.strip() for line in tracking_path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _cleanup_tracked_files(path: Path) -> None:
    for relative_name in _read_tracking(path):
        target = path / relative_name
        try:
            if target.is_file() or target.is_symlink():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
        except FileNotFoundError:
            continue
    for root, dirs, _files in os.walk(path, topdown=False):
        for dirname in dirs:
            directory = Path(root) / dirname
            try:
                directory.rmdir()
            except OSError:
                pass


def _copy_tree_contents(source: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            if destination.exists():
                _copy_tree_contents(item, destination)
            else:
                shutil.copytree(item, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def switch_comfy_registry_node_version(
    comfyui_path: Path,
    node_id: str,
    version: str | None,
    target_path: Path | None = None,
    use_uv: bool = True,
    custom_env: dict[str, str] | None = None,
    run_postinstall: bool = True,
) -> ComfyRegistryNodeVersion:
    """安装或切换 Comfy Registry 节点版本。

    Args:
        comfyui_path (Path):
            ComfyUI 根目录。
        node_id (str):
            Comfy Registry 节点 ID。
        version (str | None):
            目标版本，未指定时切换到 Registry 默认版本。
        target_path (Path | None):
            已安装节点路径，未指定时使用 `custom_nodes/<node_id>`。
        use_uv (bool):
            是否使用 uv 安装 Python 依赖。
        custom_env (dict[str, str] | None):
            自定义安装环境变量。
        run_postinstall (bool):
            是否执行节点内 requirements.txt 和 install.py。

    Returns:
        ComfyRegistryNodeVersion:
            已安装或切换到的 Registry 版本信息。

    Raises:
        ValueError:
            节点 ID 为空或 Registry 节点不可安装时抛出。
    """
    node_id = node_id.strip()
    if not node_id:
        raise ValueError("Comfy Registry 节点 ID 不能为空")
    if target_path is None:
        target_path = comfyui_path / "custom_nodes" / node_id
    if not target_path.exists():
        return install_comfy_registry_node(
            comfyui_path=comfyui_path,
            node_id=node_id,
            version=version,
            use_uv=use_uv,
            custom_env=custom_env,
            run_postinstall=run_postinstall,
        )

    info = fetch_comfy_registry_install_info(node_id, version=version)
    if not info.download_url:
        raise ValueError(f"Comfy Registry 节点不可安装: {node_id}@{version or 'latest'}")

    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        archive_path = download_file(url=info.download_url, path=tmp_path, save_name=f"{node_id}.zip", progress=False)
        staging_path = tmp_path / node_id
        _extract_registry_zip(archive_path, staging_path)
        _cleanup_tracked_files(target_path)
        _copy_tree_contents(staging_path, target_path)

    if run_postinstall:
        _run_postinstall(target_path, node_id, use_uv=use_uv, custom_env=custom_env)
    return info


def fetch_comfy_registry_extension_index(search: str | None = None, limit: int = 200) -> list[ExtensionIndexItem]:
    """获取 Registry 节点并转换为扩展源条目。

    Args:
        search (str | None):
            搜索关键字，未指定时返回默认列表。
        limit (int):
            请求节点数量。

    Returns:
        list[ExtensionIndexItem]:
            `ExtensionIndexItem` 列表。
    """
    from sd_webui_all_in_one.base_manager.version_manager import ExtensionIndexItem

    items: list[ExtensionIndexItem] = []
    for node in fetch_comfy_registry_nodes(search=search, limit=limit):
        version = node.latest_version.version if node.latest_version else ""
        download_url = node.latest_version.download_url if node.latest_version else ""
        dependencies = tuple(node.latest_version.dependencies) if node.latest_version else ()
        items.append(
            ExtensionIndexItem(
                name=node.name,
                url=node.repository or download_url or node.id,
                description=node.description,
                tags=(*node.tags, "Comfy Registry"),
                install_type="comfy-registry",
                files=(),
                reference=node.repository,
                source_type="comfy-registry",
                registry_id=node.id,
                registry_version=version,
                repository=node.repository,
                download_url=download_url,
                dependencies=dependencies,
            )
        )
    return items
