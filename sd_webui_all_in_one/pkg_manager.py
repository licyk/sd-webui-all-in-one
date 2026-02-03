"""依赖环境管理工具"""

import os
import sys
from typing import Any
from pathlib import Path

from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.updater import check_and_update_uv, check_and_update_pip

logger = get_logger(
    name="Env Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def pip_install(
    *args: Any,
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> None:
    """使用 Pip / uv 安装 Python 软件包

    Args:
        *args (Any):
            要安装的 Python 软件包 (可使用 Pip / uv 命令行参数, 如`--upgrade`, `--force-reinstall`)
        use_uv (bool | None):
            使用 uv 代替 Pip 进行安装, 当 uv 安装 Python 软件包失败时, 将回退到 Pip 进行重试
        custom_env (dict[str, str] | None):
            自定义环境变量
        cwd (Path | None):
            执行 Pip / uv 时的起始路径

    Raises:
        RuntimeError: 当 uv 和 pip 都无法安装软件包时抛出异常
    """

    if custom_env is None:
        custom_env = os.environ.copy()

    check_and_update_pip(custom_env=custom_env)

    if use_uv:
        custom_env["UV_PYTHON"] = sys.executable
        check_and_update_uv(custom_env=custom_env)

        try:
            run_cmd(["uv", "pip", "install", *args], custom_env=custom_env, cwd=cwd)
            return
        except RuntimeError as e:
            logger.warning("检测到 uv 安装 Python 软件包失败, 尝试回退到 Pip 重试 Python 软件包安装: %s", e)

    try:
        run_cmd(
            [Path(sys.executable).as_posix(), "-m", "pip", "install", *args],
            custom_env=custom_env,
            cwd=cwd,
        )
    except RuntimeError as e:
        logger.error("安装 Python 软件包失败: %s", e)
        raise RuntimeError(f"安装 Python 软件包发生错误: {e}") from e


def install_manager_depend(
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
    custom_sys_pkg_cmd: list[list[str]] | list[str] | None = None,
) -> None:
    """安装自身组件依赖

    自定义命令的例子:
    ```python
    custom_sys_pkg_cmd = [
        ["apt", "update"],
        ["apt", "install", "aria2", "google-perftools", "p7zip-full", "unzip", "tree", "git", "git-lfs", "-y"]
    ]
    # 另一种等效形式
    custom_sys_pkg_cmd = [
        "apt update",
        "apt install aria2 google-perftools p7zip-full unzip tree git git-lfs -y",
    ]
    ```
    这将分别执行两条命令:
    ```
    1. apt update
    2. apt install aria2 google-perftools p7zip-full unzip tree git git-lfs -y
    ```

    Args:
        use_uv (bool | None):
            使用 uv 代替 Pip 进行安装, 当 uv 安装 Python 软件包失败时, 将回退到 Pip 进行重试
        custom_env (dict[str, str] | None):
            自定义环境变量
        custom_sys_pkg_cmd (list[list[str]] | list[str] | None):
            自定义调用系统包管理器命令

    Raises:
        RuntimeError:
            安装自身组件依赖失败时
    """
    if custom_env is None:
        custom_env = os.environ.copy()
    if custom_sys_pkg_cmd is None:
        custom_sys_pkg_cmd = [
            ["apt", "update"],
            [
                "apt",
                "install",
                "aria2",
                "google-perftools",
                "git",
                "git-lfs",
                "-y",
            ],
        ]
    try:
        logger.info("安装自身组件依赖中")
        pip_install("uv", "--upgrade", use_uv=False, custom_env=custom_env)
        pip_install(
            "modelscope",
            "huggingface_hub",
            "hf-xet",
            "requests",
            "tqdm",
            "wandb",
            "zstandard",
            "py7zr",
            "rarfile",
            "--upgrade",
            use_uv=use_uv,
            custom_env=custom_env,
        )
        for cmd in custom_sys_pkg_cmd:
            run_cmd(cmd, custom_env=custom_env)
    except RuntimeError as e:
        logger.error("安装自身组件依赖失败: %s", e)
        raise RuntimeError(f"安装自身组件依赖失败: {e}") from e


def install_pytorch(
    torch_package: str | list[str] | None = None,
    xformers_package: str | list[str] | None = None,
    custom_env: dict[str, str] | None = None,
    use_uv: bool | None = True,
) -> None:
    """安装 PyTorch / xFormers

    Args:
        torch_package (str | list[str] | None):
            PyTorch 软件包名称和版本信息, 如`torch==2.0.0 torchvision==0.15.1` / `["torch==2.0.0", "torchvision==0.15.1"]`
        xformers_package (str | list[str] | None):
            xFormers 软件包名称和版本信息, 如`xformers==0.0.18` / `["xformers==0.0.18"]`
        custom_env (dict[str, str] | None):
            包含 PyPI 镜像配置的环境变量字典
        use_uv (bool | None):
            是否使用 uv 代替 Pip 进行安装

    Raises:
        RuntimeError:
            安装 PyTorch / xFormers 发生错误时
    """
    if custom_env is None:
        custom_env = os.environ.copy()

    logger.debug("使用的环境变量: %s", custom_env)

    if torch_package is not None:
        torch_package = torch_package.split() if isinstance(torch_package, str) else torch_package
        try:
            logger.info("安装 PyTorch 中, 版本: '%s'", " ".join(torch_package))
            pip_install(*torch_package, use_uv=use_uv, custom_env=custom_env)
            logger.info("安装 PyTorch 成功")
        except RuntimeError as e:
            logger.error("安装 PyTorch 时发生错误: %s", e)
            raise RuntimeError(f"安装 PyTorch 时发生错误: {e}") from e

    if xformers_package is not None:
        xformers_package = xformers_package.split() if isinstance(xformers_package, str) else xformers_package
        try:
            logger.info("安装 xFormers 中, 版本: '%s'", " ".join(xformers_package))
            pip_install(*xformers_package, use_uv=use_uv, custom_env=custom_env)
            logger.info("安装 xFormers 成功")
        except RuntimeError as e:
            logger.error("安装 xFormers 时发生错误: %s", e)
            raise RuntimeError(f"安装 xFormers 时发生错误: {e}") from e


def install_requirements(
    path: Path,
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> bool:
    """从 requirements.txt 文件指定安装的依赖

    Args:
        path (Path):
            requirements.txt 文件路径
        use_uv (bool | None):
            是否使用 uv 代替 Pip 进行安装
        custom_env (dict[str, str] | None):
            自定义环境变量
        cwd (Path | None):
            执行 Pip / uv 时的起始路径

    Raises:
        RuntimeError:
            安装依赖发生错误时
    """
    if custom_env is None:
        custom_env = os.environ.copy()

    try:
        logger.info("从 %s 安装 Python 软件包中", path)
        pip_install("-r", path.as_posix(), use_uv=use_uv, custom_env=custom_env, cwd=cwd)
        logger.info("从 %s 安装 Python 软件包成功", path)
    except RuntimeError as e:
        logger.info("从 %s 安装 Python 软件包时发生错误: %s", path, e)
        raise RuntimeError(f"从 '{path}' 安装 Python 软件包时发生错误: {e}") from e
