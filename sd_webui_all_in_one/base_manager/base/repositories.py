"""仓库克隆、名称解析和镜像环境。"""

import os
import urllib.parse
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    HUGGINGFACE_MIRROR_LIST,
    set_git_base_config,
    set_github_mirror,
)
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.file_manager import (
    is_folder_empty,
    copy_files,
    remove_files,
)
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
    SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH,
)
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def clone_repo(
    repo: str,
    path: Path,
) -> None:
    """克隆仓库到本地, 当仓库已经存在时则跳过克隆
    Args:
        repo (str):
            Git 仓库链接
        path (Path):
            下载到本地的路径

    Raises:
        FileExistsError:
            当克隆 Git 仓库的路径存在文件时
    """
    if path.is_file():
        raise FileExistsError(f"在 '{path}' 存在了文件, 无法进行 Git 仓库克隆")

    if path.is_dir() and not is_folder_empty(path):
        logger.info("'%s' 已存在于 '%s', 跳过下载", Path(repo).name, path)
        return

    with TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)
        if path.exists():
            remove_files(path)
        src = git_warpper.clone(
            repo=repo,
            path=tmp_dir,
        )
        copy_files(src, path)
    logger.info("'%s' 下载到 '%s' 完成", Path(repo).name, path)


def get_repo_name_from_url(
    url: str,
) -> str:
    """从 Git 仓库链接中解析并返回仓库名称

    Args:
        url:
            Git 仓库的链接

    Returns:
        str:
            Git 仓库的名称
    """

    # 1. 处理标准的 HTTP/HTTPS/Git 协议链接
    # 例如: https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
    parsed = urllib.parse.urlparse(url)
    path = parsed.path

    # 2. 处理特殊的 SSH 格式 (urllib 无法正确解析此类非标准 URI)
    # 例如: git@github.com:AUTOMATIC1111/stable-diffusion-webui.git
    if not parsed.scheme and ":" in url:
        # 提取冒号后面的路径部分: AUTOMATIC1111/stable-diffusion-webui.git
        path = url.split(":")[-1]

    # 3. 路径清洗
    # 移除末尾的斜杠 (如果有)
    path = path.rstrip("/")

    # 获取路径的最后一部分 (文件名部分)
    # stable-diffusion-webui.git
    repo_name = os.path.basename(path)

    # 4. 移除 .git 后缀
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]

    return repo_name


def apply_git_base_config_and_github_mirror(
    git_config_path: Path | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """为 Git 应用基本配置并设置 Github 镜像源

    Args:
        git_config_path (Path | None):
            Git 配置文件路径
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        origin_env (dict[str, str] | None):
            原始的环境变量字典

    Returns:
        (dict[str, str]):
            包含 Git 配置 (GIT_CONFIG_GLOBAL) 的环境变量字典
    """
    if origin_env is not None:
        custom_env = origin_env.copy()
    else:
        custom_env = os.environ.copy()

    config_path_env = custom_env.get("GIT_CONFIG_GLOBAL", None)
    if config_path_env is None:
        if git_config_path is None:
            config_path = SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / ".gitconfig"
        else:
            config_path = git_config_path
    else:
        config_path = Path(config_path_env)
        config_path.parent.mkdir(parents=True, exist_ok=True)

    set_github_mirror(
        mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        config_path=config_path,
    )
    set_git_base_config(config_path)
    custom_env["GIT_CONFIG_GLOBAL"] = config_path.as_posix()

    return custom_env


def apply_git_config_global_to_process(custom_env: dict[str, str]) -> str | None:
    """将环境变量中的 Git 全局配置路径同步到当前进程。

    Args:
        custom_env (dict[str, str]): 包含 Git 配置的环境变量字典。

    Returns:
        str | None: 已同步的 Git 全局配置路径，不存在时返回 None。
    """
    git_config_global = custom_env.get("GIT_CONFIG_GLOBAL")
    if git_config_global:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_global
    return git_config_global


def apply_github_raw_file_mirror(
    raw_file_path: str,
    custom_github_mirror: str | list[str] | None = None,
) -> str | None:
    """
    根据 GitHub 镜像源生成 raw 文件 URL

    Args:
        raw_file_path (str):
            GitHub raw 文件路径, 例如 `owner/repo/branch/path/file.json`
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源。字符串可直接传完整 JSON URL, 或传镜像前缀;
            列表会按顺序测试并选择第一个可用镜像前缀

    Returns:
        str | None:
            可用镜像 URL, 未启用或未找到可用镜像时返回 None

    Raises:
        ValueError:
            传入的镜像源参数类型不支持时
    """
    github_mirror = GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    if github_mirror is None:
        return None
    if isinstance(github_mirror, str):
        if github_mirror.endswith(".json"):
            return github_mirror
        mirror_prefix = github_mirror.replace("github.com", "raw.githubusercontent.com", 1).rstrip("/")
        return f"{mirror_prefix}/{raw_file_path}"
    if isinstance(github_mirror, list):
        for gh in github_mirror:
            mirror_prefix = gh.replace("github.com", "raw.githubusercontent.com", 1).rstrip("/")
            test_url = f"{mirror_prefix}/licyk/empty/main/README.md"
            req = urllib.request.Request(test_url, headers=headers)
            try:
                logger.info("测试镜像源: %s", gh)
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.getcode() == 200:
                        logger.info("该镜像源可用")
                        return f"{mirror_prefix}/{raw_file_path}"
            except Exception:
                logger.warning("该镜像源不可用")

        logger.warning("无可用的 Github 镜像源")
        return None

    raise ValueError(f"传入的 Github 镜像源列表类型不支持: {type(github_mirror)}")


def apply_hf_mirror(
    use_hf_mirror: bool = False,
    custom_hf_mirror: str | list[str] | None = None,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """配置 HuggingFace 镜像源

    Args:
        use_hf_mirror (bool):
            是否启用 HuggingFace 镜像源
        custom_hf_mirror (str | list[str] | None):
            自定义 HuggingFace 镜像源
        origin_env (dict[str, str] | None):
            原始环境变量字典

    Returns:
        dict[str, str]:
            应用 HuggingFace 镜像源后的环境变量字典

    Raises:
        ValueError:
            传入的 HuggingFace 镜像源列表类型不受支持时抛出。
    """

    if origin_env is not None:
        custom_env = origin_env.copy()
    else:
        custom_env = os.environ.copy()

    hf_mirror = (HUGGINGFACE_MIRROR_LIST if custom_hf_mirror is None else custom_hf_mirror) if use_hf_mirror else None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    if hf_mirror is None:
        return custom_env
    if isinstance(hf_mirror, str):
        custom_env["HF_ENDPOINT"] = hf_mirror
        return custom_env
    if isinstance(hf_mirror, list):
        for hf in hf_mirror:  # pylint: disable=not-an-iterable
            test_url = f"{hf}/api/models?limit=1"
            req = urllib.request.Request(test_url, headers=headers)
            try:
                logger.info("测试镜像源: %s", hf)
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.getcode() == 200:
                        logger.info("该镜像源可用")
                        custom_env["HF_ENDPOINT"] = hf
                        return custom_env
            except Exception:
                logger.warning("该镜像源不可用")

        logger.warning("无可用的 HuggingFace 镜像源")
        return custom_env

    raise ValueError(f"传入的 HuggingFace 镜像源列表类型不支持: {type(hf_mirror)}")
