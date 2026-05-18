"""TC Malloc 内存优化配置工具"""

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.colab_tools import is_colab_environment
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
    ROOT_PATH,
)
from sd_webui_all_in_one.package_analyzer import CommonVersionComparison


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


GLIBC_PTHREAD_MERGED_VERSION = "2.34"
TCMALLOC_LIB_PATTERNS = (
    r"libtcmalloc(_minimal|)\.so\.\d+",
    r"libtcmalloc\.so\.\d+",
)


@dataclass(frozen=True)
class TCMallocInfo:
    """可用 TCMalloc 配置信息"""

    path: str
    ld_preload: str


def get_glibc_version() -> str | None:
    """获取 glibc 版本

    Returns:
        str | None: glibc 版本, 无法获取时返回 None
    """
    try:
        result = subprocess.run(
            ["ldd", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            errors="ignore",
            check=True,
        ).stdout
        libc_ver_line = result.splitlines()[0]
        libc_ver = re.search(r"(\d+\.\d+)", libc_ver_line)
        if libc_ver:
            version = libc_ver.group(1)
            logger.info("glibc 版本: %s", version)
            return version

        logger.error("无法确定 glibc 版本")
    except Exception as e:
        logger.error("检查 glibc 版本时出错: %s", e)
    return None


def get_ldconfig_libraries() -> list[str]:
    """获取 ldconfig 缓存中的动态库信息

    Returns:
        list[str]: ldconfig 输出行列表
    """
    result = subprocess.run(
        ["ldconfig", "-p"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        text=True,
        errors="ignore",
        check=True,
        env=dict(os.environ, PATH="/usr/sbin:" + (os.getenv("PATH") or "")),
    ).stdout
    return result.splitlines()


def parse_ldconfig_library(lib: str) -> tuple[str, str] | None:
    """解析 ldconfig 库信息

    Args:
        lib (str): ldconfig 输出行

    Returns:
        tuple[str, str] | None: 库名和库路径
    """
    match = re.search(r"(.+?)\s+=>\s+(.+)", lib)
    if match is None:
        return None
    return match.group(1).strip(), match.group(2).strip()


def get_tcmalloc_candidates() -> list[tuple[str, str]]:
    """获取 ldconfig 缓存中的 TCMalloc 候选库

    Returns:
        list[tuple[str, str]]: 候选库名和路径列表
    """
    try:
        libraries = get_ldconfig_libraries()
    except Exception as e:
        logger.error("检查 TCMalloc 库时出错: %s", e)
        return []

    candidates: list[tuple[str, str]] = []
    seen_paths: set[str] = set()
    for lib_pattern in TCMALLOC_LIB_PATTERNS:
        for lib in libraries:
            if not re.search(lib_pattern, lib):
                continue

            parsed = parse_ldconfig_library(lib)
            if parsed is None:
                continue

            lib_name, lib_path = parsed
            if lib_path in seen_paths:
                continue

            seen_paths.add(lib_path)
            candidates.append((lib_name, lib_path))
    return candidates


def tcmalloc_links_libpthread(lib_path: str) -> bool:
    """检查 TCMalloc 库是否链接 libpthread

    Args:
        lib_path (str): TCMalloc 库路径

    Returns:
        bool: 链接 libpthread 时返回 True
    """
    try:
        ldd_result = subprocess.run(
            ["ldd", lib_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            text=True,
            errors="ignore",
            check=True,
        ).stdout
    except Exception as e:
        logger.error("检查 %s 链接库时出错: %s", lib_path, e)
        return False

    return "libpthread" in ldd_result


def get_common_tcmalloc_path() -> str | None:
    """获取当前系统可用的 TCMalloc 库路径

    Returns:
        str | None: TCMalloc 库路径, 无可用库时返回 None
    """
    libc_ver = get_glibc_version()
    if libc_ver is None:
        return None

    for lib_name, lib_path in get_tcmalloc_candidates():
        logger.info("检查 TCMalloc: %s => %s", lib_name, lib_path)

        if CommonVersionComparison(libc_ver) < CommonVersionComparison(GLIBC_PTHREAD_MERGED_VERSION):
            if tcmalloc_links_libpthread(lib_path):
                logger.info(
                    "%s 链接到 libpthread, 可用于 LD_PRELOAD=%s",
                    lib_name,
                    lib_path,
                )
                return lib_path

            logger.info(
                "%s 没有链接到 libpthread, 将触发未定义符号: pthread_key_create 错误",
                lib_name,
            )
            continue

        logger.info(
            "%s 链接到 libc.so, 可用于 LD_PRELOAD=%s",
            lib_name,
            lib_path,
        )
        return lib_path

    logger.warning("无法定位 TCMalloc。未在系统上找到可用的 tcmalloc 或 google-perftool, 取消加载内存优化")
    return None


def get_colab_tcmalloc_path() -> str:
    """获取 Colab 环境使用的 TCMalloc 库路径

    Returns:
        str: Colab TCMalloc 库路径
    """
    return (ROOT_PATH / "optimize" / "libtcmalloc_minimal.so.4").as_posix()


def get_tcmalloc_path() -> str | None:
    """获取当前环境可用的 TCMalloc 库路径

    Returns:
        str | None: TCMalloc 库路径, 无可用库时返回 None
    """
    if is_colab_environment():
        return get_colab_tcmalloc_path()
    return get_common_tcmalloc_path()


def apply_tcmalloc_preload(
    path: str | Path,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """配置 LD_PRELOAD 环境变量

    Args:
        path (str | Path):
            TCMalloc 库路径
        origin_env (dict[str, str] | None):
            原始的环境变量字典

    Returns:
        dict[str, str]: 追加 LD_PRELOAD 后的环境变量字典
    """
    if origin_env is None:
        custom_env = os.environ.copy()
    else:
        custom_env = origin_env.copy()

    tcmalloc_path = Path(path).as_posix()
    if "LD_PRELOAD" in custom_env and custom_env["LD_PRELOAD"]:
        custom_env["LD_PRELOAD"] = custom_env["LD_PRELOAD"] + ":" + tcmalloc_path
    else:
        custom_env["LD_PRELOAD"] = tcmalloc_path

    return custom_env


def get_tcmalloc_info(
    origin_env: dict[str, str] | None = None,
) -> TCMallocInfo | None:
    """获取当前环境可用的 TCMalloc 配置信息

    Args:
        origin_env (dict[str, str] | None):
            原始的环境变量字典

    Returns:
        TCMallocInfo | None: TCMalloc 配置信息, 无可用库时返回 None
    """
    path = get_tcmalloc_path()
    if path is None:
        return None

    custom_env = apply_tcmalloc_preload(
        path=path,
        origin_env=origin_env,
    )
    return TCMallocInfo(
        path=path,
        ld_preload=custom_env["LD_PRELOAD"],
    )


def get_tcmalloc_var(
    origin_env: dict[str, str] | None = None,
) -> str | None:
    """获取用于配置 LD_PRELOAD 环境变量的 TCMalloc 配置

    Args:
        origin_env (dict[str, str] | None):
            原始的环境变量字典

    Returns:
        str | None: LD_PRELOAD 配置, 无可用库时返回 None
    """
    info = get_tcmalloc_info(origin_env=origin_env)
    if info is None:
        return None
    return info.ld_preload


def set_tcmalloc() -> bool:
    """配置 TCMalloc 内存优化, 通过 LD_PRELOAD 环境变量指定 TCMalloc

    Returns:
        bool: 配置成功时返回 True
    """
    info = get_tcmalloc_info(origin_env=os.environ.copy())
    if info is None:
        logger.error("配置 TCMalloc 内存优化失败")
        return False

    os.environ.update(
        apply_tcmalloc_preload(
            path=info.path,
            origin_env=os.environ.copy(),
        )
    )
    logger.info("TCMalloc 内存优化配置完成")
    return True


class TCMalloc:
    """TCMalloc 配置工具

    Attributes:
        workspace (str | Path): 工作区路径
        tcmalloc_has_configure (bool): TCMalloc 配置状态
    """

    def __init__(
        self,
        workspace: str | Path,
    ) -> None:
        """TCMalloc 配置工具初始化

        Args:
            workspace (str | Path): 工作区路径
        """
        self.workspace = Path(workspace)
        self.tcmalloc_has_configure = False

    def configure_tcmalloc_common(self) -> bool:
        """使用 TCMalloc 优化内存的占用, 通过 LD_PRELOAD 环境变量指定 TCMalloc

        Returns:
            bool:
                配置成功时返回 True
        """
        path = get_common_tcmalloc_path()
        if path is None:
            return False

        os.environ.update(
            apply_tcmalloc_preload(
                path=path,
                origin_env=os.environ.copy(),
            )
        )
        return True

    def configure_tcmalloc_colab(self) -> bool:
        """配置 TCMalloc (Colab)

        Returns:
            bool: TCMalloc (Colab) 配置结果
        """
        logger.info("配置 TCMalloc 内存优化")
        os.environ.update(
            apply_tcmalloc_preload(
                path=get_colab_tcmalloc_path(),
                origin_env=os.environ.copy(),
            )
        )
        return True

    def configure_tcmalloc(self) -> bool:
        """配置 TCMalloc

        Returns:
            bool: TCMalloc 配置结果
        """
        if self.tcmalloc_has_configure:
            logger.info("TCMalloc 内存优化已配置")
            return True

        if is_colab_environment():
            status = self.configure_tcmalloc_colab()
        else:
            status = self.configure_tcmalloc_common()

        if not status:
            logger.error("配置 TCMalloc 内存优化失败")
            return False

        logger.info("TCMalloc 内存优化配置完成")
        self.tcmalloc_has_configure = True
        return True
