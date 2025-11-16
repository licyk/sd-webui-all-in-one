"""SD WebUI All In One 模块初始化工具 (弃用)"""

import warnings
from urllib.request import urlretrieve
from urllib.error import URLError, ContentTooShortError, HTTPError
from pathlib import Path


def init_sd_webui_all_in_one_module(
    url: str | None = None,
    force_download: bool | None = False,
) -> None:
    """SD WebUI All In One 模块下载工具"""
    if url is None:
        url = "https://github.com/licyk/sd-webui-all-in-one/raw/dev/sd_webui_all_in_one.py"

    root_path = Path(__file__).parent
    sd_webui_all_in_one_path = root_path / "sd_webui_all_in_one.py"
    if sd_webui_all_in_one_path.exists() and not force_download:
        print(f"SD WebUI All In One 核心已存在, 路径: {sd_webui_all_in_one_path}")
        return

    try:
        urlretrieve(url, sd_webui_all_in_one_path)
        print(f"SD WebUI All In One 核心模块下载成功, 路径: {sd_webui_all_in_one_path}")
    except (URLError, HTTPError, ContentTooShortError) as e:
        raise Exception(f"SD WebUI All In One 核心模块下载错误: {e}") from e
    except Exception as e:
        raise Exception(f"未知错误导致 SD WebUI All In One 核心模块下载失败: {e}") from e


warnings.warn(
    """sd_scripts_ipynb_core 将被弃用, 请改用 sd_webui_all_in_one 模块.

- 使用 sd_webui_all_in_one 的方法:
1. 安装 sd_webui_all_in_one 内核

    python -m pip install git+https://github.com/licyk/sd-webui-all-in-one

2. 将原有 sd_scripts_ipynb_core 的模块导入改为 sd_webui_all_in_one, 例如原有的模块导入如下:

    from sd_scripts_ipynb_core import SDWebUIManager, logger

修改后的模块导入:

    from sd_webui_all_in_one import SDWebUIManager, logger


- 关于 Jupyter Notebook:
如果原有的 Jupyter Notebook 中初始化 sd_scripts_ipynb_core 的代码如下:

    #################################################################################################################
    # SD_SCRIPTS_IPYNB_CORE_URL, FORCE_DOWNLOAD_CORE 参数可根据需求修改, 通常保持默认即可
    SD_SCRIPTS_IPYNB_CORE_URL = "https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_scripts_ipynb_core.py" # ComfyUI Manager 核心下载地址
    FORCE_DOWNLOAD_CORE = False # 设置为 True 时, 即使 ComfyUI Manager 已存在也会重新下载
    #################################################################################################################

    # 省略的其余代码

    os.environ["MANAGER_LOGGER_NAME"] = "ComfyUI Manager"
    from sd_scripts_ipynb_core import logger, VERSION, ComfyUIManager
    logger.info("ComfyUI Manager 版本: %s", VERSION)

可以将代码中 `SD_SCRIPTS_IPYNB_CORE_URL` 的值修改为 `https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_webui_all_in_one.py`
再将导入部分的 `from sd_scripts_ipynb_core import` 修改为 `from sd_webui_all_in_one import`
修改后的代码如下:

    #################################################################################################################
    # SD_SCRIPTS_IPYNB_CORE_URL, FORCE_DOWNLOAD_CORE 参数可根据需求修改, 通常保持默认即可
    SD_SCRIPTS_IPYNB_CORE_URL = "https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_webui_all_in_one.py" # ComfyUI Manager 核心下载地址
    FORCE_DOWNLOAD_CORE = False # 设置为 True 时, 即使 ComfyUI Manager 已存在也会重新下载
    #################################################################################################################

    # 省略的其余代码

    os.environ["MANAGER_LOGGER_NAME"] = "ComfyUI Manager"
    from sd_webui_all_in_one import logger, VERSION, ComfyUIManager
    logger.info("ComfyUI Manager 版本: %s", VERSION)

修改后可正常使用 sd_webui_all_in_one 模块.
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
