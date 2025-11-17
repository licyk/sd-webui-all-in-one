"""TC Malloc 内存优化配置工具"""

import os
import re
import subprocess
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.downloader import download_file
from sd_webui_all_in_one.colab_tools import is_colab_environment
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.package_analyzer.ver_cmp import CommonVersionComparison


logger = get_logger(
    name="TC Malloc",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class TCMalloc:
    """TCMalloc 配置工具

    Attributes:
        workspace (str | Path): 工作区路径
        tcmalloc_has_configure (bool): TCMalloc 配置状态
    """

    def __init__(self, workspace: str | Path) -> None:
        """TCMalloc 配置工具初始化

        Args:
            workspace (str | Path): 工作区路径
        """
        self.workspace = Path(workspace)
        self.tcmalloc_has_configure = False

    def configure_tcmalloc_common(self) -> bool:
        """使用 TCMalloc 优化内存的占用, 通过 LD_PRELOAD 环境变量指定 TCMalloc

        Args:
            bool: 配置成功时返回`True`
        """
        # 检查 glibc 版本
        try:
            result = subprocess.run(["ldd", "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            libc_ver_line = result.stdout.split("\n")[0]
            libc_ver = re.search(r"(\d+\.\d+)", libc_ver_line)
            if libc_ver:
                libc_ver = libc_ver.group(1)
                logger.info("glibc 版本: %s", libc_ver)
            else:
                logger.error("无法确定 glibc 版本")
                return False
        except Exception as e:
            logger.error("检查 glibc 版本时出错: %s", e)
            return False

        # 从 2.34 开始, libpthread 已经集成到 libc.so 中
        libc_v234 = "2.34"

        # 定义 Tcmalloc 库数组
        tcmalloc_libs = [r"libtcmalloc(_minimal|)\.so\.\d+", r"libtcmalloc\.so\.\d+"]

        # 遍历数组
        for lib_pattern in tcmalloc_libs:
            try:
                # 获取系统库缓存信息
                result = subprocess.run(
                    ["ldconfig", "-p"],
                    capture_output=True,
                    text=True,
                    env=dict(os.environ, PATH="/usr/sbin:" + os.getenv("PATH")),
                    encoding="utf-8",
                    errors="replace",
                )
                libraries = result.stdout.split("\n")

                # 查找匹配的 TCMalloc 库
                for lib in libraries:
                    if re.search(lib_pattern, lib):
                        # 解析库信息
                        match = re.search(r"(.+?)\s+=>\s+(.+)", lib)
                        if match:
                            lib_name, lib_path = (
                                match.group(1).strip(),
                                match.group(2).strip(),
                            )
                            logger.info("检查 TCMalloc: %s => %s", lib_name, lib_path)

                            # 确定库是否链接到 libpthread 和解析未定义符号: pthread_key_create
                            if CommonVersionComparison(libc_ver) < CommonVersionComparison(libc_v234):
                                # glibc < 2.34, pthread_key_create 在 libpthread.so 中。检查链接到 libpthread.so
                                ldd_result = subprocess.run(["ldd", lib_path], capture_output=True, text=True, encoding="utf-8", errors="replace")
                                if "libpthread" in ldd_result.stdout:
                                    logger.info(
                                        "%s 链接到 libpthread, 执行 LD_PRELOAD=%s",
                                        lib_name,
                                        lib_path,
                                    )
                                    # 设置完整路径 LD_PRELOAD
                                    if "LD_PRELOAD" in os.environ and os.environ["LD_PRELOAD"]:
                                        os.environ["LD_PRELOAD"] = os.environ["LD_PRELOAD"] + ":" + lib_path
                                    else:
                                        os.environ["LD_PRELOAD"] = lib_path
                                    return True
                                else:
                                    logger.info(
                                        "%s 没有链接到 libpthread, 将触发未定义符号: pthread_Key_create 错误",
                                        lib_name,
                                    )
                            else:
                                # libc.so (glibc) 的 2.34 版本已将 pthread 库集成到 glibc 内部
                                logger.info(
                                    "%s 链接到 libc.so, 执行 LD_PRELOAD=%s",
                                    lib_name,
                                    lib_path,
                                )
                                # 设置完整路径 LD_PRELOAD
                                if "LD_PRELOAD" in os.environ and os.environ["LD_PRELOAD"]:
                                    os.environ["LD_PRELOAD"] = os.environ["LD_PRELOAD"] + ":" + lib_path
                                else:
                                    os.environ["LD_PRELOAD"] = lib_path
                                return True
            except Exception as e:
                logger.error("检查 TCMalloc 库时出错: %s", e)
                continue

        if "LD_PRELOAD" not in os.environ:
            logger.warning("无法定位 TCMalloc。未在系统上找到 tcmalloc 或 google-perftool, 取消加载内存优化")
            return False

    def configure_tcmalloc_colab(self) -> bool:
        """配置 TCMalloc (Colab)

        Returns:
            bool: TCMalloc (Colab) 配置结果
        """
        logger.info("配置 TCMalloc 内存优化")
        url = "https://github.com/licyk/sd-webui-all-in-one/raw/main/config/libtcmalloc_minimal.so.4"
        libtcmalloc_path = self.workspace / "libtcmalloc_minimal.so.4"
        status = download_file(url=url, path=self.workspace, save_name="libtcmalloc_minimal.so.4")
        if status is None:
            logger.error("下载 TCMalloc 库失败, 无法配置 TCMalloc")
            return False

        if "LD_PRELOAD" in os.environ and os.environ["LD_PRELOAD"]:
            os.environ["LD_PRELOAD"] = os.environ["LD_PRELOAD"] + ":" + libtcmalloc_path.as_posix()
        else:
            os.environ["LD_PRELOAD"] = libtcmalloc_path.as_posix()

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
