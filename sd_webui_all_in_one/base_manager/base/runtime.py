"""WebUI 通用启动流程。"""

import os
import sys
from pathlib import Path

from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.utils import (
    print_divider,
    append_python_path,
)
from sd_webui_all_in_one.custom_exceptions import WebUiRuntimeError
from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    HOTPATCHER_ENV_PREFIX,
    ensure_hotpatcher_pythonpath_first,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def launch_webui(
    webui_path: Path,
    launch_script: str | Path,
    webui_name: str | None = None,
    launch_args: list[str] | None = None,
    custom_env: dict[str, str] | None = None,
) -> None:
    """运行 WebUI

    Args:
        webui_path (Path):
            WebUI 的根目录
        launch_script (str | Path):
            启动 WebUI 的脚本路径, 相对路径会以 WebUI 根目录为基准解析
        webui_name (str | None):
            WebUI 的名称
        launch_args (list[str] | None):
            启动 WebUI 的参数
        custom_env (dict[str, str] | None):
            自定义环境变量

    Raises:
        WebUiRuntimeError:
            运行 WebUI 时出现错误
    """
    if launch_args is None:
        launch_args = []

    if webui_name is None:
        webui_name = "WebUI"

    if custom_env is None:
        custom_env = os.environ.copy()

    custom_env = append_python_path(
        new_path=webui_path,
        origin_env=custom_env,
    )
    if any(key.startswith(HOTPATCHER_ENV_PREFIX) for key in custom_env):
        custom_env = ensure_hotpatcher_pythonpath_first(custom_env)

    launch_script_path = Path(launch_script)
    if not launch_script_path.is_absolute():
        launch_script_path = webui_path / launch_script_path

    cmd = [Path(sys.executable).as_posix(), launch_script_path.as_posix()] + launch_args
    print_divider("=")
    try:
        try:
            run_cmd(cmd, custom_env=custom_env, cwd=webui_path)
        finally:
            print_divider("=")
    except KeyboardInterrupt:
        logger.info("已关闭 %s", webui_name)
    except RuntimeError as e:
        raise WebUiRuntimeError(f"运行 {webui_name} 时出现错误: {e}") from e
