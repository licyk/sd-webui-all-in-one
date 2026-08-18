"""环境变量管理工具"""

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    DEFAULT_ENV_VARS,
    LOGGER_NAME,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def generate_proxy_env_vars(proxy_address: str | None = None) -> dict[str, str]:
    """生成代理相关环境变量

    Args:
        proxy_address (str | None):
            代理服务器地址, 为 None 时不配置代理

    Returns:
        (dict[str, str]):
            代理相关环境变量字典
    """
    env = {"NO_PROXY": "localhost,127.0.0.1,::1"}
    if proxy_address is not None:
        env["HTTP_PROXY"] = proxy_address
        env["HTTPS_PROXY"] = proxy_address
    return env


def generate_cache_path_env_vars(
    cache_path: Path,
    origin_env: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """生成缓存路径相关环境变量

    Args:
        cache_path (Path):
            缓存根目录路径
        origin_env (Mapping[str, str] | None):
            原始环境变量字典, 为 None 时使用当前进程环境变量

    Returns:
        (dict[str, str]):
            已配置缓存路径的环境变量字典
    """
    env = os.environ if origin_env is None else origin_env
    defaults = {
        "CACHE_HOME": cache_path.as_posix(),
        "HF_HOME": (cache_path / "huggingface").as_posix(),
        "MATPLOTLIBRC": cache_path.as_posix(),
        "MODELSCOPE_CACHE": (cache_path / "modelscope" / "hub").as_posix(),
        "MS_CACHE_HOME": (cache_path / "modelscope" / "hub").as_posix(),
        "SYCL_CACHE_DIR": (cache_path / "libsycl_cache").as_posix(),
        "TORCH_HOME": (cache_path / "torch").as_posix(),
        "U2NET_HOME": (cache_path / "u2net").as_posix(),
        "XDG_CACHE_HOME": cache_path.as_posix(),
        "PIP_CACHE_DIR": (cache_path / "pip").as_posix(),
        "PYTHONPYCACHEPREFIX": (cache_path / "pycache").as_posix(),
        "TORCHINDUCTOR_CACHE_DIR": (cache_path / "torchinductor").as_posix(),
        "TRITON_CACHE_DIR": (cache_path / "triton").as_posix(),
        "UV_CACHE_DIR": (cache_path / "uv").as_posix(),
    }
    return {key: env.get(key, value) for key, value in defaults.items()}


def generate_config_file_env_vars(config_dir: Path) -> dict[str, str]:
    """生成 Pip、uv 和 Git 配置文件相关环境变量

    Args:
        config_dir (Path):
            配置文件所在目录

    Returns:
        (dict[str, str]):
            配置文件相关环境变量字典
    """
    return {
        "PIP_CONFIG_FILE": (config_dir / "pip.ini").as_posix(),
        "UV_CONFIG_FILE": (config_dir / "uv.toml").as_posix(),
        "GIT_CONFIG_GLOBAL": (config_dir / ".gitconfig").as_posix(),
    }


def configure_pip() -> None:
    """使用环境变量配置 Pip / uv"""
    logger.info("配置 Pip / uv")
    os.environ["UV_HTTP_TIMEOUT"] = "30"
    os.environ["UV_CONCURRENT_DOWNLOADS"] = "50"
    os.environ["UV_INDEX_STRATEGY"] = "unsafe-best-match"
    os.environ["UV_PYTHON"] = Path(sys.executable).as_posix()
    os.environ["UV_NO_PROGRESS"] = "1"
    os.environ["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    os.environ["PIP_NO_WARN_SCRIPT_LOCATION"] = "0"
    os.environ["PIP_TIMEOUT"] = "30"
    os.environ["PIP_RETRIES"] = "5"
    os.environ["PIP_PREFER_BINARY"] = "1"
    os.environ["PIP_YES"] = "1"


def configure_env_var() -> None:
    """通过环境变量配置部分环境功能"""
    logger.info("使用环境变量配置部分设置")
    for e, v in DEFAULT_ENV_VARS:
        logger.info("- Env:%s = %s", e, v)
        os.environ[e] = v


def config_wandb_token(
    token: str | None = None,
) -> None:
    """配置 WandB 所需 Token, 配置时将设置`WANDB_API_KEY`环境变量

    Args:
        token (str | None): WandB Token
    """
    if token is not None:
        logger.info("配置 WandB Token")
        os.environ["WANDB_API_KEY"] = token


def generate_uv_and_pip_env_mirror_config(
    index_url: str | list[str] | None = None,
    extra_index_url: str | list[str] | None = None,
    find_links: str | list[str] | None = None,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """生成 Pip 和 uv 包管理器可使用镜像源环境变量

    - 当传入的镜像源参数为 None 时, 不进行任何配置
    - 当传入的镜像源参数为字符串或者列表时:
        - 如果为空字符串或者为空列表, 则将对应的镜像源配置进行清空
        - 否则设置对应的镜像源配置

    Args:
        index_url (str | list[str] | None):
            `PIP_INDEX_URL`, `UV_DEFAULT_INDEX` 环境变量配置
        extra_index_url (str | list[str] | None):
            `PIP_EXTRA_INDEX_URL`, `UV_INDEX` 环境变量配置
        find_links (str | list[str] | None):
            `PIP_FIND_LINKS`, `UV_FIND_LINKS` 环境变量配置
        origin_env (dict[str, str] | None):
            原始的环境变量字典

    Returns:
        (dict[str, str]):
            配置镜像源后的环境变量字典
    """
    if origin_env is None:
        custom_env = os.environ.copy()
    else:
        custom_env = origin_env.copy()

    if index_url is not None:
        logger.debug("配置 PIP_INDEX_URL, UV_DEFAULT_INDEX")
        if isinstance(index_url, list):
            pip_index_url_str = " ".join([x.strip() for x in index_url if x.strip() != ""])
        else:
            pip_index_url_str = " ".join([x.strip() for x in index_url.split() if x.strip() != ""])

        if pip_index_url_str == "":
            custom_env.pop("PIP_INDEX_URL", None)
            custom_env.pop("UV_DEFAULT_INDEX", None)
        else:
            custom_env["PIP_INDEX_URL"] = pip_index_url_str
            custom_env["UV_DEFAULT_INDEX"] = pip_index_url_str

    if extra_index_url is not None:
        logger.debug("配置 PIP_EXTRA_INDEX_URL, UV_INDEX")
        if isinstance(extra_index_url, list):
            pip_extra_index_url_str = " ".join([x.strip() for x in extra_index_url if x.strip() != ""])
        else:
            pip_extra_index_url_str = " ".join([x.strip() for x in extra_index_url.split() if x.strip() != ""])

        if pip_extra_index_url_str == "":
            custom_env.pop("PIP_EXTRA_INDEX_URL", None)
            custom_env.pop("UV_INDEX", None)
        else:
            custom_env["PIP_EXTRA_INDEX_URL"] = pip_extra_index_url_str
            custom_env["UV_INDEX"] = pip_extra_index_url_str

    if find_links is not None:
        logger.debug("配置 PIP_FIND_LINKS, UV_FIND_LINKS")
        if isinstance(find_links, list):
            pip_find_links_str = " ".join([x.strip() for x in find_links if x.strip() != ""])
            uv_find_links_str = ",".join([x.strip() for x in find_links if x.strip() != ""])
        else:
            pip_find_links_str = " ".join([x.strip() for x in find_links.split() if x.strip() != ""])
            uv_find_links_str = ",".join([x.strip() for x in find_links.split() if x.strip() != ""])

        if pip_find_links_str == "":
            custom_env.pop("PIP_FIND_LINKS", None)
            custom_env.pop("UV_FIND_LINKS", None)
        else:
            custom_env["PIP_FIND_LINKS"] = pip_find_links_str
            custom_env["UV_FIND_LINKS"] = uv_find_links_str

    return custom_env
