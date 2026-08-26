"""Runtime environment and repository snapshot collection."""

from __future__ import annotations

import platform
import sys
from importlib import metadata
from pathlib import Path

from sd_webui_all_in_one.base_manager.repository_inspector import RepositoryState, inspect_repository, run_git_output

from sd_webui_all_in_one.base_manager.snapshot.codec import _parse_direct_url
from sd_webui_all_in_one.base_manager.snapshot.models import (
    SNAPSHOT_SCHEMA_VERSION,
    DirectUrlSnapshot,
    ExtensionEnabledResolver,
    ExtensionSnapshot,
    PackageSnapshot,
    PythonSnapshot,
    RepositorySnapshot,
    SourceType,
    SystemSnapshot,
    WebUiIdentitySnapshot,
    WebUiSnapshot,
    WheelSnapshot,
    logger,
    utc_now_iso,
)


def collect_python_info() -> PythonSnapshot:
    """采集当前 Python 解释器信息

    Returns:
        PythonSnapshot: 当前 Python 解释器快照。
    """
    logger.debug("采集 Python 解释器信息")
    return PythonSnapshot(
        version=platform.python_version(),
        implementation=platform.python_implementation(),
        executable=Path(sys.executable),
        platform=sys.platform,
    )


def collect_system_info() -> SystemSnapshot:
    """采集当前系统和架构信息

    Returns:
        SystemSnapshot: 当前系统环境快照。
    """
    logger.debug("采集系统信息: %s/%s", platform.system() or sys.platform, platform.machine() or "unknown")
    return SystemSnapshot(
        system=platform.system() or sys.platform,
        architecture=platform.machine() or "unknown",
    )


def _read_distribution_text(dist: metadata.Distribution, filename: str) -> str | None:
    try:
        return dist.read_text(filename)
    except Exception:
        logger.warning("读取发行版元数据文件失败: %s", filename)
        return None


def _source_type_from_direct_url(direct_url: DirectUrlSnapshot | None) -> SourceType:
    if direct_url is None:
        return "unknown"
    if direct_url.vcs_info is not None:
        return "vcs"
    if direct_url.dir_info is not None:
        return "local-directory"
    if direct_url.archive_info is not None:
        return "archive"
    return "unknown"


def _editable_from_direct_url(direct_url: DirectUrlSnapshot | None) -> bool:
    if direct_url is None:
        return False
    if direct_url.dir_info is None:
        return False
    return bool(direct_url.dir_info.editable)


def _parse_wheel_metadata(raw_wheel: str | None) -> WheelSnapshot | None:
    if not raw_wheel:
        return None

    generator: str | None = None
    root_is_purelib: bool | None = None
    tags: list[str] = []
    for line in raw_wheel.splitlines():
        key, sep, value = line.partition(":")
        if sep == "":
            continue
        normalized_key = key.strip().lower()
        normalized_value = value.strip()
        if normalized_key == "generator":
            generator = normalized_value
        elif normalized_key == "root-is-purelib":
            root_is_purelib = normalized_value.lower() == "true"
        elif normalized_key == "tag":
            tags.append(normalized_value)

    logger.debug("解析 WHEEL 元数据: generator=%s, 标签数=%s", generator, len(tags))
    return WheelSnapshot(
        generator=generator,
        root_is_purelib=root_is_purelib,
        tags=tags,
    )


def collect_installed_packages() -> list[PackageSnapshot]:
    """采集当前 Python 环境已安装软件包信息

    Returns:
        list[PackageSnapshot]: 已安装 Python 包快照列表。
    """
    packages: list[PackageSnapshot] = []
    logger.info("开始采集已安装 Python 包")
    for dist in metadata.distributions():
        try:
            name = dist.metadata["Name"]
        except KeyError:
            logger.debug("跳过无名称的发行版")
            continue
        if not name:
            logger.debug("跳过名称为空的发行版")
            continue

        direct_url = _parse_direct_url(_read_distribution_text(dist, "direct_url.json"))
        installer_raw = _read_distribution_text(dist, "INSTALLER")
        requested_raw = _read_distribution_text(dist, "REQUESTED")
        wheel = _parse_wheel_metadata(_read_distribution_text(dist, "WHEEL"))

        packages.append(
            PackageSnapshot(
                name=name,
                version=dist.version,
                installer=installer_raw.strip() if installer_raw else None,
                requested=requested_raw is not None,
                editable=_editable_from_direct_url(direct_url),
                direct_url=direct_url,
                source_type=_source_type_from_direct_url(direct_url),
                wheel=wheel,
            )
        )
        logger.debug("采集到包: %s %s", name, dist.version)

    result = sorted(packages, key=lambda item: item.name.lower())
    logger.info("已采集 %s 个已安装 Python 包", len(result))
    return result


def repository_state_to_snapshot(state: RepositoryState) -> RepositorySnapshot:
    """将仓库状态转换为快照字段

    Args:
        state (RepositoryState):
            仓库检查结果。

    Returns:
        RepositorySnapshot: 仓库快照对象。
    """
    return RepositorySnapshot(
        path=state.path,
        name=state.name,
        is_git_repo=state.is_git_repo,
        url=state.url,
        branch=state.branch,
        commit=state.commit,
        commit_date=state.commit_date,
        message=state.message,
        error=state.error,
    )


def repository_dirty(path: Path, is_git_repo: bool) -> bool | None:
    """检查 Git 仓库是否存在未提交变更

    Args:
        path (Path):
            Git 仓库路径。
        is_git_repo (bool):
            目标路径是否为 Git 仓库。

    Returns:
        bool | None: Git 仓库是否存在未提交变更；非 Git 仓库或检查失败时返回 None。
    """
    if not is_git_repo:
        return None
    try:
        return run_git_output(path, "status", "--porcelain") != ""
    except Exception:
        logger.warning("检查 Git 仓库变更状态失败: %s", path)
        return None


def collect_repository_snapshot(path: Path) -> RepositorySnapshot:
    """采集 Git 仓库快照

    Args:
        path (Path):
            Git 仓库路径。

    Returns:
        RepositorySnapshot: Git 仓库快照。
    """
    logger.debug("采集仓库快照: %s", path)
    state = inspect_repository(path)
    if state.error:
        logger.warning("仓库检查存在问题: %s (%s)", path, state.error)
    snapshot = repository_state_to_snapshot(state)
    snapshot.dirty = repository_dirty(path, state.is_git_repo)
    logger.debug("仓库快照: 名称=%s, is_git_repo=%s, 分支=%s, 提交=%s", snapshot.name, snapshot.is_git_repo, snapshot.branch, snapshot.commit)
    return snapshot


def collect_git_extensions(
    extension_dir: Path,
    enabled_resolver: ExtensionEnabledResolver | None = None,
    ignored_names: set[str] | None = None,
) -> list[ExtensionSnapshot]:
    """采集扩展目录中的 Git 扩展快照

    Args:
        extension_dir (Path):
            扩展根目录。
        enabled_resolver (ExtensionEnabledResolver | None):
            用于判断扩展启用状态的回调。
        ignored_names (set[str] | None):
            采集扩展时需要忽略的目录名。

    Returns:
        list[ExtensionSnapshot]: Git 扩展快照列表。
    """
    if ignored_names is None:
        ignored_names = {"__pycache__"}
    if not extension_dir.is_dir():
        logger.warning("扩展目录不存在: %s", extension_dir)
        return []

    logger.info("开始采集 Git 扩展: %s", extension_dir)
    extensions: list[ExtensionSnapshot] = []
    for ext_path in sorted(extension_dir.iterdir(), key=lambda item: item.name.lower()):
        if ext_path.name in ignored_names or not ext_path.is_dir():
            logger.debug("跳过忽略或非目录的条目: %s", ext_path)
            continue
        repo = collect_repository_snapshot(ext_path)
        if not repo.is_git_repo:
            logger.warning("跳过非 Git 仓库的扩展: %s", ext_path)
            continue
        enabled = enabled_resolver(ext_path.name, ext_path) if enabled_resolver is not None else None
        logger.debug("采集到 Git 扩展: %s (%s)", ext_path.name, repo.url)
        extensions.append(
            ExtensionSnapshot(
                name=ext_path.name,
                path=ext_path,
                enabled=enabled,
                is_git_repo=repo.is_git_repo,
                url=repo.url,
                branch=repo.branch,
                commit=repo.commit,
                commit_date=repo.commit_date,
                message=repo.message,
                error=repo.error,
                dirty=repo.dirty,
                source_type="git",
            )
        )
    logger.info("已采集 %s 个 Git 扩展", len(extensions))
    return extensions


def build_webui_snapshot(
    webui_name: str,
    webui_type: str,
    webui_path: Path,
    include_packages: bool = True,
    extensions: list[ExtensionSnapshot] | None = None,
) -> WebUiSnapshot:
    """构建 WebUI 环境快照

    Args:
        webui_name (str):
            WebUI 显示名称。
        webui_type (str):
            WebUI 类型标识。
        webui_path (Path):
            WebUI 根目录。
        include_packages (bool):
            是否采集当前 Python 包列表。
        extensions (list[ExtensionSnapshot] | None):
            已采集的扩展快照列表。

    Returns:
        WebUiSnapshot: WebUI 环境快照。
    """
    logger.info("开始采集 %s 环境快照: %s", webui_name, webui_path)
    packages = collect_installed_packages() if include_packages else []
    kernel = collect_repository_snapshot(webui_path)
    extension_list = extensions or []
    logger.info("环境快照采集完成: 包 %s 个, 扩展 %s 个", len(packages), len(extension_list))
    return WebUiSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        created_at=utc_now_iso(),
        webui=WebUiIdentitySnapshot(
            name=webui_name,
            type=webui_type,
            path=webui_path,
        ),
        python=collect_python_info(),
        packages=packages,
        kernel=kernel,
        extensions=extension_list,
        system=collect_system_info(),
    )
