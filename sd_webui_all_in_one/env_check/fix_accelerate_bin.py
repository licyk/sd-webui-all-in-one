import importlib.metadata
import sys
from pathlib import Path

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import pip_install
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR, LOGGER_NAME
from sd_webui_all_in_one.cmd import run_cmd


logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def check_accelerate_bin(
    base_path: Path,
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
) -> None:
    """检查 Numpy 是否需要降级

    Args:
        base_path (Path):
            SD Trainer 根目录
        use_uv (bool| None):
            是否使用 uv 安装依赖
        custom_env (dict[str, str] | None):
            环境变量字典

    Raises:
        RuntimeError:
            检查 Numpy 版本时出现错误
    """
    try:
        repo = git_warpper.get_current_branch_remote_url(base_path)
        if "bmaltais/kohya_ss" not in repo:
            logger.debug("当前分支非 bmaltais/kohya_ss")
            return
    except Exception as e:
        logger.debug("获取仓库远程源失败: %s", e)
        return

    logger.info("检查 accelerate 可执行文件可用性")
    try:
        run_cmd(["accelerate", "--help"], live=False)
        logger.info("accelerate 可执行文件可用")
        return
    except RuntimeError:
        logger.info("accelerate 不可用, 尝试重新安装中")

    try:
        pkg = f"accelerate=={importlib.metadata.version('accelerate')}"
    except Exception:
        pkg = "accelerate"

    try:
        run_cmd([Path(sys.executable).as_posix(), "-m", "pip", "uninstall", "accelerate", "-y"])
        pip_install(pkg, "--no-deps", use_uv=use_uv, custom_env=custom_env)
    except RuntimeError as e:
        logger.error("accelerate 重新安装发生错误: %s", e)
        raise RuntimeError(f"accelerate 重新安装发生错误: {e}") from e
