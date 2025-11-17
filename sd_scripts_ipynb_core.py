"""SD WebUI All In One 模块初始化工具 (弃用)"""

import sys
import warnings
import subprocess
from importlib.metadata import version


def init_sd_webui_all_in_one_module(
    url: str | None = None,
    force_download: bool | None = False,
) -> None:
    """SD WebUI All In One 模块下载工具"""
    if url is None:
        url = "https://github.com/licyk/sd-webui-all-in-one@dev"

    cmd = f'"{sys.executable}" -m pip install git+"{url}"'

    if not force_download:
        try:
            _ = version("sd-webui-all-in-one")
            print("SD WebUI All In One 已安装")
            return
        except Exception:
            pass

    print("安装 SD WebUI All In One 中")
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,
        shell=True,
        encoding="utf-8",
        errors="replace",
    ) as p:
        for line in p.stdout:
            print(line, end="", flush=True)

        p.wait()
        if p.returncode != 0:
            raise RuntimeError("执行 SD WebUI All In One 安装进程发生了错误")
        print("安装 SD WebUI All In One 成功")


warnings.warn(
    """sd_scripts_ipynb_core 将被弃用, 请改用 sd_webui_all_in_one 模块.

- 使用 sd_webui_all_in_one 的方法:
1. 安装 sd_webui_all_in_one 内核

    python -m pip install git+https://github.com/licyk/sd-webui-all-in-one

2. 将原有 sd_scripts_ipynb_core 的模块导入改为 sd_webui_all_in_one, 例如原有的模块导入如下:

    from sd_scripts_ipynb_core import SDWebUIManager, logger

修改后的模块导入:

    from sd_webui_all_in_one import SDWebUIManager, logger
""",
    DeprecationWarning,
    stacklevel=2,
)


init_sd_webui_all_in_one_module()
del init_sd_webui_all_in_one_module
# pylint: disable=unused-wildcard-import
# pylint: disable=wildcard-import
# pylint: disable=wrong-import-position
from sd_webui_all_in_one import *  # noqa: F403
