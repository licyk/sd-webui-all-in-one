"""更新工具"""

import importlib.metadata
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

from sd_webui_all_in_one.mirror_manager import get_pypi_mirror_config
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.package_analyzer.py_ver_cmp import PyWhlVersionComparison
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    UV_MINIMUM_VER,
    PIP_MINIMUM_VER,
    ARIA2_MINIMUM_VER,
    LOGGER_NAME,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def network_gfw_test(
    timeout: int | None = 3,
) -> bool:
    """检查当前网络环境是否被 GFW 阻挡

    Args:
        timeout (int | None):
            超时时间设置

    Returns:
        bool:
            当未被阻挡时则返回 True
    """
    try:
        proxy_support = urllib.request.ProxyHandler()
        opener = urllib.request.build_opener(proxy_support)
        urllib.request.install_opener(opener)
        with urllib.request.urlopen("https://www.google.com", timeout=timeout) as response:
            if response.status == 200:
                logger.debug("测试链接正常访问")
                return True
            else:
                logger.debug("测试链接访问失败: %s", response.status)
                return False
    except urllib.error.HTTPError as e:
        logger.debug("测试链接访问失败 (HTTPError): %s", e.code)
        return False
    except urllib.error.URLError as e:
        logger.debug("测试链接访问失败 (URLError): %s", e.reason)
        return False
    except Exception as e:
        logger.debug("测试链接访问失败: %s", e)
        return False


def check_and_update_uv(
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查 uv 版本并尝试更新

    Args:
        custom_env (dict[str, str] | None):
            自定义环境变量

    Raises:
        RuntimeError:
            更新 uv 发生错误时
    """
    try:
        ver = importlib.metadata.version("uv")
        if PyWhlVersionComparison(ver) >= PyWhlVersionComparison(UV_MINIMUM_VER):
            return
        logger.info("更新 uv 中")
    except Exception:
        logger.info("安装 uv 中")

    try:
        custom_env = get_auto_pypi_mirror_config(custom_env)
        run_cmd(
            [Path(sys.executable).as_posix(), "-m", "pip", "install", "uv", "--upgrade"],
            custom_env=custom_env,
        )
        logger.info("uv 更新完成")
    except RuntimeError as e:
        raise RuntimeError(f"更新 uv 时发生错误: {e}") from e


def check_and_update_pip(
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查 Pip 版本并尝试更新

    Args:
        custom_env (dict[str, str] | None):
            自定义环境变量

    Raises:
        RuntimeError:
            更新 Pip 发生错误时
    """
    try:
        ver = importlib.metadata.version("pip")
        if PyWhlVersionComparison(ver) >= PyWhlVersionComparison(PIP_MINIMUM_VER):
            return
        logger.info("更新 Pip 中")
    except Exception:
        logger.info("安装 Pip 中")
        try:
            run_cmd([Path(sys.executable).as_posix(), "-m", "ensurepip"])
        except RuntimeError as e:
            raise RuntimeError(f"安装 Pip 时发生错误: {e}") from e

    try:
        custom_env = get_auto_pypi_mirror_config(custom_env)
        run_cmd(
            [Path(sys.executable).as_posix(), "-m", "pip", "install", "pip", "--upgrade"],
            custom_env=custom_env,
        )
        logger.info("Pip 更新完成")
    except RuntimeError as e:
        raise RuntimeError(f"更新 Pip 时发生错误: {e}") from e


def get_aria2_ver() -> str | None:
    """获取 Aria2 版本

    Returns:
        (str | None):
            Aria2 版本号
    """
    try:
        aria2_output = run_cmd(["aria2c", "--version"], live=False).strip().splitlines()
    except RuntimeError:
        return None

    for text in aria2_output:
        version_match = re.search(r"aria2 version (\d+\.\d+\.\d+)", text)
        if version_match:
            return version_match.group(1)

    return None


def check_aria2_version() -> bool:
    """检查 Aria2 是否需要更新

    Returns:
        bool:
            当 Aria2 需要更新时则返回 True
    """
    try:
        ver = get_aria2_ver()
        if ver is None:
            raise Exception()
        if PyWhlVersionComparison(ver) >= PyWhlVersionComparison(ARIA2_MINIMUM_VER):
            return False
    except Exception:
        return True


def get_auto_pypi_mirror_config(
    custom_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """为安装 Pip 和 uv 配置所需的镜像源

    Args:
        custom_env (dict[str, str] | None):
            原始的环境变量

    Returns:
        (dict[str, str]):
            配置 PyPI 镜像源后的环境变量
    """
    if network_gfw_test():
        return get_pypi_mirror_config(
            use_cn_mirror=False,
            origin_env=custom_env,
        )
    else:
        return get_pypi_mirror_config(
            use_cn_mirror=True,
            origin_env=custom_env,
        )
