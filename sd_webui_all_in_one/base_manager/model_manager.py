"""WebUI 模型管理服务"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

from sd_webui_all_in_one.downloader import DownloadToolType, download_file
from sd_webui_all_in_one.file_manager import copy_files, copy_files_merge, move_files, move_files_merge, remove_files


WebUiModelType: TypeAlias = Literal[
    "sd_webui",
    "comfyui",
    "fooocus",
    "sd_trainer",
    "sd_scripts",
    "invokeai",
]
"""支持模型管理的 WebUI 类型"""


FileWebUiModelType: TypeAlias = Literal[
    "sd_webui",
    "comfyui",
    "fooocus",
    "sd_trainer",
    "sd_scripts",
]
"""按文件夹管理模型的 WebUI 类型"""


FILE_MODEL_ROOT_DIRS: dict[FileWebUiModelType, str] = {
    "sd_webui": "models",
    "comfyui": "models",
    "fooocus": "models",
    "sd_trainer": "sd-models",
    "sd_scripts": "sd-models",
}
"""各 WebUI 模型根目录名"""


WEBUI_MODEL_TITLES: dict[WebUiModelType, str] = {
    "sd_webui": "Stable Diffusion WebUI",
    "comfyui": "ComfyUI",
    "fooocus": "Fooocus",
    "sd_trainer": "SD Trainer",
    "sd_scripts": "SD Scripts",
    "invokeai": "InvokeAI",
}
"""模型管理窗口默认标题"""


@dataclass(frozen=True, slots=True)
class ModelRoot:
    """WebUI 模型根目录信息"""

    webui_type: WebUiModelType
    webui_path: Path
    root_path: Path


@dataclass(frozen=True, slots=True)
class ModelEntry:
    """模型目录中的一个条目"""

    name: str
    path: Path
    relative_path: str
    is_dir: bool
    size: int
    modified_time: float


def _is_path_name(value: str) -> bool:
    return value not in {"", ".", ".."} and "\x00" not in value and "/" not in value and "\\" not in value


def _path_size(path: Path) -> int:
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    return 0


class FileModelManager:
    """基于 WebUI 模型目录的文件管理器"""

    def __init__(
        self,
        webui_type: FileWebUiModelType,
        webui_path: Path,
    ) -> None:
        if webui_type not in FILE_MODEL_ROOT_DIRS:
            raise ValueError(f"不支持按文件夹管理模型的 WebUI 类型: {webui_type}")
        self.webui_type = webui_type
        self.webui_path = Path(webui_path)
        self.root = ModelRoot(
            webui_type=webui_type,
            webui_path=self.webui_path,
            root_path=self.webui_path / FILE_MODEL_ROOT_DIRS[webui_type],
        )

    @property
    def root_path(self) -> Path:
        """模型根目录

        Returns:
            Path:
                WebUI 模型根目录。
        """
        return self.root.root_path

    def ensure_root(self) -> Path:
        """确保模型根目录存在并返回路径

        Returns:
            Path:
                已创建或已存在的模型根目录。
        """
        self.root_path.mkdir(parents=True, exist_ok=True)
        return self.root_path

    def resolve_path(
        self,
        relative_path: str | Path | None = None,
    ) -> Path:
        """解析模型根目录内路径，并拒绝越界路径

        Args:
            relative_path (str | Path | None):
                模型根目录内的相对路径，也可以是已位于模型根目录内的绝对路径。

        Returns:
            Path:
                解析后的绝对路径。

        Raises:
            ValueError:
                路径不在模型根目录内时抛出。
        """
        self.ensure_root()
        if relative_path is None or str(relative_path) in {"", "."}:
            candidate = self.root_path
        else:
            path = Path(relative_path)
            candidate = path if path.is_absolute() else self.root_path / path

        root = self.root_path.resolve()
        resolved = candidate.resolve()
        if resolved != root and not resolved.is_relative_to(root):
            raise ValueError(f"路径不在模型目录内: {candidate}")
        return resolved

    def relative_to_root(
        self,
        path: str | Path,
    ) -> str:
        """将模型根目录内路径转为相对路径

        Args:
            path (str | Path):
                模型根目录内的路径。

        Returns:
            str:
                相对模型根目录的 POSIX 风格路径。
        """
        resolved = self.resolve_path(path)
        root = self.root_path.resolve()
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
            raise ValueError(f"名称无效: {name}")
        return clean_name

    def list_entries(
        self,
        relative_path: str | Path | None = None,
    ) -> list[ModelEntry]:
        """列出指定模型目录下的直接条目

        Args:
            relative_path (str | Path | None):
                要列出的模型目录相对路径。

        Returns:
            list[ModelEntry]:
                目录下的直接文件和文件夹条目。

        Raises:
            NotADirectoryError:
                指定路径存在但不是文件夹时抛出。
        """
        path = self.resolve_path(relative_path)
        if not path.exists():
            return []
        if not path.is_dir():
            raise NotADirectoryError(f"不是文件夹: {path}")

        entries: list[ModelEntry] = []
        for item in path.iterdir():
            try:
                stat_result = item.stat()
                modified_time = stat_result.st_mtime
            except OSError:
                modified_time = 0
            entries.append(
                ModelEntry(
                    name=item.name,
                    path=item,
                    relative_path=self.relative_to_root(item),
                    is_dir=item.is_dir(),
                    size=_path_size(item),
                    modified_time=modified_time,
                )
            )
        return sorted(entries, key=lambda entry: (not entry.is_dir, entry.name.lower()))

    def list_directories(self) -> list[str]:
        """列出模型根目录内所有文件夹相对路径

        Returns:
            list[str]:
                模型根目录内所有文件夹的相对路径。
        """
        root = self.ensure_root().resolve()
        dirs = ["."]
        for current_root, dir_names, _file_names in os.walk(root):
            current = Path(current_root)
            dir_names.sort(key=str.lower)
            for dir_name in dir_names:
                path = current / dir_name
                try:
                    relative = path.resolve().relative_to(root).as_posix()
                except ValueError:
                    continue
                dirs.append(relative)
        return dirs

    def create_folder(
        self,
        parent_relative_path: str | Path | None,
        name: str,
    ) -> Path:
        """在指定目录下创建文件夹

        Args:
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
        parent = self.resolve_path(parent_relative_path)
        if not parent.is_dir():
            raise NotADirectoryError(f"不是文件夹: {parent}")
        target = parent / self.validate_name(name)
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"目标已存在: {target}")
        target.mkdir(parents=True)
        return target

    def _target_path(
        self,
        source_path: Path,
        target_dir_relative_path: str | Path | None,
        new_name: str | None = None,
    ) -> Path:
        target_dir = self.resolve_path(target_dir_relative_path)
        if not target_dir.is_dir():
            raise NotADirectoryError(f"不是文件夹: {target_dir}")
        target_name = source_path.name if new_name is None else self.validate_name(new_name)
        target = (target_dir / target_name).resolve()
        self.resolve_path(target)
        return target

    def _copy_to_target(
        self,
        source_path: Path,
        target_path: Path,
        overwrite: bool,
    ) -> Path:
        if target_path.exists() or target_path.is_symlink():
            if not overwrite:
                raise FileExistsError(f"目标已存在: {target_path}")
            if source_path.is_dir() and target_path.is_dir():
                copy_files_merge(source_path, target_path)
                return target_path
            remove_files(target_path)

        copy_files(source_path, target_path)
        return target_path

    def _move_to_target(
        self,
        source_path: Path,
        target_path: Path,
        overwrite: bool,
    ) -> Path:
        if source_path == self.root_path.resolve():
            raise ValueError("不能移动模型根目录")
        if target_path.exists() or target_path.is_symlink():
            if not overwrite:
                raise FileExistsError(f"目标已存在: {target_path}")
            if source_path.is_dir() and target_path.is_dir():
                move_files_merge(source_path, target_path)
                return target_path
            remove_files(target_path)

        move_files(source_path, target_path)
        return target_path

    def copy_entry(
        self,
        source_relative_path: str | Path,
        target_dir_relative_path: str | Path | None,
        new_name: str | None = None,
        overwrite: bool = False,
    ) -> Path:
        """复制模型根目录内的条目到目标文件夹

        Args:
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
        source = self.resolve_path(source_relative_path)
        if not source.exists() and not source.is_symlink():
            raise FileNotFoundError(f"源路径不存在: {source}")
        target = self._target_path(source, target_dir_relative_path, new_name)
        return self._copy_to_target(source, target, overwrite)

    def move_entry(
        self,
        source_relative_path: str | Path,
        target_dir_relative_path: str | Path | None,
        new_name: str | None = None,
        overwrite: bool = False,
    ) -> Path:
        """移动模型根目录内的条目到目标文件夹

        Args:
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
        source = self.resolve_path(source_relative_path)
        if not source.exists() and not source.is_symlink():
            raise FileNotFoundError(f"源路径不存在: {source}")
        target = self._target_path(source, target_dir_relative_path, new_name)
        return self._move_to_target(source, target, overwrite)

    def delete_entry(
        self,
        relative_path: str | Path,
    ) -> None:
        """永久删除模型根目录内条目

        Args:
            relative_path (str | Path):
                要删除的模型条目相对路径。

        Raises:
            ValueError:
                试图删除模型根目录时抛出。
        """
        target = self.resolve_path(relative_path)
        if target == self.root_path.resolve():
            raise ValueError("不能删除模型根目录")
        remove_files(target)

    def import_paths(
        self,
        source_paths: list[Path],
        target_dir_relative_path: str | Path | None,
        overwrite: bool = False,
    ) -> list[Path]:
        """复制导入本地模型文件或文件夹

        Args:
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
        target_dir = self.resolve_path(target_dir_relative_path)
        if not target_dir.is_dir():
            raise NotADirectoryError(f"不是文件夹: {target_dir}")

        imported: list[Path] = []
        for source in source_paths:
            source_path = Path(source).expanduser().resolve()
            if not source_path.exists() and not source_path.is_symlink():
                raise FileNotFoundError(f"源路径不存在: {source_path}")
            target_path = self._target_path(source_path, target_dir)
            imported.append(self._copy_to_target(source_path, target_path, overwrite))
        return imported

    def download_url(
        self,
        url: str,
        target_dir_relative_path: str | Path | None,
        save_name: str | None = None,
        downloader: DownloadToolType | None = None,
    ) -> Path:
        """下载模型到指定模型文件夹

        Args:
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
        target_dir = self.resolve_path(target_dir_relative_path)
        target_dir.mkdir(parents=True, exist_ok=True)
        clean_save_name = self.validate_name(save_name) if save_name else None
        return download_file(
            url=url,
            path=target_dir,
            save_name=clean_save_name,
            tool=downloader,
        )


class InvokeAIModelManager:
    """InvokeAI 专用模型管理器"""

    def __init__(
        self,
        invokeai_path: Path,
    ) -> None:
        self.invokeai_path = Path(invokeai_path)

    @property
    def import_cache_path(self) -> Path:
        """复制导入本地模型时使用的安全暂存目录

        Returns:
            Path:
                InvokeAI 本地导入暂存目录。
        """
        return self.invokeai_path / "models" / "_imports"

    def list_models(self):
        """列出 InvokeAI 已注册模型

        Returns:
            list[dict[str, Any]]:
                InvokeAI 已注册模型信息列表。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import get_invokeai_model_list

        return get_invokeai_model_list(invokeai_path=self.invokeai_path)

    def install_from_url(
        self,
        url: str,
    ) -> bool:
        """通过 InvokeAI 模型管理器从 URL 安装模型

        Args:
            url (str):
                模型下载链接或 InvokeAI 支持的模型源。

        Returns:
            bool:
                安装成功时返回 True。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import install_invokeai_model_from_source

        return install_invokeai_model_from_source(invokeai_path=self.invokeai_path, source=url)

    def import_local_paths(
        self,
        source_paths: list[Path],
    ) -> bool:
        """复制本地模型后交给 InvokeAI 注册，保证源文件不被移动

        Args:
            source_paths (list[Path]):
                要导入的本地模型文件或文件夹路径。

        Returns:
            bool:
                InvokeAI 注册成功时返回 True。

        Raises:
            FileNotFoundError:
                任一源路径不存在时抛出。
            FileExistsError:
                导入暂存目录中已有同名目标时抛出。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import import_model_to_invokeai

        self.import_cache_path.mkdir(parents=True, exist_ok=True)
        copied_paths: list[Path] = []
        for source in source_paths:
            source_path = Path(source).expanduser().resolve()
            if not source_path.exists() and not source_path.is_symlink():
                raise FileNotFoundError(f"源路径不存在: {source_path}")
            target = self.import_cache_path / source_path.name
            if target.exists() or target.is_symlink():
                raise FileExistsError(f"InvokeAI 导入暂存路径已存在: {target}")
            copy_files(source_path, target)
            copied_paths.append(target)

        return import_model_to_invokeai(
            model_list=copied_paths,
            install_model_to_local=False,
            invokeai_path=self.invokeai_path,
        )

    def unregister(
        self,
        model_id: str,
    ) -> bool:
        """按 InvokeAI 默认删除语义移除模型

        Args:
            model_id (str):
                InvokeAI 模型 ID。

        Returns:
            bool:
                移除成功时返回 True。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import uninstall_model_from_invokeai

        return uninstall_model_from_invokeai(
            model_identifiers=[model_id],
            delete_files=True,
            invokeai_path=self.invokeai_path,
        )

    def delete(
        self,
        model_id: str,
    ) -> bool:
        """删除模型记录，并让 InvokeAI 决定是否删除模型文件

        Args:
            model_id (str):
                InvokeAI 模型 ID。

        Returns:
            bool:
                删除成功时返回 True。
        """
        from sd_webui_all_in_one.base_manager.invokeai_base import uninstall_model_from_invokeai

        return uninstall_model_from_invokeai(
            model_identifiers=[model_id],
            delete_files=True,
            invokeai_path=self.invokeai_path,
        )


def launch_model_manager_gui(
    webui_type: WebUiModelType,
    webui_path: Path,
    title: str | None = None,
) -> None:
    """启动模型管理 GUI

    Args:
        webui_type (WebUiModelType):
            要管理模型的 WebUI 类型。
        webui_path (Path):
            WebUI 根目录路径。
        title (str | None):
            可选的窗口标题。

    Raises:
        RuntimeError:
            tkinter 不可用或 GUI 模块导入失败时抛出。
    """
    try:
        from sd_webui_all_in_one.base_manager.gui.model_manager_gui import launch_model_manager_gui as _launch_model_manager_gui
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动模型管理 GUI") from e
        raise RuntimeError(f"导入 GUI 管理模块发生错误: {e}") from e

    _launch_model_manager_gui(
        webui_type=webui_type,
        webui_path=webui_path,
        title=title or WEBUI_MODEL_TITLES[webui_type],
    )


def launch_sd_webui_model_manager_gui(sd_webui_path: Path) -> None:
    """启动 Stable Diffusion WebUI 模型管理 GUI

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录路径。
    """
    launch_model_manager_gui("sd_webui", sd_webui_path)


def launch_comfyui_model_manager_gui(comfyui_path: Path) -> None:
    """启动 ComfyUI 模型管理 GUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录路径。
    """
    launch_model_manager_gui("comfyui", comfyui_path)


def launch_fooocus_model_manager_gui(fooocus_path: Path) -> None:
    """启动 Fooocus 模型管理 GUI

    Args:
        fooocus_path (Path):
            Fooocus 根目录路径。
    """
    launch_model_manager_gui("fooocus", fooocus_path)


def launch_sd_trainer_model_manager_gui(sd_trainer_path: Path) -> None:
    """启动 SD Trainer 模型管理 GUI

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录路径。
    """
    launch_model_manager_gui("sd_trainer", sd_trainer_path)


def launch_sd_scripts_model_manager_gui(sd_scripts_path: Path) -> None:
    """启动 SD Scripts 模型管理 GUI

    Args:
        sd_scripts_path (Path):
            SD Scripts 根目录路径。
    """
    launch_model_manager_gui("sd_scripts", sd_scripts_path)


def launch_invokeai_model_manager_gui(invokeai_path: Path) -> None:
    """启动 InvokeAI 模型管理 GUI

    Args:
        invokeai_path (Path):
            InvokeAI 根目录路径。
    """
    launch_model_manager_gui("invokeai", invokeai_path)
