"""已安装扩展管理。"""

# pylint: disable=too-many-instance-attributes,too-many-arguments,too-many-positional-arguments,too-many-locals

from pathlib import Path
from typing import (
    Callable,
    Iterable,
    Literal,
)

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    clone_repo,
    get_repo_name_from_url,
)
from sd_webui_all_in_one.base_manager.repository_inspector import (
    RepositoryState,  # noqa: F401
    inspect_repository,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.file_manager import remove_files

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


from sd_webui_all_in_one.base_manager.version_manager.models import ManagedExtension, RepositoryUpdateStatus
from sd_webui_all_in_one.base_manager.version_manager.repository import (
    check_repository_update,
    switch_repository_branch,
    switch_repository_commit,
    update_repository,
)


class ExtensionManager:
    """
    可复用扩展管理器

    抽象扩展目录、启禁用策略、安装、更新、卸载和版本切换流程,
    使不同 WebUI 可以通过不同目录和启禁用函数复用同一套逻辑。
    """

    def __init__(
        self,
        root_path: Path,
        extension_dir_name: str,
        is_enabled: Callable[[str, Path], bool],
        set_enabled: Callable[[str, bool], None],
        ignored_names: Iterable[str] | None = None,
        include_files: bool = False,
    ) -> None:
        """
        初始化扩展管理器

        Args:
            root_path (Path):
                WebUI 根目录
            extension_dir_name (str):
                扩展目录名称
            is_enabled (Callable[[str, Path], bool]):
                扩展启用状态读取函数
            set_enabled (Callable[[str, bool], None]):
                扩展启用状态写入函数
            ignored_names (Iterable[str] | None):
                需要忽略的扩展名称
            include_files (bool):
                是否允许把单文件扩展纳入列表
        """
        self.root_path = Path(root_path)
        self.extension_path = self.root_path / extension_dir_name
        self.is_enabled = is_enabled
        self.set_enabled = set_enabled
        self.ignored_names = set(ignored_names or {"__pycache__"})
        self.include_files = include_files
        logger.info("初始化扩展管理器完成, 扩展目录: %s", self.extension_path)

    def list_extensions(self) -> list[ManagedExtension]:
        """
        获取本地扩展列表

        Returns:
            list[ManagedExtension]: 本地扩展列表
        """
        if not self.extension_path.exists():
            logger.warning("扩展目录不存在: %s", self.extension_path)
            return []
        result: list[ManagedExtension] = []
        for ext_path in sorted(self.extension_path.iterdir(), key=lambda item: item.name.lower()):
            if ext_path.name in self.ignored_names:
                continue
            if not ext_path.is_dir() and not (self.include_files and ext_path.is_file()):
                continue
            logger.debug("解析扩展: %s", ext_path.name)
            repo_state = inspect_repository(ext_path)
            result.append(
                ManagedExtension(
                    name=ext_path.name,
                    path=ext_path,
                    enabled=self.is_enabled(ext_path.name, ext_path),
                    is_git_repo=repo_state.is_git_repo,
                    url=repo_state.url,
                    branch=repo_state.branch,
                    commit=repo_state.commit,
                    commit_date=repo_state.commit_date,
                    message=repo_state.message,
                    error=repo_state.error,
                    source_type="git" if repo_state.is_git_repo else ("file" if ext_path.is_file() else "unknown"),
                )
            )
        logger.info("获取扩展列表完成: %s, 共 %s 个扩展", self.extension_path, len(result))
        return result

    def set_extension_enabled(
        self,
        name: str,
        enabled: bool,
    ) -> None:
        """
        设置扩展启用状态

        Args:
            name (str):
                扩展名称
            enabled (bool):
                是否启用
        """
        logger.info("设置扩展启用状态: %s -> %s", name, enabled)
        self.set_enabled(name, enabled)

    def install_extension(
        self,
        url: str,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> Path:
        """
        从 Git 地址安装扩展

        Args:
            url (str):
                Git 仓库地址
            use_github_mirror (bool):
                是否启用 GitHub 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像源

        Returns:
            Path: 扩展安装路径

        Raises:
            FileExistsError:
                扩展已经存在
        """
        del use_github_mirror, custom_github_mirror
        extension_name = get_repo_name_from_url(url)
        extension_path = self.extension_path / extension_name
        logger.info("安装扩展中: %s", url)
        if extension_path.exists():
            logger.warning("扩展已存在, 无法安装: %s", extension_path)
            raise FileExistsError(f"'{extension_name}' 扩展已存在")
        clone_repo(repo=url, path=extension_path)
        logger.info("扩展安装完成: %s", extension_path)
        return extension_path

    def update_extension(
        self,
        name: str,
    ) -> None:
        """
        更新扩展

        Args:
            name (str):
                扩展名称

        Raises:
            ValueError:
                扩展不是 Git 仓库
        """
        ext_path = self.extension_path / name
        logger.info("更新扩展中: %s", name)
        if not git_warpper.is_git_repo(ext_path):
            logger.warning("扩展 '%s' 不是 Git 仓库, 无法更新", name)
            raise ValueError(f"'{name}' 不是 Git 仓库，无法更新")
        update_repository(ext_path)
        logger.info("更新扩展完成: %s", name)

    def update_all(
        self,
    ) -> None:
        """
        更新所有 Git 扩展

        Raises:
            AggregateError:
                一个或多个扩展更新失败
        """
        errors: list[Exception] = []
        logger.info("更新所有扩展中: %s", self.extension_path)
        for ext in self.list_extensions():
            if not ext.is_git_repo:
                continue
            try:
                update_repository(ext.path)
            except Exception as e:
                logger.error("更新扩展 '%s' 时发生错误: %s", ext.name, e)
                errors.append(e)
        if errors:
            logger.error("更新扩展时发生错误, 共 %s 个扩展更新失败", len(errors))
            raise AggregateError("更新扩展时发生错误", errors)
        logger.info("更新所有扩展完成: %s", self.extension_path)

    def check_updates(
        self,
        fetch: bool = True,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> list[RepositoryUpdateStatus]:
        """
        检查所有扩展是否存在远程更新

        Args:
            fetch (bool):
                是否先拉取远程引用
            use_github_mirror (bool):
                是否启用 GitHub 镜像源
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像源

        Returns:
            list[RepositoryUpdateStatus]: 扩展更新状态列表
        """
        result: list[RepositoryUpdateStatus] = []
        logger.info("检查扩展更新中: %s", self.extension_path)
        for ext in self.list_extensions():
            if not ext.is_git_repo:
                result.append(
                    RepositoryUpdateStatus(
                        name=ext.name,
                        path=ext.path,
                        is_git_repo=False,
                        branch=ext.branch,
                        current_commit=ext.commit,
                        error=ext.error or "非 Git 仓库",
                    )
                )
                continue
            status = check_repository_update(
                ext.path,
                fetch=fetch,
                use_github_mirror=use_github_mirror,
                custom_github_mirror=custom_github_mirror,
            )
            status.name = ext.name
            result.append(status)
        logger.info("检查扩展更新完成: %s, 共 %s 个扩展", self.extension_path, len(result))
        return result

    def uninstall_extension(
        self,
        name: str,
    ) -> None:
        """
        卸载扩展

        Args:
            name (str):
                扩展名称

        Raises:
            FileNotFoundError:
                扩展未安装
        """
        ext_path = self.extension_path / name
        logger.info("卸载扩展中: %s", name)
        if not ext_path.exists():
            logger.warning("扩展未安装, 无法卸载: %s", name)
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        remove_files(ext_path)
        logger.info("卸载扩展完成: %s", name)

    def switch_extension_commit(
        self,
        name: str,
        commit: str,
    ) -> None:
        """
        切换扩展到指定提交

        Args:
            name (str):
                扩展名称
            commit (str):
                目标提交 ID
        """
        logger.info("切换扩展到指定提交: %s -> %s", name, commit)
        switch_repository_commit(self.extension_path / name, commit)

    def switch_extension_branch(
        self,
        name: str,
        branch: str,
    ) -> None:
        """
        切换扩展分支

        Args:
            name (str):
                扩展名称
            branch (str):
                目标分支
        """
        logger.info("切换扩展分支: %s -> %s", name, branch)
        switch_repository_branch(self.extension_path / name, branch)
