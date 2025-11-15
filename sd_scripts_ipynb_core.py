import os
import urllib.request
from pathlib import Path


SD_SCRIPTS_IPYNB_CORE_URL = "https://github.com/licyk/sd-webui-all-in-one/raw/main/sd_scripts_ipynb_core.py" # SD Scripts Manager 核心下载地址
FORCE_DOWNLOAD_CORE = False # 设置为 True 时, 即使 SD Scripts Manager 已存在也会重新下载

try:
    _ = ROOT_PATH
except Exception as _:
    ROOT_PATH = Path(os.getcwd())
    SD_SCRIPTS_IPYNB_CORE_PATH = ROOT_PATH / "sd_scripts_ipynb_core.py" # SD Scripts Manager 核心保存路径
try:
    if SD_SCRIPTS_IPYNB_CORE_PATH.exists() and not FORCE_DOWNLOAD_CORE:
        print("SD WebUI All In One 核心模块已存在")
    else:
        urllib.request.urlretrieve(SD_SCRIPTS_IPYNB_CORE_URL, SD_SCRIPTS_IPYNB_CORE_PATH)
        print("SD WebUI All In One 核心模块下载成功")
except Exception as e:
    raise Exception(f"SD WebUI All In One 核心模块下载错误: {e}")

from sd_scripts_ipynb_core import *