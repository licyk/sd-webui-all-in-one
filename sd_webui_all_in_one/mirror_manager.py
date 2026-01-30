"""PyPI / Github / HuggingFace 镜像管理工具"""

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.file_operations.file_manager import remove_files
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR


logger = get_logger(
    name="Mirror Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def set_pypi_index_mirror(mirror: str | None = None) -> None:
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


def set_pypi_extra_index_mirror(mirror: str | None = None) -> None:
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


def set_pypi_find_links_mirror(mirror: str | None = None) -> None:
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


def set_github_mirror(mirror: str | list[str] | None = None, config_path: Path | str = None) -> None:
    """设置 Github 镜像源

    当`mirror`传入的是 Github 镜像源地址, 则直接设置 GIT_CONFIG_GLOBAL 环境变量并直接使用该镜像源地址

    如果传入的是镜像源列表, 则自动测试可用的 Github 镜像源并设置 GIT_CONFIG_GLOBAL 环境变量

    当不传入参数时则清除 GIT_CONFIG_GLOBAL 环境变量并删除 GIT_CONFIG_GLOBAL 环境变量对应的 Git 配置文件

    使用:
    ```python
    set_github_mirror() # 不传入参数时则清除 Github 镜像源

    set_github_mirror("https://ghfast.top/https://github.com") # 只设置一个 Github 镜像源时将直接使用该 Github 镜像源

    set_github_mirror( # 传入 Github 镜像源列表时将自动测试可用的 Github 镜像源并设置
        [
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
        mirror (str | list[str] | None): Github 镜像源地址
        config_path (Path | str): Git 配置文件路径
    """
    if mirror is None:
        logger.info("清除 GIT_CONFIG_GLOBAL 环境变量, 取消使用 Github 镜像源")
        git_config = os.environ.pop("GIT_CONFIG_GLOBAL", None)
        if git_config is not None:
            p = Path(git_config)
            if p.exists():
                p.unlink()
        return

    if config_path is None:
        config_path = os.getcwd()

    config_path = Path(config_path) if not isinstance(config_path, Path) and config_path is not None else config_path
    git_config_path = config_path / ".gitconfig"
    os.environ["GIT_CONFIG_GLOBAL"] = git_config_path.as_posix()

    if isinstance(mirror, str):
        logger.info("通过 GIT_CONFIG_GLOBAL 环境变量设置 Github 镜像源")
        try:
            run_cmd(
                [
                    "git",
                    "config",
                    "--global",
                    f"url.{mirror}.insteadOf",
                    "https://github.com",
                ]
            )
        except Exception as e:
            logger.error("设置 Github 镜像源时发生错误: %s", e)
    elif isinstance(mirror, list):
        with TemporaryDirectory() as tmp_dir:
            tmp_dir = Path(tmp_dir)
            mirror_test_path = tmp_dir / "__github_mirror_test__"
            custon_env = os.environ.copy()
            custon_env.pop("GIT_CONFIG_GLOBAL", None)
            for gh in mirror:
                logger.info("测试 Github 镜像源: %s", gh)
                test_repo = f"{gh}/licyk/empty"
                if mirror_test_path.exists():
                    remove_files(mirror_test_path)
                try:
                    run_cmd(
                        ["git", "clone", test_repo, mirror_test_path.as_posix()],
                        custom_env=custon_env,
                        live=False,
                    )
                    if mirror_test_path.exists():
                        remove_files(mirror_test_path)
                    run_cmd(
                        [
                            "git",
                            "config",
                            "--global",
                            f"url.{gh}.insteadOf",
                            "https://github.com",
                        ]
                    )
                    logger.info("该镜像源可用")
                    return
                except Exception as _:
                    logger.info("镜像源不可用")

            logger.info("无可用的 Github 镜像源, 取消使用 Github 镜像源")
            if git_config_path.exists():
                git_config_path.unlink()
            os.environ.pop("GIT_CONFIG_GLOBAL", None)
    else:
        logger.info("未知镜像源参数类型: %s", type(mirror))
        return


def set_huggingface_mirror(mirror: str | None = None) -> None:
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
    set_github_mirror(github_mirror)
    set_huggingface_mirror(huggingface_mirror)
    logger.info("镜像源配置完成")
