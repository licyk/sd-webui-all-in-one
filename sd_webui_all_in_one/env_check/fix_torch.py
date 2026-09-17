"""Torch 修复工具"""

import ctypes
import shutil
import importlib.util
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def fix_torch_libomp() -> None:
    """检测并修复 PyTorch 的 libomp 问题"""
    logger.info("检测 PyTorch 的 libomp 问题")
    try:
        torch_spec = importlib.util.find_spec("torch")
        if torch_spec is None or torch_spec.submodule_search_locations is None:
            return
        for folder in torch_spec.submodule_search_locations:
            folder = Path(folder)
            lib_folder = folder / "lib"
            test_file = lib_folder / "fbgemm.dll"
            dest = lib_folder / "libomp140.x86_64.dll"
            if dest.exists():
                break

            if not test_file.is_file():
                # 非 Windows 平台或新版本 PyTorch 不包含该文件, 无需修复
                break

            with open(test_file, "rb") as f:
                contents = f.read()
                if b"libomp140.x86_64.dll" not in contents:
                    break
            try:
                _ = ctypes.cdll.LoadLibrary(test_file.as_posix())
            except FileNotFoundError:
                logger.warning("检测到 PyTorch 版本存在 libomp 问题, 进行修复")
                shutil.copyfile(lib_folder / "libiomp5md.dll", dest)
    except (ImportError, ValueError) as e:
        # find_spec 在 torch 包损坏时可能抛出异常
        logger.warning("查找 PyTorch 安装位置失败, 跳过 libomp 问题检测: %s", e)
    except OSError as e:
        logger.warning("检测或修复 PyTorch 的 libomp 问题时发生错误: %s", e)
