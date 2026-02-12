"""Torch 修复工具"""

import ctypes
import shutil
import importlib.util
from pathlib import Path
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, LOGGER_NAME


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
        for folder in torch_spec.submodule_search_locations:
            folder = Path(folder)
            lib_folder = folder / "lib"
            test_file = lib_folder / "fbgemm.dll"
            dest = lib_folder / "libomp140.x86_64.dll"
            if dest.exists():
                break

            with open(test_file, "rb") as f:
                contents = f.read()
                if b"libomp140.x86_64.dll" not in contents:
                    break
            try:
                _ = ctypes.cdll.LoadLibrary(test_file)
            except FileNotFoundError:
                logger.warning("检测到 PyTorch 版本存在 libomp 问题, 进行修复")
                shutil.copyfile(lib_folder / "libiomp5md.dll", dest)
    except Exception:
        pass
