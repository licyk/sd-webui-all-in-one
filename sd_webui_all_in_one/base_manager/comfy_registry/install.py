"""Implementation grouped from the former ``comfy_registry.py`` module."""

from __future__ import annotations

import os
import shutil
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.downloader import download_file
from sd_webui_all_in_one.pkg_manager import install_requirements

from .client import fetch_comfy_registry_install_info, logger
from .models import ComfyRegistryInstallUnavailableError, ComfyRegistryNodeVersion


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
        ComfyRegistryInstallUnavailableError:
            Registry 节点没有可下载安装包时抛出。
        FileExistsError:
            目标节点已安装时抛出。
    """
    node_id = node_id.strip()
    if not node_id:
        raise ValueError("Comfy Registry 节点 ID 不能为空")
    info = fetch_comfy_registry_install_info(node_id, version=version)
    if not info.download_url:
        raise ComfyRegistryInstallUnavailableError(
            node_id=node_id,
            version=version,
            reason="Registry install 元数据缺少 downloadUrl",
        )

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
        ComfyRegistryInstallUnavailableError:
            Registry 节点没有可下载安装包时抛出。
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
        raise ComfyRegistryInstallUnavailableError(
            node_id=node_id,
            version=version,
            reason="Registry install 元数据缺少 downloadUrl",
        )

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
