"""PyPI / Github / HuggingFace 镜像管理工具"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.env_manager import generate_uv_and_pip_env_mirror_config
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.file_operations.file_manager import remove_files
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR, LOGGER_NAME
from sd_webui_all_in_one.pytorch_manager.base import (
    PYPI_EXTRA_INDEX_MIRROR_CERNET,
    PYPI_INDEX_MIRROR_OFFICIAL,
    PYPI_INDEX_MIRROR_TENCENT,
    PYTORCH_FIND_LINKS_MIRROR_ALIYUN,
    PYTORCH_FIND_LINKS_MIRROR_LICYK,
    PYTORCH_FIND_LINKS_MIRROR_OFFICIAL,
)


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

GITHUB_MIRROR_LIST = [
    "https://ghfast.top/https://github.com",
    "https://mirror.ghproxy.com/https://github.com",
    "https://ghproxy.net/https://github.com",
    "https://gh.api.99988866.xyz/https://github.com",
    "https://gh-proxy.com/https://github.com",
    "https://ghps.cc/https://github.com",
    "https://gh.idayer.com/https://github.com",
    "https://ghproxy.1888866.xyz/github.com",
    "https://slink.ltd/https://github.com",
    "https://github.boki.moe/github.com",
    "https://github.moeyy.xyz/https://github.com",
    "https://gh-proxy.net/https://github.com",
    "https://gh-proxy.ygxz.in/https://github.com",
    "https://wget.la/https://github.com",
    "https://kkgithub.com",
    "https://gitclone.com/github.com",
]
"""Github 镜像源列表"""

HUGGINGFACE_MIRROR_LIST = [
    "https://hf-mirror.com",
]
"""HuggingFace 镜像源列表"""


def set_pypi_index_mirror(
    mirror: str | None = None,
) -> None:
    """设置 PyPI Index 镜像源

    Args:
        mirror (str | None): PyPI 镜像源链接, 当不传入镜像源链接时则清除镜像源
    """
    if mirror is not None:
        logger.info("使用 PIP_INDEX_URL, UV_DEFAULT_INDEX 环境变量设置 PyPI Index 镜像源")
        os.environ["PIP_INDEX_URL"] = mirror
        os.environ["UV_DEFAULT_INDEX"] = mirror
    else:
        logger.info("清除 PIP_INDEX_URL, UV_DEFAULT_INDEX 环境变量, 取消使用 PyPI Index 镜像源")
        os.environ.pop("PIP_INDEX_URL", None)
        os.environ.pop("UV_DEFAULT_INDEX", None)


def set_pypi_extra_index_mirror(
    mirror: str | None = None,
) -> None:
    """设置 PyPI Extra Index 镜像源

    Args:
        mirror (str | None): PyPI 镜像源链接, 当不传入镜像源链接时则清除镜像源
    """
    if mirror is not None:
        logger.info("使用 PIP_EXTRA_INDEX_URL, UV_INDEX 环境变量设置 PyPI Extra Index 镜像源")
        os.environ["PIP_EXTRA_INDEX_URL"] = mirror
        os.environ["UV_INDEX"] = mirror
    else:
        logger.info("清除 PIP_EXTRA_INDEX_URL, UV_INDEX 环境变量, 取消使用 PyPI Extra Index 镜像源")
        os.environ.pop("PIP_EXTRA_INDEX_URL", None)
        os.environ.pop("UV_INDEX", None)


def set_pypi_find_links_mirror(
    mirror: str | None = None,
) -> None:
    """设置 PyPI Find Links 镜像源

    Args:
        mirror (str | None): PyPI 镜像源链接, 当不传入镜像源链接时则清除镜像源
    """
    if mirror is not None:
        logger.info("使用 PIP_FIND_LINKS, UV_FIND_LINKS 环境变量设置 PyPI Find Links 镜像源")
        os.environ["PIP_FIND_LINKS"] = " ".join([x.strip() for x in mirror.strip().split()])
        # UV_FIND_LINKS 使用 `,` 分割镜像源: https://github.com/astral-sh/uv/pull/10477
        os.environ["UV_FIND_LINKS"] = ",".join([x.strip() for x in mirror.strip().split()])
    else:
        logger.info("清除 PIP_FIND_LINKS, UV_FIND_LINKS 环境变量, 取消使用 PyPI Find Links 镜像源")
        os.environ.pop("PIP_FIND_LINKS", None)
        os.environ.pop("UV_FIND_LINKS", None)


def test_github_mirror(
    mirror: list[str],
) -> str | None:
    """测试 Github 镜像源可用性, 当有一个可用的 Github 镜像源则直接返回该镜像源地址

    Args:
        mirror (list[str]):
            Github 镜像源列表

    Returns:
        (str | None): 当有可用镜像源可用时则返回该镜像源地址
    """
    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        mirror_test_path = tmp_dir / "__github_mirror_test__"
        custon_env = os.environ.copy()
        custon_env.pop("GIT_CONFIG_GLOBAL", None)
        for gh in mirror:
            logger.info("测试 Github 镜像源: %s", gh)
            test_repo = f"{gh}/licyk/empty"
            try:
                if mirror_test_path.exists():
                    remove_files(mirror_test_path)
                run_cmd(
                    ["git", "clone", "--depth", "1", test_repo, mirror_test_path.as_posix()],
                    custom_env=custon_env,
                    live=False,
                )
                if mirror_test_path.exists():
                    remove_files(mirror_test_path)
                logger.info("该镜像源可用")
                return gh
            except Exception:
                logger.info("镜像源不可用")

    logger.info("无可用的 Github 镜像源")
    return None


def set_git_base_config(
    config_path: Path,
) -> None:
    """设置 Git 基本配置

    Args:
        config_path (Path):
            Git 配置文件路径

    Raises:
        RuntimeError:
            设置 Git 基本配置时发生错误
    """
    try:
        run_cmd(["git", "config", "--file", config_path.as_posix(), "--add", "safe.directory", "'*'"], live=False)
        run_cmd(["git", "config", "--file", config_path.as_posix(), "core.longpaths", "true"], live=False)
    except RuntimeError as e:
        raise RuntimeError(f"设置 Git 基本配置时发生错误: {e}") from e


def set_github_mirror(
    mirror: str | list[str] | None = None,
    config_path: Path = None,
) -> Path:
    """设置 Github 镜像源并返回带有镜像源配置的 Git 配置文件路径

    当`mirror`传入的是 Github 镜像源地址, 则直接设置 Github 镜像源

    如果传入的是镜像源列表, 则自动测试可用的 Github 镜像源并设置 Github 镜像源

    当不传入参数时则不进行任何 Github 镜像源配置

    传入参数为 [] 时则清除 Github 镜像源配置

    使用:
    ```python
    set_github_mirror(mirror=None) # 传入参数为 None 时则不进行任何 Github 镜像源配置

    set_github_mirror(mirror=[]) # 传入参数为 [] 时则清除 Github 镜像源配置

    set_github_mirror(mirror="https://ghfast.top/https://github.com") # 只设置一个 Github 镜像源时将直接使用该 Github 镜像源

    set_github_mirror( # 传入 Github 镜像源列表时将自动测试可用的 Github 镜像源并设置
        mirror=[
            "https://ghfast.top/https://github.com",
            "https://mirror.ghproxy.com/https://github.com",
            "https://ghproxy.net/https://github.com",
            "https://gh.api.99988866.xyz/https://github.com",
            "https://gh-proxy.com/https://github.com",
            "https://ghps.cc/https://github.com",
            "https://gh.idayer.com/https://github.com",
            "https://ghproxy.1888866.xyz/github.com",
            "https://slink.ltd/https://github.com",
            "https://github.boki.moe/github.com",
            "https://github.moeyy.xyz/https://github.com",
            "https://gh-proxy.net/https://github.com",
            "https://gh-proxy.ygxz.in/https://github.com",
            "https://wget.la/https://github.com",
            "https://kkgithub.com",
            "https://gitclone.com/github.com",
        ]
    )
    ```

    Args:
        mirror (str | list[str] | None):
            Github 镜像源地址
        config_path (Path | None):
            Git 配置文件路径

    Returns:
        Path:
            配置 Github 镜像源后的 Git 配置文件路径

    Raises:
        RuntimeError:
            设置镜像源出现错误时
        ValueError:
            传入的镜像源类型不支持时
    """

    def _set_github_mirror(
        mirror: str,
    ) -> None:
        logger.info("通过 GIT_CONFIG_GLOBAL 环境变量设置 Github 镜像源")
        try:
            run_cmd(["git", "config", "--file", config_path.as_posix(), f"url.{mirror}.insteadOf", "https://github.com"])
        except RuntimeError as e:
            logger.error("设置 Github 镜像源时发生错误: %s", e)
            raise RuntimeError(f"设置 Github 镜像源时发生错误: {e}") from e

    def _configure_github_mirror(
        mirror: str | list[str],
    ) -> None:
        if isinstance(mirror, str):
            _set_github_mirror(mirror)
        elif isinstance(mirror, list):
            if len(mirror) == 0:
                logger.info("取消使用 Github 镜像源")
                if config_path.exists():
                    remove_files(config_path)
            elif len(mirror) == 1:
                _set_github_mirror(mirror)
            else:
                gh = test_github_mirror(mirror)
                if gh is not None:
                    _set_github_mirror(gh)
                else:
                    logger.info("取消使用 Github 镜像源")
                    if config_path.exists():
                        remove_files(config_path)
        else:
            logger.info("未知镜像源参数类型: %s", type(mirror))
            raise ValueError(f"未知镜像源参数类型: {type(mirror)}")

    if config_path is None:
        config_path = Path().cwd() / ".gitconfig"

    if mirror is not None:
        _configure_github_mirror(mirror)

    return config_path


def set_huggingface_mirror(
    mirror: str | None = None,
) -> None:
    """设置 HuggingFace 镜像源

    Args:
        mirror (str | None): HuggingFace 镜像源链接, 当不传入镜像源链接时则清除镜像源
    """
    if mirror is not None:
        logger.info("使用 HF_ENDPOINT 环境变量设置 HuggingFace 镜像源")
        os.environ["HF_ENDPOINT"] = mirror
    else:
        logger.info("清除 HF_ENDPOINT 环境变量, 取消使用 HuggingFace 镜像源")
        os.environ.pop("HF_ENDPOINT", None)


def set_mirror(
    pypi_index_mirror: str | None = None,
    pypi_extra_index_mirror: str | None = None,
    pypi_find_links_mirror: str | None = None,
    github_mirror: str | list[str] | None = None,
    huggingface_mirror: str | None = None,
) -> None:
    """镜像源设置

    Args:
        pypi_index_mirror (str | None): PyPI Index 镜像源链接
        pypi_extra_index_mirror (str | None): PyPI Extra Index 镜像源链接
        pypi_find_links_mirror (str | None): PyPI Find Links 镜像源链接
        github_mirror (str | list[str] | None): Github 镜像源链接或者镜像源链接列表
        huggingface_mirror (str | None): HuggingFace 镜像源链接
    """
    logger.info("配置镜像源中")
    set_pypi_index_mirror(pypi_index_mirror)
    set_pypi_extra_index_mirror(pypi_extra_index_mirror)
    set_pypi_find_links_mirror(pypi_find_links_mirror)
    os.environ["GIT_CONFIG_GLOBAL"] = set_github_mirror(github_mirror).as_posix()
    set_huggingface_mirror(huggingface_mirror)
    logger.info("镜像源配置完成")


def get_pypi_mirror_config(
    use_cn_mirror: bool | None = False,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """获取带有 PyPI 镜像源配置的环境变量字典

    如果设置了 `SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR=1` 环境变量, 则启用 SD WebUI All In One 自带的额外 PyPI 镜像源

    Args:
        use_cn_mirror (bool | None):
            是否使用国内镜像源
        origin_env (dict[str, str] | None):
            原始的环境变量字典

    Returns:
        (dict[str, str]):
            带有 PyPI 镜像源配置的环境变量字典
    """
    if use_cn_mirror:
        return generate_uv_and_pip_env_mirror_config(
            index_url=PYPI_INDEX_MIRROR_TENCENT,
            extra_index_url=PYPI_EXTRA_INDEX_MIRROR_CERNET,
            find_links=[PYTORCH_FIND_LINKS_MIRROR_ALIYUN, PYTORCH_FIND_LINKS_MIRROR_LICYK] if SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR else PYTORCH_FIND_LINKS_MIRROR_ALIYUN,
            origin_env=origin_env,
        )
    else:
        return generate_uv_and_pip_env_mirror_config(
            index_url=PYPI_INDEX_MIRROR_OFFICIAL,
            extra_index_url=[],
            find_links=[PYTORCH_FIND_LINKS_MIRROR_OFFICIAL, PYTORCH_FIND_LINKS_MIRROR_LICYK] if SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR else PYTORCH_FIND_LINKS_MIRROR_OFFICIAL,
            origin_env=origin_env,
        )
