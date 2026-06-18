"""WebUI 环境快照恢复工具"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, cast
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    clone_repo,
    install_pytorch_with_fallback,
)
from sd_webui_all_in_one.base_manager.snapshot import (
    DirectUrlSnapshot,
    ExtensionSnapshot,
    PackageSnapshot,
    RepositorySnapshot,
    WebUiSnapshot,
    collect_installed_packages,
    load_snapshot,
    repository_dirty,
)
from sd_webui_all_in_one.base_manager.version_manager import fetch_repository
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.env_manager import generate_uv_and_pip_env_mirror_config
from sd_webui_all_in_one.file_manager import is_folder_empty
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.mirror_manager import get_pypi_mirror_config
from sd_webui_all_in_one.package_analyzer import normalize_package_name
from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.pytorch_manager import PYTORCH_DEVICE_LIST, PyTorchDeviceType, get_pytorch_mirror
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

PYTORCH_PACKAGE_NAMES = {"torch", "torchvision", "torchaudio", "xformers"}
PROTECTED_PACKAGE_NAMES = {
    "sd-webui-all-in-one",
    "pip",
    "setuptools",
    "wheel",
    "uv",
}


@dataclass(slots=True)
class SnapshotRestoreOptions:
    """快照恢复选项"""

    prune_packages: bool = False
    prune_extensions: bool = False
    force_git_reset: bool = False
    use_uv: bool = True
    use_pypi_mirror: bool = True
    use_github_mirror: bool = False
    custom_github_mirror: str | list[str] | None = None


@dataclass(slots=True)
class ExtensionRestoreTools:
    """WebUI 扩展恢复工具"""

    directory_name: str
    set_status: Callable[[Path, str, bool], None]
    uninstall: Callable[[Path, str], None]
    strip_disabled_suffix: bool = False


def normalize_extension_name(
    name: str,
    strip_disabled_suffix: bool = False,
) -> str:
    """规范化扩展名用于快照对比"""
    normalized = name.casefold()
    if strip_disabled_suffix:
        normalized = normalized.removesuffix(".disabled")
    return normalized


def _normalized_package_name(name: str) -> str:
    return normalize_package_name(name)


def _is_protected_package(name: str) -> bool:
    return _normalized_package_name(name) in PROTECTED_PACKAGE_NAMES


def _package_version_spec(package: PackageSnapshot) -> str:
    return f"{package.name}=={package.version}"


def _local_path_from_url(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        path_text = url2pathname(unquote(parsed.path))
        if parsed.netloc:
            path_text = f"//{parsed.netloc}{path_text}"
        return Path(path_text)
    if parsed.scheme == "":
        return Path(url)
    return None


def _install_args_from_direct_url(package: PackageSnapshot) -> list[str] | None:
    direct_url = package.direct_url
    if direct_url is None or direct_url.url is None:
        return [_package_version_spec(package)]

    local_path = _local_path_from_url(direct_url.url)
    if local_path is not None:
        if not local_path.exists():
            logger.warning("本地包路径不存在, 跳过安装 '%s': %s", package.name, local_path)
            return None
        if package.editable:
            return ["-e", local_path.as_posix()]
        return [local_path.as_posix()]

    if direct_url.vcs_info is not None:
        vcs = direct_url.vcs_info.vcs or "git"
        url = direct_url.url
        vcs_url = url if url.startswith(f"{vcs}+") else f"{vcs}+{url}"
        revision = direct_url.vcs_info.commit_id or direct_url.vcs_info.requested_revision
        if revision:
            vcs_url = f"{vcs_url}@{revision}"
        if direct_url.subdirectory:
            vcs_url = f"{vcs_url}#subdirectory={direct_url.subdirectory}"
        return [f"{package.name} @ {vcs_url}"]

    if direct_url.archive_info is not None:
        return [f"{package.name} @ {direct_url.url}"]

    return [_package_version_spec(package)]


def _install_package(package: PackageSnapshot, custom_env: dict[str, str], use_uv: bool) -> None:
    args = _install_args_from_direct_url(package)
    if args is None:
        return
    logger.info("恢复 Python 包: %s", package.name)
    pip_install(*args, use_uv=use_uv, custom_env=custom_env)


def _infer_pytorch_device_type(packages: list[PackageSnapshot]) -> PyTorchDeviceType | None:
    for package in packages:
        if "+" not in package.version:
            continue
        suffix = package.version.split("+", 1)[1]
        if suffix in PYTORCH_DEVICE_LIST:
            return cast(PyTorchDeviceType, suffix)
    return None


def _pypi_env(use_pypi_mirror: bool) -> dict[str, str]:
    return get_pypi_mirror_config(use_cn_mirror=use_pypi_mirror)


def _pytorch_env(packages: list[PackageSnapshot], use_pypi_mirror: bool) -> dict[str, str]:
    dtype = _infer_pytorch_device_type(packages)
    if dtype is None:
        logger.info("未从 PyTorch 包版本推断出特殊源, 使用普通 PyPI 源安装")
        return _pypi_env(use_pypi_mirror=use_pypi_mirror)

    try:
        url, kind = get_pytorch_mirror(dtype=dtype, use_cn_mirror=use_pypi_mirror)
    except ValueError as e:
        logger.warning("未找到 PyTorch 特殊源 '%s': %s, 使用普通 PyPI 源安装", dtype, e)
        return _pypi_env(use_pypi_mirror=use_pypi_mirror)

    mirrors: dict[str, str | list[str] | None] = {
        "index_url": [],
        "extra_index_url": [],
        "find_links": [],
    }
    mirrors[kind] = url
    return generate_uv_and_pip_env_mirror_config(
        index_url=mirrors["index_url"],
        extra_index_url=mirrors["extra_index_url"],
        find_links=mirrors["find_links"],
    )


def _install_pytorch_packages(packages: list[PackageSnapshot], options: SnapshotRestoreOptions) -> None:
    if not packages:
        return

    torch_packages = [package for package in packages if _normalized_package_name(package.name) != "xformers"]
    xformers_packages = [package for package in packages if _normalized_package_name(package.name) == "xformers"]
    custom_env = _pytorch_env(packages, use_pypi_mirror=options.use_pypi_mirror)
    torch_package = [_package_version_spec(package) for package in torch_packages] or None
    xformers_package = [_package_version_spec(package) for package in xformers_packages] or None

    install_pytorch_with_fallback(
        torch_package=torch_package,
        xformers_package=xformers_package,
        custom_env=custom_env,
        use_uv=options.use_uv,
    )


def _current_package_map() -> dict[str, PackageSnapshot]:
    return {
        _normalized_package_name(package.name): package
        for package in collect_installed_packages()
    }


def _target_package_map(snapshot: WebUiSnapshot) -> dict[str, PackageSnapshot]:
    packages: dict[str, PackageSnapshot] = {}
    for package in snapshot.packages:
        normalized = _normalized_package_name(package.name)
        if normalized in PROTECTED_PACKAGE_NAMES:
            logger.info("跳过受保护 Python 包: %s", package.name)
            continue
        packages[normalized] = package
    return packages


def restore_python_packages(snapshot: WebUiSnapshot, options: SnapshotRestoreOptions) -> None:
    """恢复 Python 包"""
    target_packages = _target_package_map(snapshot)
    current_packages = _current_package_map()
    to_install = [
        package
        for normalized, package in target_packages.items()
        if normalized not in current_packages or current_packages[normalized].version != package.version
    ]

    pytorch_packages = [
        package
        for package in to_install
        if _normalized_package_name(package.name) in PYTORCH_PACKAGE_NAMES
    ]
    other_packages = [
        package
        for package in to_install
        if _normalized_package_name(package.name) not in PYTORCH_PACKAGE_NAMES
    ]

    _install_pytorch_packages(pytorch_packages, options)
    custom_env = _pypi_env(use_pypi_mirror=options.use_pypi_mirror)
    for package in other_packages:
        _install_package(package, custom_env=custom_env, use_uv=options.use_uv)

    if options.prune_packages:
        _prune_python_packages(target_packages=target_packages, current_packages=current_packages)


def _prune_python_packages(
    target_packages: dict[str, PackageSnapshot],
    current_packages: dict[str, PackageSnapshot],
) -> None:
    uninstall_names = [
        package.name
        for normalized, package in current_packages.items()
        if normalized not in target_packages and not _is_protected_package(package.name)
    ]
    if not uninstall_names:
        return

    logger.info("卸载快照外 Python 包: %s", ", ".join(uninstall_names))
    run_cmd([Path(sys.executable).as_posix(), "-m", "pip", "uninstall", *uninstall_names, "-y"])


def _extension_tools(webui_type: str) -> ExtensionRestoreTools | None:
    if webui_type == "sd_webui":
        from sd_webui_all_in_one.base_manager.sd_webui_base import set_sd_webui_extensions_status, uninstall_sd_webui_extension

        return ExtensionRestoreTools(
            directory_name="extensions",
            set_status=set_sd_webui_extensions_status,
            uninstall=uninstall_sd_webui_extension,
        )
    if webui_type == "comfyui":
        from sd_webui_all_in_one.base_manager.comfyui_base import set_comfyui_custom_node_status, uninstall_comfyui_custom_node

        return ExtensionRestoreTools(
            directory_name="custom_nodes",
            set_status=set_comfyui_custom_node_status,
            uninstall=uninstall_comfyui_custom_node,
            strip_disabled_suffix=True,
        )
    if webui_type == "invokeai":
        from sd_webui_all_in_one.base_manager.invokeai_base import set_invokeai_custom_nodes_status, uninstall_invokeai_custom_node

        return ExtensionRestoreTools(
            directory_name="nodes",
            set_status=set_invokeai_custom_nodes_status,
            uninstall=uninstall_invokeai_custom_node,
        )
    return None


def _ensure_git_target(repo: RepositorySnapshot | ExtensionSnapshot, target_path: Path) -> bool:
    if not repo.is_git_repo:
        logger.info("快照目标不是 Git 仓库, 跳过: %s", target_path)
        return False

    if target_path.exists() and not git_warpper.is_git_repo(target_path):
        if target_path.is_dir() and is_folder_empty(target_path) and repo.url:
            clone_repo(repo.url, target_path)
        else:
            logger.warning("目标路径已存在且不是 Git 仓库, 跳过: %s", target_path)
            return False
    elif not target_path.exists():
        if not repo.url:
            logger.warning("目标路径不存在且快照缺少远程地址, 跳过: %s", target_path)
            return False
        clone_repo(repo.url, target_path)

    if not git_warpper.is_git_repo(target_path):
        logger.warning("目标路径不是 Git 仓库, 跳过: %s", target_path)
        return False
    return True


def restore_git_repository(
    repo: RepositorySnapshot | ExtensionSnapshot,
    target_path: Path,
    options: SnapshotRestoreOptions,
) -> bool:
    """恢复 Git 仓库到快照提交"""
    if repo.commit is None:
        logger.info("快照目标缺少 commit, 跳过: %s", target_path)
        return target_path.is_dir()
    if not _ensure_git_target(repo, target_path):
        return False

    if repository_dirty(target_path, True) and not options.force_git_reset:
        raise RuntimeError(f"'{target_path}' 存在未提交变更, 请先处理或使用强制恢复")

    try:
        fetch_repository(target_path)
    except Exception as e:
        logger.warning("拉取 '%s' 远程引用失败, 将尝试使用本地提交恢复: %s", target_path, e)

    git_warpper.switch_commit(target_path, repo.commit)
    return True


def _extension_target_path(webui_path: Path, extension: ExtensionSnapshot, tools: ExtensionRestoreTools) -> Path:
    return webui_path / tools.directory_name / extension.name


def _target_extension_names(snapshot: WebUiSnapshot, tools: ExtensionRestoreTools) -> set[str]:
    return {
        normalize_extension_name(extension.name, strip_disabled_suffix=tools.strip_disabled_suffix)
        for extension in snapshot.extensions
        if extension.is_git_repo
    }


def _prune_extensions(webui_path: Path, snapshot: WebUiSnapshot, tools: ExtensionRestoreTools) -> None:
    extension_root = webui_path / tools.directory_name
    if not extension_root.is_dir():
        return

    target_names = _target_extension_names(snapshot, tools)
    for path in sorted(extension_root.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_dir() or path.name == "__pycache__":
            continue
        normalized = normalize_extension_name(path.name, strip_disabled_suffix=tools.strip_disabled_suffix)
        if normalized in target_names:
            continue
        logger.info("卸载快照外扩展: %s", path.name)
        tools.uninstall(webui_path, path.name)


def restore_extensions(snapshot: WebUiSnapshot, webui_path: Path, options: SnapshotRestoreOptions) -> None:
    """恢复 WebUI 扩展"""
    tools = _extension_tools(snapshot.webui.type)
    if tools is None:
        if snapshot.extensions:
            logger.warning("当前 WebUI 类型不支持扩展恢复: %s", snapshot.webui.type)
        return

    for extension in snapshot.extensions:
        target_path = _extension_target_path(webui_path, extension, tools)
        restored = restore_git_repository(
            repo=extension,
            target_path=target_path,
            options=options,
        )
        if restored and extension.enabled is not None:
            tools.set_status(webui_path, extension.name, extension.enabled)

    if options.prune_extensions:
        _prune_extensions(webui_path=webui_path, snapshot=snapshot, tools=tools)


def restore_webui_snapshot(
    snapshot_path: Path,
    webui_path: Path,
    expected_webui_type: str,
    options: SnapshotRestoreOptions | None = None,
) -> None:
    """从快照文件恢复 WebUI 环境"""
    if options is None:
        options = SnapshotRestoreOptions()

    snapshot = load_snapshot(snapshot_path)
    if snapshot.webui.type != expected_webui_type:
        raise ValueError(f"快照 WebUI 类型不匹配: 期望 '{expected_webui_type}', 实际 '{snapshot.webui.type}'")

    git_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=options.use_github_mirror,
        custom_github_mirror=options.custom_github_mirror,
        origin_env=os.environ.copy(),
    )
    old_git_config = os.environ.get("GIT_CONFIG_GLOBAL")
    git_config = git_env.get("GIT_CONFIG_GLOBAL")
    if git_config is not None:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config

    try:
        restore_python_packages(snapshot=snapshot, options=options)
        if snapshot.kernel is not None:
            restore_git_repository(repo=snapshot.kernel, target_path=webui_path, options=options)
        restore_extensions(snapshot=snapshot, webui_path=webui_path, options=options)
    finally:
        if old_git_config is None:
            os.environ.pop("GIT_CONFIG_GLOBAL", None)
        else:
            os.environ["GIT_CONFIG_GLOBAL"] = old_git_config
