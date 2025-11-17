"""依赖环境管理工具"""

import os
import sys
from typing import Any
from pathlib import Path


from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR


logger = get_logger(
    name="Env Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def pip_install(
    *args: Any,
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
) -> str:
    """使用 Pip / uv 安装 Python 软件包

    Args:
        *args (Any): 要安装的 Python 软件包 (可使用 Pip / uv 命令行参数, 如`--upgrade`, `--force-reinstall`)
        use_uv (bool | None): 使用 uv 代替 Pip 进行安装, 当 uv 安装 Python 软件包失败时, 将回退到 Pip 进行重试
        custom_env (dict[str, str] | None): 自定义环境变量
        cwd (Path | str | None): 执行 Pip / uv 时的起始路径
    Returns:
        str: 命令的执行输出
    Raises:
        RuntimeError: 当 uv 和 pip 都无法安装软件包时抛出异常
    """
    if custom_env is None:
        custom_env = os.environ.copy()
    cwd = Path(cwd) if not isinstance(cwd, Path) and cwd is not None else cwd
    if use_uv:
        try:
            run_cmd(["uv", "--version"], live=False, custom_env=custom_env)
        except Exception as _:
            logger.info("安装 uv 中")
            run_cmd(
                [Path(sys.executable).as_posix(), "-m", "pip", "install", "uv"],
                custom_env=custom_env,
            )

        try:
            return run_cmd(["uv", "pip", "install", *args], custom_env=custom_env, cwd=cwd)
        except Exception as e:
            logger.warning(
                "检测到 uv 安装 Python 软件包失败, 尝试回退到 Pip 重试 Python 软件包安装: %s",
                e,
            )
            return run_cmd(
                [Path(sys.executable).as_posix(), "-m", "pip", "install", *args],
                custom_env=custom_env,
                cwd=cwd,
            )
    else:
        return run_cmd(
            [Path(sys.executable).as_posix(), "-m", "pip", "install", *args],
            custom_env=custom_env,
            cwd=cwd,
        )


def install_manager_depend(
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
    custom_sys_pkg_cmd: list[list[str]] | list[str] | None = None,
) -> bool:
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
        use_uv (bool | None): 使用 uv 代替 Pip 进行安装, 当 uv 安装 Python 软件包失败时, 将回退到 Pip 进行重试
        custom_env (dict[str, str] | None): 自定义环境变量
        custom_sys_pkg_cmd (list[list[str]] | list[str] | None): 自定义调用系统包管理器命令
    Returns:
        bool: 组件安装结果
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
                "p7zip-full",
                "unzip",
                "tree",
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
            "--upgrade",
            use_uv=use_uv,
            custom_env=custom_env,
        )
        for cmd in custom_sys_pkg_cmd:
            run_cmd(cmd, custom_env=custom_env)
        return True
    except Exception as e:
        logger.error("安装自身组件依赖失败: %s", e)
        return False


def install_pytorch(
    torch_package: str | list[str] | None = None,
    xformers_package: str | list[str] | None = None,
    pytorch_mirror: str | None = None,
    use_uv: bool | None = True,
) -> bool:
    """安装 PyTorch / xFormers

    Args:
        torch_package (str | list[str] | None): PyTorch 软件包名称和版本信息, 如`torch==2.0.0 torchvision==0.15.1` / `["torch==2.0.0", "torchvision==0.15.1"]`
        xformers_package (str | list[str] | None): xFormers 软件包名称和版本信息, 如`xformers==0.0.18` / `["xformers==0.0.18"]`
        pytorch_mirror (str | None): 指定安装 PyTorch / xFormers 时使用的镜像源
        use_uv (bool | None): 是否使用 uv 代替 Pip 进行安装
    Returns:
        bool: 安装 PyTorch / xFormers 成功时返回`True`
    """
    custom_env = os.environ.copy()
    if pytorch_mirror is not None:
        logger.info("使用自定义 PyTorch 镜像源: %s", pytorch_mirror)
        custom_env.pop("PIP_EXTRA_INDEX_URL", None)
        custom_env.pop("PIP_FIND_LINKS", None)
        custom_env.pop("UV_INDEX", None)
        custom_env.pop("UV_FIND_LINKS", None)
        custom_env["PIP_INDEX_URL"] = pytorch_mirror
        custom_env["UV_DEFAULT_INDEX"] = pytorch_mirror

    if torch_package is not None:
        logger.info("安装 PyTorch 中")
        torch_package = torch_package.split() if isinstance(torch_package, str) else torch_package
        try:
            pip_install(*torch_package, use_uv=use_uv)
            logger.info("安装 PyTorch 成功")
        except Exception as e:
            logger.error("安装 PyTorch 时发生错误: %s", e)
            return False

    if xformers_package is not None:
        logger.info("安装 xFormers 中")
        xformers_package = xformers_package.split() if isinstance(xformers_package, str) else xformers_package
        try:
            pip_install(*xformers_package, use_uv=use_uv)
            logger.info("安装 xFormers 成功")
        except Exception as e:
            logger.error("安装 xFormers 时发生错误: %s", e)
            return False

    return True


def install_requirements(
    path: Path | str,
    use_uv: bool | None = True,
    custom_env: dict[str, str] | None = None,
    cwd: Path | str | None = None,
) -> bool:
    """从 requirements.txt 文件指定安装的依赖

    Args:
        path (Path | str): requirements.txt 文件路径
        use_uv (bool | None): 是否使用 uv 代替 Pip 进行安装
        custom_env (dict[str, str] | None): 自定义环境变量
        cwd (Path | str | None): 执行 Pip / uv 时的起始路径
    Returns:
        bool: 安装依赖成功时返回`True`
    """
    if custom_env is None:
        custom_env = os.environ.copy()
    cwd = Path(cwd) if not isinstance(cwd, Path) and cwd is not None else cwd
    path = Path(path) if not isinstance(path, Path) and path is not None else path

    try:
        logger.info("从 %s 安装 Python 软件包中", path)
        pip_install("-r", path.as_posix(), use_uv=use_uv, custom_env=custom_env, cwd=cwd)
        logger.info("从 %s 安装 Python 软件包成功", path)
        return True
    except Exception as e:
        logger.info("从 %s 安装 Python 软件包时发生错误: %s", path, e)
        return False
