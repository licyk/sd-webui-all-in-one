"""环境变量管理工具"""

import os
import sys
from collections.abc import MutableMapping
from dataclasses import dataclass
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


def generate_cache_path_env_vars(cache_path: Path) -> dict[str, str]:
    """生成缓存路径相关环境变量

    返回值为默认值, 应用时不覆盖已存在的同名环境变量, 见`ManagedEnvVars.apply()`

    Args:
        cache_path (Path):
            缓存根目录路径

    Returns:
        (dict[str, str]):
            缓存路径相关环境变量字典
    """
    return {
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


@dataclass(frozen=True)
class ManagedEnvVars:
    """SD WebUI All In One 管理的环境变量

    Attributes:
        defaults (dict[str, str]):
            默认值, 仅在环境中不存在同名环境变量时应用
        overrides (dict[str, str]):
            覆盖值, 总是覆盖环境中的同名环境变量
    """

    defaults: dict[str, str]
    overrides: dict[str, str]

    def apply(self, env: MutableMapping[str, str]) -> None:
        """将环境变量应用到环境变量字典

        Args:
            env (MutableMapping[str, str]):
                要应用的环境变量字典, 如`os.environ`
        """
        for key, value in self.defaults.items():
            env.setdefault(key, value)
        env.update(self.overrides)


def generate_managed_env_vars(
    cache_path: Path | None = None,
    set_config: bool = False,
    python_executable: Path | None = None,
) -> ManagedEnvVars:
    """生成 SD WebUI All In One 管理的环境变量

    Args:
        cache_path (Path | None):
            缓存根目录路径, 为 None 时不生成缓存路径相关环境变量
        set_config (bool):
            是否生成`DEFAULT_ENV_VARS`中的基础配置环境变量
        python_executable (Path | None):
            uv 使用的 Python 解释器路径, 为 None 时不生成`UV_PYTHON`

    Returns:
        (ManagedEnvVars):
            管理的环境变量
    """
    defaults = {} if cache_path is None else generate_cache_path_env_vars(cache_path)
    overrides = dict(DEFAULT_ENV_VARS) if set_config else {}
    if python_executable is not None:
        overrides["UV_PYTHON"] = python_executable.as_posix()
    return ManagedEnvVars(defaults=defaults, overrides=overrides)


def get_managed_env_vars(cache_path: Path) -> ManagedEnvVars:
    """获取外部进程 (如交互式终端) 所需的 SD WebUI All In One 管理的环境变量

    结果只由参数决定, 不读取当前进程环境变量, 也不包含`UV_PYTHON`, 代理和配置文件相关环境变量,
    这些环境变量由调用方根据目标进程决定

    Args:
        cache_path (Path):
            缓存根目录路径

    Returns:
        (ManagedEnvVars):
            管理的环境变量
    """
    return generate_managed_env_vars(cache_path=cache_path, set_config=True)


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
    managed = generate_managed_env_vars(set_config=True, python_executable=Path(sys.executable))
    for e, v in managed.overrides.items():
        logger.info("- Env:%s = %s", e, v)
    managed.apply(os.environ)


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
