"""Implementation grouped from the former ``model_manager.py`` module."""

from __future__ import annotations

import os
from pathlib import Path
from sd_webui_all_in_one.downloader import DownloadToolType, download_file
from sd_webui_all_in_one.file_manager import copy_files, copy_files_merge, move_files, move_files_merge, remove_files

from .models import FILE_MODEL_ROOT_DIRS, FileWebUiModelType, ModelEntry, ModelRoot, logger


def _is_path_name(value: str) -> bool:
    return value not in {"", ".", ".."} and "\x00" not in value and "/" not in value and "\\" not in value


def _path_size(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            logger.debug("读取文件大小失败, 视为 0 字节: %s", path)
            return 0
    return 0


class FileModelManager:
    """基于 WebUI 模型目录的文件管理器"""

    def __init__(self, webui_type: FileWebUiModelType) -> None:
        if webui_type not in FILE_MODEL_ROOT_DIRS:
            raise ValueError(f"不支持按文件夹管理模型的 WebUI 类型: {webui_type}")
        self.webui_type = webui_type
        logger.debug("初始化 FileModelManager, webui_type=%s", webui_type)

    def root(self, webui_path: Path) -> ModelRoot:
        """返回模型根目录信息。

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            ModelRoot: WebUI 类型、根目录和模型目录。
        """
        path = Path(webui_path)
        root_path = path / FILE_MODEL_ROOT_DIRS[self.webui_type]
        logger.debug("计算模型根目录: %s, 根目录=%s", self.webui_type, root_path)
        return ModelRoot(
            webui_type=self.webui_type,
            webui_path=path,
            root_path=root_path,
        )

    def root_path(self, webui_path: Path) -> Path:
        """返回模型根目录路径。

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            Path: WebUI 模型根目录。
        """
        return self.root(webui_path).root_path

    def ensure_root(self, webui_path: Path) -> Path:
        """确保模型根目录存在并返回路径

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            Path:
                已创建或已存在的模型根目录。
        """
        root = self.root_path(webui_path)
        root.mkdir(parents=True, exist_ok=True)
        logger.debug("确保模型根目录存在: %s", root)
        return root

    def resolve_path(
        self,
        webui_path: Path,
        relative_path: str | Path | None = None,
    ) -> Path:
        """解析模型根目录内路径，并拒绝越界路径

        Args:
            webui_path (Path):
                WebUI 根目录。
            relative_path (str | Path | None):
                模型根目录内的相对路径，也可以是已位于模型根目录内的绝对路径。

        Returns:
            Path:
                解析后的绝对路径。

        Raises:
            ValueError:
                路径不在模型根目录内时抛出。
        """
        root_path = self.ensure_root(webui_path)
        if relative_path is None or str(relative_path) in {"", "."}:
            candidate = root_path
        else:
            path = Path(relative_path)
            candidate = path if path.is_absolute() else root_path / path

        root = root_path.resolve()
        resolved = candidate.resolve()
        if resolved != root and not resolved.is_relative_to(root):
            logger.warning("路径越界, 拒绝访问: %s", candidate)
            raise ValueError(f"路径不在模型目录内: {candidate}")
        logger.debug("解析路径: %s -> %s", candidate, resolved)
        return resolved

    def relative_to_root(
        self,
        webui_path: Path,
        path: str | Path,
    ) -> str:
        """将模型根目录内路径转为相对路径

        Args:
            webui_path (Path):
                WebUI 根目录。
            path (str | Path):
                模型根目录内的路径。

        Returns:
            str:
                相对模型根目录的 POSIX 风格路径。
        """
        resolved = self.resolve_path(webui_path, path)
        root = self.root_path(webui_path).resolve()
        if resolved == root:
            return "."
        return resolved.relative_to(root).as_posix()

    def validate_name(
        self,
        name: str,
    ) -> str:
        """校验单个文件或文件夹名称

        Args:
            name (str):
                待校验的文件或文件夹名称。

        Returns:
            str:
                去除首尾空白后的名称。

        Raises:
            ValueError:
                名称为空、包含路径分隔符或包含空字符时抛出。
        """
        clean_name = name.strip()
        if not _is_path_name(clean_name):
            logger.warning("名称无效: %s", name)
            raise ValueError(f"名称无效: {name}")
        return clean_name

    def list_entries(
        self,
        webui_path: Path,
        relative_path: str | Path | None = None,
    ) -> list[ModelEntry]:
        """列出指定模型目录下的直接条目

        Args:
            webui_path (Path):
                WebUI 根目录。
            relative_path (str | Path | None):
                要列出的模型目录相对路径。

        Returns:
            list[ModelEntry]:
                目录下的直接文件和文件夹条目。

        Raises:
            NotADirectoryError:
                指定路径存在但不是文件夹时抛出。
        """
        path = self.resolve_path(webui_path, relative_path)
        if not path.exists():
            logger.debug("路径不存在, 返回空列表: %s", path)
            return []
        if not path.is_dir():
            logger.warning("路径不是文件夹: %s", path)
            raise NotADirectoryError(f"不是文件夹: {path}")

        logger.debug("开始扫描目录: %s", path)
        entries: list[ModelEntry] = []
        for item in path.iterdir():
            try:
                stat_result = item.stat()
                modified_time = stat_result.st_mtime
            except OSError:
                logger.warning("读取条目属性失败, 修改时间置 0: %s", item)
                modified_time = 0
            entries.append(
                ModelEntry(
                    name=item.name,
                    path=item,
                    relative_path=self.relative_to_root(webui_path, item),
                    is_dir=item.is_dir(),
                    size=_path_size(item),
                    modified_time=modified_time,
                )
            )
            logger.debug("扫描到条目: %s, is_dir=%s", item, item.is_dir())
        logger.info("目录扫描完成: %s, 共 %s 个条目", path, len(entries))
        return sorted(entries, key=lambda entry: (not entry.is_dir, entry.name.lower()))

    def list_directories(self, webui_path: Path) -> list[str]:
        """列出模型根目录内所有文件夹相对路径

        Args:
            webui_path (Path): WebUI 根目录。

        Returns:
            list[str]:
                模型根目录内所有文件夹的相对路径。
        """
        root = self.ensure_root(webui_path).resolve()
        dirs = ["."]
        logger.debug("开始扫描模型根目录: %s", root)
        for current_root, dir_names, _file_names in os.walk(root):
            current = Path(current_root)
            dir_names.sort(key=str.lower)
            for dir_name in dir_names:
                path = current / dir_name
                try:
                    relative = path.resolve().relative_to(root).as_posix()
                except ValueError:
                    logger.warning("跳过无法解析的目录: %s", path)
                    continue
                logger.debug("发现目录: %s", relative)
                dirs.append(relative)
        logger.info("目录扫描完成, 共 %s 个文件夹", len(dirs))
        return dirs

    def create_folder(
        self,
        webui_path: Path,
        parent_relative_path: str | Path | None,
        name: str,
    ) -> Path:
        """在指定目录下创建文件夹

        Args:
            webui_path (Path):
                WebUI 根目录。
            parent_relative_path (str | Path | None):
                父级模型目录相对路径。
            name (str):
                要创建的文件夹名称。

        Returns:
            Path:
                新建文件夹路径。

        Raises:
            NotADirectoryError:
                父级路径不是文件夹时抛出。
            FileExistsError:
                目标文件夹已存在时抛出。
        """
        parent = self.resolve_path(webui_path, parent_relative_path)
        if not parent.is_dir():
            logger.warning("父级路径不是文件夹: %s", parent)
            raise NotADirectoryError(f"不是文件夹: {parent}")
        target = parent / self.validate_name(name)
        if target.exists() or target.is_symlink():
            logger.warning("目标文件夹已存在: %s", target)
            raise FileExistsError(f"目标已存在: {target}")
        target.mkdir(parents=True)
        logger.info("创建文件夹: %s", target)
        return target

    def _target_path(
        self,
        webui_path: Path,
        source_path: Path,
        target_dir_relative_path: str | Path | None,
        new_name: str | None = None,
    ) -> Path:
        target_dir = self.resolve_path(webui_path, target_dir_relative_path)
        if not target_dir.is_dir():
            logger.warning("目标路径不是文件夹: %s", target_dir)
            raise NotADirectoryError(f"不是文件夹: {target_dir}")
        target_name = source_path.name if new_name is None else self.validate_name(new_name)
        target = (target_dir / target_name).resolve()
        self.resolve_path(webui_path, target)
        logger.debug("计算目标路径: %s", target)
        return target

    def _copy_to_target(
        self,
        source_path: Path,
        target_path: Path,
        overwrite: bool,
    ) -> Path:
        if target_path.exists() or target_path.is_symlink():
            if not overwrite:
                logger.warning("目标已存在且不允许覆盖: %s", target_path)
                raise FileExistsError(f"目标已存在: {target_path}")
            if source_path.is_dir() and target_path.is_dir():
                logger.debug("合并复制目录: %s -> %s", source_path, target_path)
                copy_files_merge(source_path, target_path)
                return target_path
            logger.debug("覆盖删除已有目标: %s", target_path)
            remove_files(target_path)

        copy_files(source_path, target_path)
        logger.debug("复制完成: %s -> %s", source_path, target_path)
        return target_path

    def _move_to_target(
        self,
        webui_path: Path,
        source_path: Path,
        target_path: Path,
        overwrite: bool,
    ) -> Path:
        if source_path == self.root_path(webui_path).resolve():
            logger.warning("不允许移动模型根目录: %s", source_path)
            raise ValueError("不能移动模型根目录")
        if target_path.exists() or target_path.is_symlink():
            if not overwrite:
                logger.warning("目标已存在且不允许覆盖: %s", target_path)
                raise FileExistsError(f"目标已存在: {target_path}")
            if source_path.is_dir() and target_path.is_dir():
                logger.debug("合并移动目录: %s -> %s", source_path, target_path)
                move_files_merge(source_path, target_path)
                return target_path
            logger.debug("覆盖删除已有目标: %s", target_path)
            remove_files(target_path)

        move_files(source_path, target_path)
        logger.debug("移动完成: %s -> %s", source_path, target_path)
        return target_path

    def copy_entry(
        self,
        webui_path: Path,
        source_relative_path: str | Path,
        target_dir_relative_path: str | Path | None,
        new_name: str | None = None,
        overwrite: bool = False,
    ) -> Path:
        """复制模型根目录内的条目到目标文件夹

        Args:
            webui_path (Path):
                WebUI 根目录。
            source_relative_path (str | Path):
                要复制的源条目相对路径。
            target_dir_relative_path (str | Path | None):
                目标文件夹相对路径。
            new_name (str | None):
                可选的新文件或文件夹名称。
            overwrite (bool):
                目标已存在时是否覆盖或合并。

        Returns:
            Path:
                复制后的目标路径。

        Raises:
            FileNotFoundError:
                源路径不存在时抛出。
        """
        source = self.resolve_path(webui_path, source_relative_path)
        if not source.exists() and not source.is_symlink():
            logger.warning("源路径不存在: %s", source)
            raise FileNotFoundError(f"源路径不存在: {source}")
        logger.debug("开始复制条目: %s", source)
        target = self._target_path(webui_path, source, target_dir_relative_path, new_name)
        result = self._copy_to_target(source, target, overwrite)
        logger.info("复制条目完成: %s -> %s", source, result)
        return result

    def move_entry(
        self,
        webui_path: Path,
        source_relative_path: str | Path,
        target_dir_relative_path: str | Path | None,
        new_name: str | None = None,
        overwrite: bool = False,
    ) -> Path:
        """移动模型根目录内的条目到目标文件夹

        Args:
            webui_path (Path):
                WebUI 根目录。
            source_relative_path (str | Path):
                要移动的源条目相对路径。
            target_dir_relative_path (str | Path | None):
                目标文件夹相对路径。
            new_name (str | None):
                可选的新文件或文件夹名称。
            overwrite (bool):
                目标已存在时是否覆盖或合并。

        Returns:
            Path:
                移动后的目标路径。

        Raises:
            FileNotFoundError:
                源路径不存在时抛出。
        """
        source = self.resolve_path(webui_path, source_relative_path)
        if not source.exists() and not source.is_symlink():
            logger.warning("源路径不存在: %s", source)
            raise FileNotFoundError(f"源路径不存在: {source}")
        logger.debug("开始移动条目: %s", source)
        target = self._target_path(webui_path, source, target_dir_relative_path, new_name)
        result = self._move_to_target(webui_path, source, target, overwrite)
        logger.info("移动条目完成: %s -> %s", source, result)
        return result

    def rename_entry(
        self,
        webui_path: Path,
        source_relative_path: str | Path,
        new_name: str,
        overwrite: bool = False,
    ) -> Path:
        """重命名模型根目录内的文件或文件夹

        Args:
            webui_path (Path):
                WebUI 根目录。
            source_relative_path (str | Path):
                要重命名的源条目相对路径。
            new_name (str):
                新文件或文件夹名称。
            overwrite (bool):
                同级目录中已有同名目标时是否覆盖。

        Returns:
            Path:
                重命名后的目标路径。

        Raises:
            FileNotFoundError:
                源路径不存在时抛出。
            ValueError:
                试图重命名模型根目录时抛出。
            FileExistsError:
                目标已存在且未允许覆盖时抛出。
        """
        source = self.resolve_path(webui_path, source_relative_path)
        if not source.exists() and not source.is_symlink():
            logger.warning("源路径不存在: %s", source)
            raise FileNotFoundError(f"源路径不存在: {source}")
        if source == self.root_path(webui_path).resolve():
            logger.warning("不允许重命名模型根目录: %s", source)
            raise ValueError("不能重命名模型根目录")

        target = (source.parent / self.validate_name(new_name)).resolve()
        self.resolve_path(webui_path, target)
        if source == target:
            return source

        if target.exists() or target.is_symlink():
            if not overwrite:
                logger.warning("目标已存在且不允许覆盖: %s", target)
                raise FileExistsError(f"目标已存在: {target}")
            logger.debug("覆盖删除已有目标: %s", target)
            remove_files(target)

        move_files(source, target)
        logger.info("重命名条目完成: %s -> %s", source, target)
        return target

    def delete_entry(
        self,
        webui_path: Path,
        relative_path: str | Path,
    ) -> None:
        """永久删除模型根目录内条目

        Args:
            webui_path (Path):
                WebUI 根目录。
            relative_path (str | Path):
                要删除的模型条目相对路径。

        Raises:
            ValueError:
                试图删除模型根目录时抛出。
        """
        target = self.resolve_path(webui_path, relative_path)
        if target == self.root_path(webui_path).resolve():
            logger.warning("不允许删除模型根目录: %s", target)
            raise ValueError("不能删除模型根目录")
        remove_files(target)
        logger.info("删除条目完成: %s", target)

    def import_paths(
        self,
        webui_path: Path,
        source_paths: list[Path],
        target_dir_relative_path: str | Path | None,
        overwrite: bool = False,
    ) -> list[Path]:
        """复制导入本地模型文件或文件夹

        Args:
            webui_path (Path):
                WebUI 根目录。
            source_paths (list[Path]):
                要复制导入的本地文件或文件夹路径。
            target_dir_relative_path (str | Path | None):
                模型根目录内的目标文件夹相对路径。
            overwrite (bool):
                目标已存在时是否覆盖或合并。

        Returns:
            list[Path]:
                导入后的目标路径列表。

        Raises:
            NotADirectoryError:
                目标路径不是文件夹时抛出。
            FileNotFoundError:
                任一源路径不存在时抛出。
        """
        target_dir = self.resolve_path(webui_path, target_dir_relative_path)
        if not target_dir.is_dir():
            logger.warning("目标路径不是文件夹: %s", target_dir)
            raise NotADirectoryError(f"不是文件夹: {target_dir}")

        logger.info("开始导入模型, 共 %s 个源路径", len(source_paths))
        imported: list[Path] = []
        for source in source_paths:
            source_path = Path(source).expanduser().resolve()
            if not source_path.exists() and not source_path.is_symlink():
                logger.warning("源路径不存在: %s", source_path)
                raise FileNotFoundError(f"源路径不存在: {source_path}")
            target_path = self._target_path(webui_path, source_path, target_dir)
            result = self._copy_to_target(source_path, target_path, overwrite)
            imported.append(result)
            logger.debug("导入条目完成: %s -> %s", source_path, result)
        logger.info("模型导入完成, 共 %s 个条目", len(imported))
        return imported

    def download_url(
        self,
        webui_path: Path,
        url: str,
        target_dir_relative_path: str | Path | None,
        save_name: str | None = None,
        downloader: DownloadToolType | None = None,
    ) -> Path:
        """下载模型到指定模型文件夹

        Args:
            webui_path (Path):
                WebUI 根目录。
            url (str):
                模型下载链接。
            target_dir_relative_path (str | Path | None):
                模型根目录内的目标文件夹相对路径。
            save_name (str | None):
                可选的保存文件名。
            downloader (DownloadToolType | None):
                可选的下载器名称。

        Returns:
            Path:
                下载完成后的文件路径。
        """
        target_dir = self.resolve_path(webui_path, target_dir_relative_path)
        target_dir.mkdir(parents=True, exist_ok=True)
        clean_save_name = self.validate_name(save_name) if save_name else None
        logger.info("开始下载模型到目录: %s, 保存文件名: %s", target_dir, clean_save_name)
        result = download_file(
            url=url,
            path=target_dir,
            save_name=clean_save_name,
            tool=downloader,
        )
        logger.info("模型下载完成: %s", result)
        return result
