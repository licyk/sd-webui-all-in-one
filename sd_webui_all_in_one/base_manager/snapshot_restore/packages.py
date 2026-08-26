"""Python package restore planning and execution."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from sd_webui_all_in_one.base_manager.base import install_pytorch_with_fallback
from sd_webui_all_in_one.base_manager.snapshot import PackageSnapshot, WebUiSnapshot, collect_installed_packages
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.env_manager import generate_uv_and_pip_env_mirror_config
from sd_webui_all_in_one.mirror_manager import get_pypi_mirror_config
from sd_webui_all_in_one.package_analyzer import normalize_package_name
from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.pytorch_manager import get_pytorch_mirror, infer_pytorch_device_type

from sd_webui_all_in_one.base_manager.snapshot_restore.models import PackageRestoreAction, PackageRestorePlanItem, SnapshotRestoreOptions, logger

PYTORCH_PACKAGE_NAMES = {"torch", "torchvision", "torchaudio", "xformers"}
PROTECTED_PACKAGE_NAMES = {"sd-webui-all-in-one", "pip", "wheel", "uv"}


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


def _pypi_env(use_pypi_mirror: bool) -> dict[str, str]:
    return get_pypi_mirror_config(use_cn_mirror=use_pypi_mirror)


def _pytorch_env(packages: list[PackageSnapshot], use_pypi_mirror: bool) -> dict[str, str]:
    dtype = infer_pytorch_device_type(package.version for package in packages) or "all"

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
    logger.debug("PyTorch 特殊源: dtype=%s, kind=%s", dtype, kind)
    return generate_uv_and_pip_env_mirror_config(
        index_url=mirrors["index_url"],
        extra_index_url=mirrors["extra_index_url"],
        find_links=mirrors["find_links"],
    )


def _pytorch_mirror_plan(
    packages: list[PackageSnapshot],
    use_pypi_mirror: bool,
) -> tuple[str | None, str | None, str | None, str | None]:
    dtype = infer_pytorch_device_type(package.version for package in packages) or "all"

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
    logger.debug("PyTorch 相关包: torch=%s, xformers=%s", [p.name for p in torch_packages], [p.name for p in xformers_packages])
    custom_env = _pytorch_env(packages, use_pypi_mirror=options.use_pypi_mirror)
    torch_package = [*[_package_version_spec(package) for package in torch_packages], "--no-deps"] if torch_packages else None
    xformers_package = [*[_package_version_spec(package) for package in xformers_packages], "--no-deps"] if xformers_packages else None

    logger.info("恢复 PyTorch 相关包: %s", ", ".join(package.name for package in packages))
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
        logger.debug("检查 Python 包: %s (当前 %s, 快照 %s)", package.name, current.version if current is not None else "未安装", package.version)

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

    logger.info("开始恢复 Python 包, 待安装 %s 个 (PyTorch %s 个, 其他 %s 个)", len(to_install), len(pytorch_packages), len(other_packages))
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
