"""WebUI 环境快照恢复工具"""

from __future__ import annotations

import os
import json
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, cast
from urllib.parse import unquote, urlparse

from sd_webui_all_in_one import git_warpper
import sd_webui_all_in_one.base_manager.comfy_registry as comfy_registry
import sd_webui_all_in_one.base_manager.comfyui_base as comfyui_base
import sd_webui_all_in_one.base_manager.invokeai_base as invokeai_base
import sd_webui_all_in_one.base_manager.sd_webui_base as sd_webui_base
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    clone_repo,
    install_pytorch_with_fallback,
)
from sd_webui_all_in_one.base_manager.snapshot import (
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
    "wheel",
    "uv",
}
PACKAGE_KERNEL_WEBUI_TYPES = {"invokeai"}

PackageRestoreAction = Literal[
    "install",
    "update",
    "skip_same_version",
    "skip_protected",
    "skip_missing_local_path",
    "uninstall",
    "install_pytorch_special",
]
GitRestoreAction = Literal[
    "clone",
    "switch_commit",
    "skip_same_commit",
    "skip_non_git_snapshot",
    "skip_non_git_target",
    "skip_missing_url",
    "skip_missing_commit",
    "blocked_dirty",
    "blocked_missing_target",
]
RegistryRestoreAction = Literal[
    "install_registry",
    "switch_registry_version",
    "skip_same_registry_version",
    "skip_registry_missing_id",
    "skip_registry_unavailable",
]
ExtensionCleanupAction = Literal["keep", "uninstall"]


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


@dataclass(slots=True)
class PackageRestorePlanItem:
    """Python 包恢复预检查项"""

    name: str
    normalized_name: str
    action: PackageRestoreAction
    reason: str
    target_version: str | None = None
    current_version: str | None = None
    source_type: str | None = None
    editable: bool = False
    local_path: Path | None = None
    pytorch_device_type: str | None = None


@dataclass(slots=True)
class GitRestorePlanItem:
    """Git 仓库恢复预检查项"""

    name: str
    path: Path
    action: GitRestoreAction
    reason: str
    target_commit: str | None = None
    current_commit: str | None = None
    dirty: bool | None = None
    url: str | None = None


@dataclass(slots=True)
class ExtensionRestorePlanItem:
    """WebUI 扩展恢复预检查项"""

    name: str
    normalized_name: str
    path: Path
    git: GitRestorePlanItem | None = None
    registry_action: RegistryRestoreAction | None = None
    cleanup_action: ExtensionCleanupAction = "keep"
    current_enabled: bool | None = None
    target_enabled: bool | None = None
    source_type: str | None = None
    registry_id: str | None = None
    current_version: str | None = None
    target_version: str | None = None
    reason: str = ""


@dataclass(slots=True)
class SnapshotRestorePlan:
    """WebUI 快照恢复预检查结果"""

    webui_type_match: bool
    expected_webui_type: str
    snapshot_webui_type: str
    snapshot_webui_name: str
    snapshot_path: Path
    webui_path: Path
    python_version_note: str | None = None
    package_changes: list[PackageRestorePlanItem] = field(default_factory=list)
    kernel_change: GitRestorePlanItem | None = None
    extension_changes: list[ExtensionRestorePlanItem] = field(default_factory=list)
    pytorch_device_type: str | None = None
    pytorch_mirror_url: str | None = None
    pytorch_mirror_kind: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def normalize_extension_name(
    name: str,
    strip_disabled_suffix: bool = False,
) -> str:
    """规范化扩展名用于快照对比

    Args:
        name (str):
            待规范化的名称。
        strip_disabled_suffix (bool):
            是否移除禁用扩展使用的后缀。

    Returns:
        str: 规范化后的扩展名。
    """
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


def _normalize_file_url_path(path: str) -> str:
    path_text = unquote(path)
    if len(path_text) >= 3 and path_text[0] == "/" and path_text[1].isalpha() and path_text[2] in {":", "|"}:
        path_text = path_text[1:]
    if len(path_text) >= 2 and path_text[0].isalpha() and path_text[1] == "|":
        path_text = f"{path_text[0]}:{path_text[2:]}"
    return path_text


def _local_path_from_url(url: str) -> Path | None:
    parsed = urlparse(url)
    if parsed.scheme == "file":
        path_text = _normalize_file_url_path(parsed.path)
        if parsed.netloc and parsed.netloc.lower() != "localhost":
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


def _local_path_from_package(package: PackageSnapshot) -> Path | None:
    direct_url = package.direct_url
    if direct_url is None or direct_url.url is None:
        return None
    return _local_path_from_url(direct_url.url)


def _install_packages(packages: list[PackageSnapshot], custom_env: dict[str, str], use_uv: bool) -> None:
    install_args: list[str] = []
    package_names: list[str] = []
    for package in packages:
        args = _install_args_from_direct_url(package)
        if args is None:
            continue
        install_args.extend(args)
        package_names.append(package.name)

    if not install_args:
        return

    logger.info("恢复 Python 包: %s", ", ".join(package_names))
    pip_install(*install_args, "--no-deps", use_uv=use_uv, custom_env=custom_env)


def _is_windows_platform(platform_tag: str) -> bool:
    return platform_tag.casefold().startswith("win")


def _normalize_pytorch_version_suffix(
    suffix: str,
    platform_tag: str | None = None,
) -> PyTorchDeviceType | None:
    platform_tag = sys.platform if platform_tag is None else platform_tag
    normalized_suffix = suffix.strip().casefold()

    if normalized_suffix == "rocm_win":
        return "rocm_win"
    if _is_windows_platform(platform_tag) and normalized_suffix.startswith("rocm"):
        return "rocm_win"
    if normalized_suffix in PYTORCH_DEVICE_LIST:
        return cast(PyTorchDeviceType, normalized_suffix)
    return None


def _infer_pytorch_device_type(
    packages: list[PackageSnapshot],
    platform_tag: str | None = None,
) -> PyTorchDeviceType | None:
    for package in packages:
        if "+" not in package.version:
            continue
        suffix = package.version.split("+", 1)[1]
        dtype = _normalize_pytorch_version_suffix(suffix, platform_tag=platform_tag)
        if dtype is not None:
            return dtype
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


def _pytorch_mirror_plan(
    packages: list[PackageSnapshot],
    use_pypi_mirror: bool,
) -> tuple[str | None, str | None, str | None, str | None]:
    dtype = _infer_pytorch_device_type(packages)
    if dtype is None:
        return None, None, None, "未从 PyTorch 包版本推断出特殊源, 将使用普通 PyPI 源"

    try:
        url, kind = get_pytorch_mirror(dtype=dtype, use_cn_mirror=use_pypi_mirror)
    except ValueError as e:
        return dtype, None, None, f"未找到 PyTorch 特殊源 '{dtype}', 将使用普通 PyPI 源: {e}"
    return dtype, url, kind, None


def _install_pytorch_packages(packages: list[PackageSnapshot], options: SnapshotRestoreOptions) -> None:
    if not packages:
        return

    torch_packages = [package for package in packages if _normalized_package_name(package.name) != "xformers"]
    xformers_packages = [package for package in packages if _normalized_package_name(package.name) == "xformers"]
    custom_env = _pytorch_env(packages, use_pypi_mirror=options.use_pypi_mirror)
    torch_package = [*[_package_version_spec(package) for package in torch_packages], "--no-deps"] if torch_packages else None
    xformers_package = [*[_package_version_spec(package) for package in xformers_packages], "--no-deps"] if xformers_packages else None

    install_pytorch_with_fallback(
        torch_package=torch_package,
        xformers_package=xformers_package,
        custom_env=custom_env,
        use_uv=options.use_uv,
    )


def _current_package_map() -> dict[str, PackageSnapshot]:
    return {_normalized_package_name(package.name): package for package in collect_installed_packages()}


def _target_package_map(snapshot: WebUiSnapshot) -> dict[str, PackageSnapshot]:
    packages: dict[str, PackageSnapshot] = {}
    for package in snapshot.packages:
        normalized = _normalized_package_name(package.name)
        if normalized in PROTECTED_PACKAGE_NAMES:
            logger.info("跳过受保护 Python 包: %s", package.name)
            continue
        packages[normalized] = package
    return packages


def _build_package_restore_plan(
    snapshot: WebUiSnapshot,
    options: SnapshotRestoreOptions,
    warnings: list[str],
) -> tuple[list[PackageRestorePlanItem], str | None, str | None, str | None]:
    target_packages: dict[str, PackageSnapshot] = {}
    current_packages = _current_package_map()
    items: list[PackageRestorePlanItem] = []
    pytorch_to_install: list[PackageSnapshot] = []

    for package in snapshot.packages:
        normalized = _normalized_package_name(package.name)
        current = current_packages.get(normalized)
        local_path = _local_path_from_package(package)

        def make_item(action: PackageRestoreAction, reason: str) -> PackageRestorePlanItem:
            return PackageRestorePlanItem(
                name=package.name,
                normalized_name=normalized,
                action=action,
                reason=reason,
                target_version=package.version,
                current_version=current.version if current is not None else None,
                source_type=package.source_type,
                editable=package.editable,
                local_path=local_path,
            )

        if normalized in PROTECTED_PACKAGE_NAMES:
            items.append(
                make_item(
                    action="skip_protected",
                    reason="受保护的管理器或基础安装工具不会通过快照恢复修改",
                )
            )
            continue

        target_packages[normalized] = package
        if current is not None and current.version == package.version:
            items.append(
                make_item(
                    action="skip_same_version",
                    reason="当前版本与快照一致",
                )
            )
            continue

        if local_path is not None and not local_path.exists():
            items.append(
                make_item(
                    action="skip_missing_local_path",
                    reason=f"本地安装来源路径不存在: {local_path}",
                )
            )
            continue

        if normalized in PYTORCH_PACKAGE_NAMES:
            pytorch_to_install.append(package)
            items.append(
                make_item(
                    action="install_pytorch_special",
                    reason="PyTorch 相关包会优先恢复并尝试按版本后缀选择特殊安装源",
                )
            )
        elif current is None:
            items.append(
                make_item(
                    action="install",
                    reason="当前环境未安装该包",
                )
            )
        else:
            items.append(
                make_item(
                    action="update",
                    reason="当前版本与快照不一致",
                )
            )

    dtype, mirror_url, mirror_kind, warning = _pytorch_mirror_plan(pytorch_to_install, options.use_pypi_mirror) if pytorch_to_install else (None, None, None, None)
    if warning is not None:
        warnings.append(warning)
    for item in items:
        if item.action == "install_pytorch_special":
            item.pytorch_device_type = dtype

    if options.prune_packages:
        for normalized, package in current_packages.items():
            if normalized in target_packages or _is_protected_package(package.name):
                continue
            items.append(
                PackageRestorePlanItem(
                    name=package.name,
                    normalized_name=normalized,
                    action="uninstall",
                    reason="启用了清理快照外 Python 包",
                    current_version=package.version,
                    source_type=package.source_type,
                    editable=package.editable,
                    local_path=_local_path_from_package(package),
                )
            )

    return items, dtype, mirror_url, mirror_kind


def restore_python_packages(snapshot: WebUiSnapshot, options: SnapshotRestoreOptions) -> None:
    """恢复 Python 包

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        options (SnapshotRestoreOptions):
            快照恢复选项。
    """
    target_packages = _target_package_map(snapshot)
    current_packages = _current_package_map()
    to_install = [package for normalized, package in target_packages.items() if normalized not in current_packages or current_packages[normalized].version != package.version]

    pytorch_packages = [package for package in to_install if _normalized_package_name(package.name) in PYTORCH_PACKAGE_NAMES]
    other_packages = [package for package in to_install if _normalized_package_name(package.name) not in PYTORCH_PACKAGE_NAMES]

    _install_pytorch_packages(pytorch_packages, options)
    custom_env = _pypi_env(use_pypi_mirror=options.use_pypi_mirror)
    _install_packages(other_packages, custom_env=custom_env, use_uv=options.use_uv)

    if options.prune_packages:
        _prune_python_packages(target_packages=target_packages, current_packages=current_packages)


def _prune_python_packages(
    target_packages: dict[str, PackageSnapshot],
    current_packages: dict[str, PackageSnapshot],
) -> None:
    uninstall_names = [package.name for normalized, package in current_packages.items() if normalized not in target_packages and not _is_protected_package(package.name)]
    if not uninstall_names:
        return

    logger.info("卸载快照外 Python 包: %s", ", ".join(uninstall_names))
    run_cmd([Path(sys.executable).as_posix(), "-m", "pip", "uninstall", *uninstall_names, "-y"])


def _extension_tools(webui_type: str) -> ExtensionRestoreTools | None:
    if webui_type == "sd_webui":
        return ExtensionRestoreTools(
            directory_name="extensions",
            set_status=sd_webui_base.set_sd_webui_extensions_status,
            uninstall=sd_webui_base.uninstall_sd_webui_extension,
        )
    if webui_type == "comfyui":
        return ExtensionRestoreTools(
            directory_name="custom_nodes",
            set_status=comfyui_base.set_comfyui_custom_node_status,
            uninstall=comfyui_base.uninstall_comfyui_custom_node,
            strip_disabled_suffix=True,
        )
    if webui_type == "invokeai":
        return ExtensionRestoreTools(
            directory_name="nodes",
            set_status=invokeai_base.set_invokeai_custom_nodes_status,
            uninstall=invokeai_base.uninstall_invokeai_custom_node,
        )
    return None


def _repo_target_name(repo: RepositorySnapshot | ExtensionSnapshot) -> str:
    return getattr(repo, "name", None) or repo.path.name


def _same_commit(current_commit: str | None, target_commit: str | None) -> bool:
    if current_commit is None or target_commit is None:
        return False
    return current_commit.startswith(target_commit) or target_commit.startswith(current_commit)


def _current_git_commit(path: Path) -> str | None:
    try:
        return git_warpper.get_current_commit(path)
    except Exception:
        return None


def _build_git_restore_plan(
    repo: RepositorySnapshot | ExtensionSnapshot,
    target_path: Path,
    options: SnapshotRestoreOptions,
) -> GitRestorePlanItem:
    name = _repo_target_name(repo)
    if not repo.is_git_repo:
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="skip_non_git_snapshot",
            reason="快照目标不是 Git 仓库",
            target_commit=repo.commit,
            url=repo.url,
        )

    if repo.commit is None:
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="skip_missing_commit",
            reason="快照目标缺少 commit",
            url=repo.url,
        )

    if target_path.exists() and not git_warpper.is_git_repo(target_path):
        if target_path.is_dir() and is_folder_empty(target_path) and repo.url:
            return GitRestorePlanItem(
                name=name,
                path=target_path,
                action="clone",
                reason="目标路径为空目录, 将 clone 后恢复到快照 commit",
                target_commit=repo.commit,
                url=repo.url,
            )
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="skip_non_git_target",
            reason="目标路径已存在且不是 Git 仓库",
            target_commit=repo.commit,
            url=repo.url,
        )

    if not target_path.exists():
        if repo.url is None:
            return GitRestorePlanItem(
                name=name,
                path=target_path,
                action="skip_missing_url",
                reason="目标路径不存在且快照缺少远程地址",
                target_commit=repo.commit,
            )
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="clone",
            reason="目标路径不存在, 将 clone 后恢复到快照 commit",
            target_commit=repo.commit,
            url=repo.url,
        )

    dirty = repository_dirty(target_path, True)
    current_commit = _current_git_commit(target_path)
    if dirty and not options.force_git_reset:
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="blocked_dirty",
            reason="目标仓库存在未提交变更, 需要先处理或启用强制恢复",
            target_commit=repo.commit,
            current_commit=current_commit,
            dirty=dirty,
            url=repo.url,
        )

    if _same_commit(current_commit, repo.commit):
        return GitRestorePlanItem(
            name=name,
            path=target_path,
            action="skip_same_commit",
            reason="当前 commit 与快照一致",
            target_commit=repo.commit,
            current_commit=current_commit,
            dirty=dirty,
            url=repo.url,
        )

    reason = "将切换到快照 commit"
    if dirty and options.force_git_reset:
        reason = "启用了强制恢复, 将覆盖未提交变更并切换到快照 commit"
    return GitRestorePlanItem(
        name=name,
        path=target_path,
        action="switch_commit",
        reason=reason,
        target_commit=repo.commit,
        current_commit=current_commit,
        dirty=dirty,
        url=repo.url,
    )


def _build_missing_kernel_plan(snapshot: WebUiSnapshot, webui_path: Path) -> GitRestorePlanItem:
    kernel = snapshot.kernel
    return GitRestorePlanItem(
        name=_repo_target_name(kernel) if kernel is not None else webui_path.name,
        path=webui_path,
        action="blocked_missing_target",
        reason="内核目录不存在, 请先通过 installer 准备 WebUI kernel 后再恢复快照",
        target_commit=kernel.commit if kernel is not None else None,
        url=kernel.url if kernel is not None else None,
    )


def _ensure_kernel_target_exists(webui_path: Path) -> None:
    if not webui_path.exists():
        raise FileNotFoundError(f"内核目录不存在, 请先通过 installer 准备 WebUI kernel 后再恢复快照: {webui_path}")


def _uses_package_kernel(snapshot: WebUiSnapshot) -> bool:
    return snapshot.webui.type in PACKAGE_KERNEL_WEBUI_TYPES


def _requires_existing_kernel_target(snapshot: WebUiSnapshot) -> bool:
    return not _uses_package_kernel(snapshot)


def _sd_webui_extension_enabled(webui_path: Path, name: str) -> bool | None:
    config_path = webui_path / "config.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    disable_all_extensions = data.get("disable_all_extensions", "none")
    if disable_all_extensions == "all":
        return False
    if disable_all_extensions == "extra":
        return True
    disabled_extensions = data.get("disabled_extensions", [])
    if not isinstance(disabled_extensions, list):
        return None
    return name not in disabled_extensions


def _extension_current_enabled(
    webui_path: Path,
    webui_type: str,
    extension_name: str,
    tools: ExtensionRestoreTools,
) -> bool | None:
    target_path = webui_path / tools.directory_name / extension_name
    if webui_type == "sd_webui":
        return _sd_webui_extension_enabled(webui_path, extension_name)
    if webui_type == "comfyui":
        enabled = comfyui_base.get_comfyui_custom_node_enabled(webui_path, extension_name)
        return enabled if enabled is not None else not extension_name.endswith(".disabled")
    if webui_type == "invokeai":
        return (target_path / "__init__.py").is_file()
    return None


def _extension_source_type(extension: ExtensionSnapshot) -> str:
    source_type = getattr(extension, "source_type", None)
    if source_type:
        return source_type
    return "git" if extension.is_git_repo else "unknown"


def _build_registry_restore_plan(
    extension: ExtensionSnapshot,
    webui_path: Path,
    target_path: Path,
) -> tuple[RegistryRestoreAction, str, str | None, str | None, str | None]:
    registry_id = extension.registry_id or extension.name.removesuffix(".disabled")
    if not registry_id:
        return "skip_registry_missing_id", "快照缺少 Comfy Registry 节点 ID", None, extension.registry_version, None

    resolved = comfyui_base.resolve_comfyui_custom_node_path(webui_path, extension.name) or comfyui_base.resolve_comfyui_custom_node_path(webui_path, registry_id)
    current_version = None
    if resolved is not None:
        current_info = comfy_registry.read_comfy_registry_info(resolved[0])
        if current_info is not None:
            current_version = current_info.version
    target_version = extension.registry_version
    del target_path
    if resolved is None:
        return "install_registry", "安装 Comfy Registry 节点", current_version, target_version, registry_id
    if target_version and current_version == target_version:
        return "skip_same_registry_version", "Registry 节点版本已一致", current_version, target_version, registry_id
    return "switch_registry_version", "切换 Comfy Registry 节点版本", current_version, target_version, registry_id


def _build_extension_restore_plan(
    snapshot: WebUiSnapshot,
    webui_path: Path,
    options: SnapshotRestoreOptions,
    warnings: list[str],
    errors: list[str],
) -> list[ExtensionRestorePlanItem]:
    tools = _extension_tools(snapshot.webui.type)
    if tools is None:
        if snapshot.extensions:
            warnings.append(f"当前 WebUI 类型不支持扩展恢复: {snapshot.webui.type}")
        return []

    items: list[ExtensionRestorePlanItem] = []
    target_names = _target_extension_names(snapshot, tools)
    for extension in snapshot.extensions:
        normalized = normalize_extension_name(extension.name, strip_disabled_suffix=tools.strip_disabled_suffix)
        target_path = _extension_target_path(webui_path, extension, tools)
        source_type = _extension_source_type(extension)
        git_plan = None if source_type == "comfy-registry" else _build_git_restore_plan(extension, target_path, options)
        registry_action = None
        current_version = None
        target_version = None
        registry_id = extension.registry_id
        reason = git_plan.reason if git_plan is not None else ""
        if source_type == "comfy-registry":
            registry_action, reason, current_version, target_version, registry_id = _build_registry_restore_plan(extension, webui_path, target_path)
        current_enabled = _extension_current_enabled(webui_path, snapshot.webui.type, extension.name, tools)
        item = ExtensionRestorePlanItem(
            name=extension.name,
            normalized_name=normalized,
            path=target_path,
            git=git_plan,
            registry_action=registry_action,
            current_enabled=current_enabled,
            target_enabled=extension.enabled,
            source_type=source_type,
            registry_id=registry_id,
            current_version=current_version,
            target_version=target_version,
            reason=reason,
        )
        items.append(item)
        if git_plan is not None and git_plan.action == "blocked_dirty":
            errors.append(f"扩展 '{extension.name}' 存在未提交变更")

    if options.prune_extensions:
        extension_root = webui_path / tools.directory_name
        if extension_root.is_dir():
            for path in sorted(extension_root.iterdir(), key=lambda item: item.name.casefold()):
                if not path.is_dir() or path.name in {"__pycache__", ".disabled"}:
                    continue
                normalized = normalize_extension_name(path.name, strip_disabled_suffix=tools.strip_disabled_suffix)
                if normalized in target_names:
                    continue
                items.append(
                    ExtensionRestorePlanItem(
                        name=path.name,
                        normalized_name=normalized,
                        path=path,
                        cleanup_action="uninstall",
                        current_enabled=_extension_current_enabled(webui_path, snapshot.webui.type, path.name, tools),
                        reason="启用了清理快照外扩展",
                    )
                )
    return items


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
    """恢复 Git 仓库到快照提交

    Args:
        repo (RepositorySnapshot | ExtensionSnapshot):
            快照中的 Git 仓库或扩展记录。
        target_path (Path):
            恢复目标路径。
        options (SnapshotRestoreOptions):
            快照恢复选项。

    Returns:
        bool: 仓库是否已恢复或可视为存在。

    Raises:
        RuntimeError:
            当恢复或 GUI 启动无法安全继续时抛出。
    """
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


def restore_comfy_registry_extension(
    extension: ExtensionSnapshot,
    webui_path: Path,
    options: SnapshotRestoreOptions,
) -> bool:
    """恢复 Comfy Registry 扩展。

    Args:
        extension (ExtensionSnapshot):
            快照中的 Registry 扩展记录。
        webui_path (Path):
            ComfyUI 根目录。
        options (SnapshotRestoreOptions):
            快照恢复选项。

    Returns:
        bool:
            Registry 扩展是否已恢复或可视为存在。
    """
    registry_id = extension.registry_id or extension.name.removesuffix(".disabled")
    if not registry_id:
        logger.warning("快照扩展缺少 Comfy Registry 节点 ID, 跳过: %s", extension.name)
        return False
    resolved = comfyui_base.resolve_comfyui_custom_node_path(webui_path, extension.name) or comfyui_base.resolve_comfyui_custom_node_path(webui_path, registry_id)
    target_path = resolved[0] if resolved is not None else webui_path / "custom_nodes" / registry_id
    custom_env = _pypi_env(use_pypi_mirror=options.use_pypi_mirror)
    try:
        comfy_registry.switch_comfy_registry_node_version(
            comfyui_path=webui_path,
            node_id=registry_id,
            version=extension.registry_version,
            target_path=target_path if target_path.exists() else None,
            use_uv=options.use_uv,
            custom_env=custom_env,
        )
    except comfy_registry.ComfyRegistryInstallUnavailableError as e:
        logger.warning("快照中的 Comfy Registry 节点不可安装，已跳过: %s", e)
        return False
    return True


def _extension_target_path(webui_path: Path, extension: ExtensionSnapshot, tools: ExtensionRestoreTools) -> Path:
    return webui_path / tools.directory_name / extension.name


def _target_extension_names(snapshot: WebUiSnapshot, tools: ExtensionRestoreTools) -> set[str]:
    names = {normalize_extension_name(extension.name, strip_disabled_suffix=tools.strip_disabled_suffix) for extension in snapshot.extensions}
    for extension in snapshot.extensions:
        if extension.registry_id:
            names.add(normalize_extension_name(extension.registry_id, strip_disabled_suffix=tools.strip_disabled_suffix))
    return names


def _prune_extensions(webui_path: Path, snapshot: WebUiSnapshot, tools: ExtensionRestoreTools) -> None:
    extension_root = webui_path / tools.directory_name
    if not extension_root.is_dir():
        return

    target_names = _target_extension_names(snapshot, tools)
    for path in sorted(extension_root.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_dir() or path.name in {"__pycache__", ".disabled"}:
            continue
        normalized = normalize_extension_name(path.name, strip_disabled_suffix=tools.strip_disabled_suffix)
        if normalized in target_names:
            continue
        logger.info("卸载快照外扩展: %s", path.name)
        tools.uninstall(webui_path, path.name)


def restore_extensions(snapshot: WebUiSnapshot, webui_path: Path, options: SnapshotRestoreOptions) -> None:
    """恢复 WebUI 扩展

    Args:
        snapshot (WebUiSnapshot):
            WebUI 环境快照。
        webui_path (Path):
            WebUI 根目录。
        options (SnapshotRestoreOptions):
            快照恢复选项。
    """
    tools = _extension_tools(snapshot.webui.type)
    if tools is None:
        if snapshot.extensions:
            logger.warning("当前 WebUI 类型不支持扩展恢复: %s", snapshot.webui.type)
        return

    for extension in snapshot.extensions:
        source_type = _extension_source_type(extension)
        if source_type == "comfy-registry" and snapshot.webui.type == "comfyui":
            restored = restore_comfy_registry_extension(extension=extension, webui_path=webui_path, options=options)
        else:
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


def preview_webui_snapshot_restore(
    snapshot_path: Path,
    webui_path: Path,
    expected_webui_type: str,
    options: SnapshotRestoreOptions | None = None,
) -> SnapshotRestorePlan:
    """预检查 WebUI 快照恢复将执行的变更

    Args:
        snapshot_path (Path):
            快照 JSON 文件路径。
        webui_path (Path):
            WebUI 根目录。
        expected_webui_type (str):
            期望的 WebUI 类型。
        options (SnapshotRestoreOptions | None):
            快照恢复选项。

    Returns:
        SnapshotRestorePlan: 快照恢复预检查计划。
    """
    if options is None:
        options = SnapshotRestoreOptions()

    snapshot = load_snapshot(snapshot_path)
    webui_type_match = snapshot.webui.type == expected_webui_type
    plan = SnapshotRestorePlan(
        webui_type_match=webui_type_match,
        expected_webui_type=expected_webui_type,
        snapshot_webui_type=snapshot.webui.type,
        snapshot_webui_name=snapshot.webui.name,
        snapshot_path=snapshot_path,
        webui_path=webui_path,
    )

    if not webui_type_match:
        plan.errors.append(f"快照 WebUI 类型不匹配: 期望 '{expected_webui_type}', 实际 '{snapshot.webui.type}'")
        return plan

    current_python_version = platform.python_version()
    if snapshot.python.version != current_python_version:
        plan.python_version_note = f"快照 Python 版本为 {snapshot.python.version}, 当前 Python 版本为 {current_python_version}; 恢复时不会修改 Python 版本"

    if _requires_existing_kernel_target(snapshot) and not webui_path.exists():
        plan.kernel_change = _build_missing_kernel_plan(snapshot, webui_path)
        plan.errors.append(f"内核目录不存在: {webui_path}")
        return plan

    package_changes, dtype, mirror_url, mirror_kind = _build_package_restore_plan(snapshot, options, plan.warnings)
    plan.package_changes = package_changes
    plan.pytorch_device_type = dtype
    plan.pytorch_mirror_url = mirror_url
    plan.pytorch_mirror_kind = mirror_kind

    if snapshot.kernel is not None and not _uses_package_kernel(snapshot):
        plan.kernel_change = _build_git_restore_plan(snapshot.kernel, webui_path, options)
        if plan.kernel_change.action == "blocked_dirty":
            plan.errors.append("内核仓库存在未提交变更")

    plan.extension_changes = _build_extension_restore_plan(
        snapshot=snapshot,
        webui_path=webui_path,
        options=options,
        warnings=plan.warnings,
        errors=plan.errors,
    )
    return plan


def restore_webui_snapshot(
    snapshot_path: Path,
    webui_path: Path,
    expected_webui_type: str,
    options: SnapshotRestoreOptions | None = None,
) -> None:
    """从快照文件恢复 WebUI 环境

    Args:
        snapshot_path (Path):
            快照 JSON 文件路径。
        webui_path (Path):
            WebUI 根目录。
        expected_webui_type (str):
            期望的 WebUI 类型。
        options (SnapshotRestoreOptions | None):
            快照恢复选项。

    Raises:
        ValueError:
            当输入数据无效或快照内容不匹配时抛出。
    """
    if options is None:
        options = SnapshotRestoreOptions()

    snapshot = load_snapshot(snapshot_path)
    if snapshot.webui.type != expected_webui_type:
        raise ValueError(f"快照 WebUI 类型不匹配: 期望 '{expected_webui_type}', 实际 '{snapshot.webui.type}'")
    if _requires_existing_kernel_target(snapshot):
        _ensure_kernel_target_exists(webui_path)

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
        if snapshot.kernel is not None and not _uses_package_kernel(snapshot):
            restore_git_repository(repo=snapshot.kernel, target_path=webui_path, options=options)
        restore_extensions(snapshot=snapshot, webui_path=webui_path, options=options)
    finally:
        if old_git_config is None:
            os.environ.pop("GIT_CONFIG_GLOBAL", None)
        else:
            os.environ["GIT_CONFIG_GLOBAL"] = old_git_config
