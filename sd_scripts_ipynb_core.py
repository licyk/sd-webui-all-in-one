"""SD WebUI All In One 模块初始化工具"""

from urllib.request import urlretrieve
from urllib.error import URLError, ContentTooShortError, HTTPError
from pathlib import Path


def init_sd_webui_all_in_one_module(
    url: str | None = None,
    force_download: bool | None = False,
) -> None:
    """SD WebUI All In One 模块下载工具"""
    if url is None:
        url = "https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_webui_all_in_one.py"

    root_path = Path(__file__).parent
    sd_webui_all_in_one_path = root_path / "sd_webui_all_in_one.py"
    if sd_webui_all_in_one_path.exists() and not force_download:
        print(f"SD WebUI All In One 核心已存在, 路径: {sd_webui_all_in_one_path}")
        return

    try:
        urlretrieve(url, sd_webui_all_in_one_path)
        print("SD WebUI All In One 核心模块下载成功")
    except (URLError, HTTPError, ContentTooShortError) as e:
        raise Exception(f"SD WebUI All In One 核心模块下载错误: {e}") from e
    except Exception as e:
        raise Exception(f"未知错误导致 SD WebUI All In One 核心模块下载失败: {e}") from e


init_sd_webui_all_in_one_module()
del init_sd_webui_all_in_one_module
# pylint: disable=unused-wildcard-import
# pylint: disable=wildcard-import
# pylint: disable=wrong-import-position
from sd_webui_all_in_one import *  # noqa: F403
