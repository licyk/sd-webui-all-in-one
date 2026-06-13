"""修复 Stable Diffusion WebUI 无效模块仓库地址模块"""

import os
from pathlib import Path

from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.cmd import run_cmd

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def fix_stable_diffusion_invaild_repo_url(
    sd_webui_path: Path,
    custom_env: dict[str, str] | None = None,
) -> None:
    """修复 Stable Diffusion WebUI 无效的组件仓库源

    Args:
        sd_webui_path (Path):
            Stable Diffusion WebUI 根目录
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        RuntimeError:
            修复 Stable Diffusion WebUI 组件仓库源失败时抛出。
    """
    logger.info("检查 Stable Diffusion WebUI 无效组件仓库源")
    stable_diffusion_path = sd_webui_path / "repositories" / "stable-diffusion-stability-ai"
    new_repo_url = "https://github.com/licyk/stablediffusion"
    if not git_warpper.is_git_repo(stable_diffusion_path):
        return

    if custom_env is None:
        custom_env = os.environ.copy()
    else:
        custom_env = custom_env.copy()

    custom_env.pop("GIT_CONFIG_GLOBAL", None)
    git_command_prefix = ["git", "-C", stable_diffusion_path.as_posix()]
    try:
        repo_url = run_cmd(
            [*git_command_prefix, "remote", "get-url", "origin"],
            custom_env=custom_env,
            live=False,
        )
    except RuntimeError as e:
        try:
            remotes = run_cmd(
                [*git_command_prefix, "remote"],
                custom_env=custom_env,
                live=False,
            )
        except RuntimeError:
            raise RuntimeError(f"修复 Stable Diffusion WebUI 无效的组件仓库源时发生错误: {e}") from e

        remote_names = {remote.strip() for remote in (remotes or "").splitlines()}
        if "origin" in remote_names:
            raise RuntimeError(f"修复 Stable Diffusion WebUI 无效的组件仓库源时发生错误: {e}") from e

        try:
            run_cmd(
                [*git_command_prefix, "remote", "add", "origin", new_repo_url],
                custom_env=custom_env,
                live=False,
            )
            logger.info("添加仓库源: origin -> %s", new_repo_url)
            return
        except RuntimeError as add_error:
            logger.error("修复 Stable Diffusion WebUI 无效的组件仓库源时发生错误: %s", add_error)
            raise RuntimeError(f"修复 Stable Diffusion WebUI 无效的组件仓库源时发生错误: {add_error}") from add_error
    except Exception as e:
        raise RuntimeError(f"修复 Stable Diffusion WebUI 无效的组件仓库源时发生错误: {e}") from e

    repo_url = (repo_url or "").strip()
    if repo_url in ["https://github.com/Stability-AI/stablediffusion.git", "https://github.com/Stability-AI/stablediffusion"]:
        try:
            run_cmd(
                [*git_command_prefix, "remote", "set-url", "origin", new_repo_url],
                custom_env=custom_env,
                live=False,
            )
            logger.info("替换仓库源: %s -> %s", repo_url, new_repo_url)
        except RuntimeError as e:
            logger.error("修复 Stable Diffusion WebUI 无效的组件仓库源时发生错误: %s", e)
            raise RuntimeError(f"修复 Stable Diffusion WebUI 无效的组件仓库源时发生错误: {e}") from e
