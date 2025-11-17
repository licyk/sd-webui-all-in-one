"""环境变量管理工具"""

import os
import sys

from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, DEFAULT_ENV_VARS


logger = get_logger(
    name="Env Var Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def configure_pip() -> None:
    """使用环境变量配置 Pip / uv"""
    logger.info("配置 Pip / uv")
    os.environ["UV_HTTP_TIMEOUT"] = "30"
    os.environ["UV_CONCURRENT_DOWNLOADS"] = "50"
    os.environ["UV_INDEX_STRATEGY"] = "unsafe-best-match"
    os.environ["UV_PYTHON"] = sys.executable
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


def config_wandb_token(token: str | None = None) -> None:
    """配置 WandB 所需 Token, 配置时将设置`WANDB_API_KEY`环境变量

    Args:
        token (str | None): WandB Token
    """
    if token is not None:
        logger.info("配置 WandB Token")
        os.environ["WANDB_API_KEY"] = token
