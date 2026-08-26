"""产品、扩展和软件包更新检查。"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,too-many-locals

from pathlib import Path
from typing import (
    Callable,
    Iterable,
    Literal,
)

from sd_webui_all_in_one.base_manager.base import (
    get_pytorch_update_status,
)
from sd_webui_all_in_one.base_manager.repository_inspector import (
    RepositoryState as RepositoryState,
)
from sd_webui_all_in_one.package_analyzer import PyWhlVersionComparison, get_package_version_from_library

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


from sd_webui_all_in_one.base_manager.version_manager.indexes import fetch_pypi_versions
from sd_webui_all_in_one.base_manager.version_manager.models import (
    ExtensionUpdateStatus,
    ManagedExtension,
    PackageUpdateStatus,
    RepositoryUpdateStatus,
    WebUiUpdateOptions,
    WebUiUpdateStatus,
    WebUiUpdateSummary,
)
from sd_webui_all_in_one.base_manager.version_manager.repository import check_repository_update


def check_package_update(
    package_name: str,
    display_name: str,
    index_url: str,
    timeout: int | None = 20,
    allow_prerelease: bool = False,
) -> PackageUpdateStatus:
    """检查作为 WebUI 内核安装的 PyPI 包是否有更新。

    默认只把正式发布版本作为更新目标。PyPI 上新发布的预发布版本 (如 ``6.10.0rc1``)
    版本号高于当前正式版本, 若直接取版本列表的第一项会误报 "有更新", 并把预发布
    版本显示成最新版本。

    Args:
        package_name (str): PyPI 包名。
        display_name (str): 内核显示名称。
        index_url (str): PyPI JSON API 或镜像地址。
        timeout (int | None): 请求超时时间。
        allow_prerelease (bool): 是否把预发布版本也作为更新目标, 默认为 ``False``。

    Returns:
        PackageUpdateStatus: PyPI 内核包的详细更新状态。
    """
    current_version = get_package_version_from_library(package_name)
    logger.info("检查软件包更新中: %s (%s)", display_name, package_name)
    latest_prerelease: str | None = None
    try:
        versions = fetch_pypi_versions(
            package_name,
            current_version=current_version,
            index_url=index_url,
            timeout=timeout,
        )
        # 版本列表已按版本号从新到旧排序, 取符合发布通道的第一项即为最新版本。
        candidates = versions if allow_prerelease else [item for item in versions if not item.is_prerelease]
        latest_version = candidates[0].version if candidates else None
        newest_prerelease = next((item.version for item in versions if item.is_prerelease), None)
        # 预发布通道只在走在正式通道前面时才值得单独报告。
        if newest_prerelease is not None and (latest_version is None or PyWhlVersionComparison(latest_version) < PyWhlVersionComparison(newest_prerelease)):
            latest_prerelease = newest_prerelease
        if latest_version is not None:
            error = None
        elif versions:
            error = "未获取到 PyPI 正式发布版本"
        else:
            error = "未获取到 PyPI 版本列表"
        has_update = latest_version is not None and (current_version is None or PyWhlVersionComparison(current_version) < PyWhlVersionComparison(latest_version))
    except Exception as exc:
        latest_version = None
        has_update = False
        error = str(exc)
        logger.error("检查软件包更新失败: %s", exc)
    logger.info("软件包更新检查完成: %s, 当前版本 %s, 最新版本 %s, 是否有更新: %s", display_name, current_version, latest_version, has_update)
    return PackageUpdateStatus(
        name=display_name,
        package_name=package_name,
        installed=current_version is not None,
        current_version=current_version,
        latest_version=latest_version,
        has_update=has_update,
        index_url=index_url,
        error=error,
        latest_prerelease=latest_prerelease,
    )


def check_extension_updates(
    extensions: Iterable[ManagedExtension],
    *,
    fetch: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    registry_version_resolver: Callable[[ManagedExtension], str | None] | None = None,
) -> list[ExtensionUpdateStatus]:
    """检查一组已安装扩展的更新状态。

    Args:
        extensions (Iterable[ManagedExtension]): 已安装扩展信息。
        fetch (bool): 是否先获取 Git 远程引用。
        use_github_mirror (bool): 是否启用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None): 自定义 GitHub 镜像源。
        registry_version_resolver (Callable[[ManagedExtension], str | None] | None):
            Registry 扩展最新版本解析函数。

    Returns:
        list[ExtensionUpdateStatus]: 每个扩展的详细更新状态。
    """
    result: list[ExtensionUpdateStatus] = []
    logger.info("检查扩展更新中")
    for extension in extensions:
        logger.debug("检查扩展更新: %s", extension.name)
        status = ExtensionUpdateStatus(
            name=extension.name,
            path=extension.path,
            enabled=extension.enabled,
            source_type=extension.source_type,
            is_git_repo=extension.is_git_repo,
            url=extension.url,
            branch=extension.branch,
            current_version=extension.registry_version or extension.commit,
            registry_id=extension.registry_id,
        )
        if extension.is_git_repo:
            repository = check_repository_update(
                extension.path,
                fetch=fetch,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )
            status.remote_branch = repository.remote_branch
            status.current_version = repository.current_commit
            status.latest_version = repository.remote_commit
            status.ahead = repository.ahead
            status.behind = repository.behind
            status.has_update = repository.has_update
            status.error = repository.error
            status.message = "存在远程更新" if repository.has_update else (repository.error or "已是最新版本")
        elif extension.source_type == "comfy-registry" and registry_version_resolver is not None:
            try:
                status.latest_version = registry_version_resolver(extension)
                if status.latest_version is None:
                    status.error = "未获取到 Registry 最新版本"
                elif status.current_version is None:
                    status.error = "未获取到已安装的 Registry 版本"
                else:
                    status.has_update = status.current_version != status.latest_version
                    status.message = "存在 Registry 更新" if status.has_update else "已是最新版本"
            except Exception as exc:
                status.error = str(exc)
                logger.error("检查 Registry 扩展更新失败: %s", exc)
        else:
            status.skipped = True
            status.message = f"扩展来源 '{extension.source_type}' 不支持更新检查"
            logger.debug("扩展来源 '%s' 不支持更新检查, 已跳过: %s", extension.source_type, extension.name)
        result.append(status)
    logger.info("检查扩展更新完成, 共 %s 个扩展", len(result))
    return result


def check_webui_updates(
    webui_type: str,
    display_name: str,
    webui_path: Path,
    *,
    extension_loader: Callable[[], list[ManagedExtension]] | None = None,
    registry_version_resolver: Callable[[ManagedExtension], str | None] | None = None,
    kernel_package_name: str | None = None,
    options: WebUiUpdateOptions | None = None,
) -> WebUiUpdateStatus:
    """聚合单个 WebUI 的内核、扩展和 PyTorch 更新状态。

    Args:
        webui_type (str): WebUI 类型标识。
        display_name (str): WebUI 显示名称。
        webui_path (Path): WebUI 根目录。
        extension_loader (Callable[[], list[ManagedExtension]] | None): 扩展加载函数。
        registry_version_resolver (Callable[[ManagedExtension], str | None] | None): Registry 最新版本解析函数。
        kernel_package_name (str | None): 使用 PyPI 安装的内核包名；为 None 时检查 Git 内核。
        options (WebUiUpdateOptions | None): 更新检查选项。

    Returns:
        WebUiUpdateStatus: WebUI 的完整结构化更新状态。
    """
    options = options or WebUiUpdateOptions()
    logger.info("检查 WebUI 更新中: %s (%s)", display_name, webui_type)
    errors: list[str] = []
    kernel: RepositoryUpdateStatus | PackageUpdateStatus | None = None
    if options.include_kernel:
        if kernel_package_name is None:
            kernel = check_repository_update(
                webui_path,
                fetch=options.fetch,
                use_github_mirror=options.use_github_mirror,
                custom_github_mirror=options.custom_github_mirror,
            )
        else:
            kernel = check_package_update(
                kernel_package_name,
                display_name,
                options.pypi_index_url,
                timeout=options.timeout,
                allow_prerelease=options.allow_prerelease,
            )

    pytorch = get_pytorch_update_status() if options.include_pytorch else None
    extensions: list[ExtensionUpdateStatus] = []
    if options.include_extensions and extension_loader is not None:
        try:
            extensions = check_extension_updates(
                extension_loader(),
                fetch=options.fetch,
                use_github_mirror=options.use_github_mirror,
                custom_github_mirror=options.custom_github_mirror,
                registry_version_resolver=registry_version_resolver,
            )
        except Exception as exc:
            errors.append(f"加载扩展失败: {exc}")
            logger.error("加载扩展失败: %s", exc)

    kernel_has_update = bool(kernel and kernel.has_update)
    pytorch_has_update = bool(pytorch and pytorch.has_update)
    extension_update_count = sum(item.has_update for item in extensions)
    skipped_count = sum(item.skipped for item in extensions)
    error_count = len(errors) + int(bool(kernel and kernel.error)) + int(bool(pytorch and pytorch.error)) + sum(bool(item.error) for item in extensions)
    summary = WebUiUpdateSummary(
        has_update=kernel_has_update or pytorch_has_update or extension_update_count > 0,
        kernel_has_update=kernel_has_update,
        pytorch_has_update=pytorch_has_update,
        extension_update_count=extension_update_count,
        checked_extension_count=len(extensions) - skipped_count,
        skipped_count=skipped_count,
        error_count=error_count,
    )
    logger.info("WebUI 更新检查完成: %s, 是否有更新: %s, 可更新扩展 %s 个", display_name, summary.has_update, summary.extension_update_count)
    return WebUiUpdateStatus(
        webui_type=webui_type,
        name=display_name,
        path=webui_path,
        kernel=kernel,
        pytorch=pytorch,
        extensions=extensions,
        extensions_supported=extension_loader is not None,
        summary=summary,
        errors=errors,
    )
