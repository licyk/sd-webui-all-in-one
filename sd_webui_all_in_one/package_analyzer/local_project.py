"""本地项目目录的静态元数据读取

在不执行任何构建代码的前提下, 从 ``pyproject.toml`` / ``setup.cfg`` 中读取本地项目的软件包名.

参考:
    - https://packaging.python.org/en/latest/specifications/pyproject-toml/
"""

from __future__ import annotations

import configparser
import os
import sys
from pathlib import Path
from urllib.parse import unquote

if sys.version_info >= (3, 11):
    import tomllib
else:
    from sd_webui_all_in_one import toml_parser as tomllib

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.package_analyzer.names import is_valid_name


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def file_url_path_to_local_path(
    path: str,
    windows: bool | None = None,
) -> str:
    """将 ``file:`` URL 的路径部分转换为本地文件系统路径

    Args:
        path (str):
            URL 的路径部分, 可包含百分号转义
        windows (bool | None):
            是否按 Windows 路径规则转换, 为 ``None`` 时根据当前系统判断

    Returns:
        str: 本地文件系统路径
    """
    local_path = unquote(path)
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return local_path

    # ``/C:/dir`` 与旧式 ``/C|/dir`` 均表示盘符路径, 需要去掉前导斜杠
    if len(local_path) >= 3 and local_path[0] == "/" and local_path[1].isalpha() and local_path[2] in ":|":
        local_path = local_path[1:]
    if len(local_path) >= 2 and local_path[0].isalpha() and local_path[1] == "|":
        local_path = f"{local_path[0]}:{local_path[2:]}"
    return local_path.replace("/", "\\")


def is_installable_dir(
    path: Path,
) -> bool:
    """判断目录是否为可安装的 Python 项目 (包含 ``pyproject.toml`` 或 ``setup.py``)

    Args:
        path (Path):
            目录路径

    Returns:
        bool: 目录可安装时返回 ``True``
    """
    return path.is_dir() and ((path / "pyproject.toml").is_file() or (path / "setup.py").is_file())


def _read_pyproject_name(
    path: Path,
) -> str | None:
    """从 ``pyproject.toml`` 的 ``[project]`` 表读取静态声明的软件包名

    Args:
        path (Path):
            ``pyproject.toml`` 文件路径

    Returns:
        str | None: 软件包名. 文件无法解析, 未声明 ``[project].name`` 或名称为动态字段时为 ``None``
    """
    try:
        with open(path, "rb") as file:
            data = tomllib.load(file)
    except (OSError, ValueError) as e:
        # tomllib.TOMLDecodeError 与项目自带解析器的 TomlDecodeError 均为 ValueError 的子类
        logger.debug("读取 '%s' 失败, 无法确定本地项目的软件包名: %s", path, e)
        return None

    project = data.get("project")
    if not isinstance(project, dict):
        return None
    dynamic = project.get("dynamic")
    if isinstance(dynamic, list) and "name" in dynamic:
        return None
    name = project.get("name")
    return name if isinstance(name, str) else None


def _read_setup_cfg_name(
    path: Path,
) -> str | None:
    """从 ``setup.cfg`` 的 ``[metadata]`` 段读取静态声明的软件包名

    Args:
        path (Path):
            ``setup.cfg`` 文件路径

    Returns:
        str | None: 软件包名. 文件无法解析, 未声明名称或名称为 ``attr:`` / ``file:`` 指令时为 ``None``
    """
    parser = configparser.ConfigParser(interpolation=None)
    try:
        with open(path, "r", encoding="utf-8") as file:
            parser.read_file(file)
    except (OSError, UnicodeDecodeError, configparser.Error) as e:
        logger.debug("读取 '%s' 失败, 无法确定本地项目的软件包名: %s", path, e)
        return None

    name = parser.get("metadata", "name", fallback=None)
    if name is None:
        return None
    name = name.strip()
    if name.startswith(("attr:", "file:")):
        return None
    return name


def get_local_project_name(
    path: Path,
) -> str | None:
    """获取本地项目目录声明的软件包名

    依次读取 ``pyproject.toml`` 的 ``[project].name`` 与 ``setup.cfg`` 的 ``[metadata].name``.
    只读取静态元数据, 不会执行 ``setup.py`` 或构建后端.

    Args:
        path (Path):
            本地项目目录

    Returns:
        str | None: 软件包名, 无法静态确定时为 ``None``
    """
    for filename, reader in (("pyproject.toml", _read_pyproject_name), ("setup.cfg", _read_setup_cfg_name)):
        candidate = path / filename
        if not candidate.is_file():
            continue
        name = reader(candidate)
        if name and is_valid_name(name):
            return name
    return None
