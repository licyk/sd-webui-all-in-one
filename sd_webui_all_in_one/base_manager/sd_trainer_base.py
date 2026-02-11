import os
from pathlib import Path
from typing import Any, Callable, TypeAlias, Literal, TypedDict, get_args

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_git_base_config_and_github_mirror,
    apply_hf_mirror,
    clone_repo,
    install_pytorch_for_webui,
    install_webui_model_from_library,
    launch_webui,
    pre_download_model_for_webui,
    prepare_pytorch_install_info,
    print_divider,
)
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.downloader import DownloadToolType, download_file
from sd_webui_all_in_one.env_check.fix_accelerate_bin import check_accelerate_bin
from sd_webui_all_in_one.env_check.fix_dependencies import py_dependency_checker
from sd_webui_all_in_one.env_check.fix_numpy import check_numpy
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.file_operations.file_manager import generate_dir_tree, get_file_list, remove_files
from sd_webui_all_in_one.mirror_manager import GITHUB_MIRROR_LIST, HUGGINGFACE_MIRROR_LIST, get_pypi_mirror_config
from sd_webui_all_in_one.model_downloader.base import ModelDownloadUrlType
from sd_webui_all_in_one.optimize.cuda_malloc import get_cuda_malloc_var
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceType
from sd_webui_all_in_one.utils import ANSIColor
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR

logger = get_logger(
    name="SD Trainer Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


SDTrainerBranchType: TypeAlias = Literal[
    "sd_trainer_main",
    "kohya_gui_main",
]
"""SD Trainer 分支类型"""

SD_TRAINER_BRANCH_LIST: list[str] = list(get_args(SDTrainerBranchType))
"""SD Trainer 分支类型列表"""


class SDTrainerBranchInfo(TypedDict):
    """SD Trainer 分支信息"""

    name: str
    """SD Trainer 分支名称"""

    dtype: SDTrainerBranchType
    """SD Trainer 分支类型"""

    url: str
    """SD Trainer 分支的 Git 仓库地址"""

    branch: str
    """SD Trainer 的 Git 分支名称"""

    use_submodule: bool
    """SD Trainer 分支中是否包含 Git 子模块"""


SD_TRAINER_BRANCH_INFO_DICT: list[SDTrainerBranchInfo] = [
    {
        "name": "Akegarasu - SD-Trainer 分支",
        "dtype": "sd_trainer_main",
        "url": "https://github.com/Akegarasu/lora-scripts",
        "branch": "main",
        "use_submodule": False,
    },
    {
        "name": "bmaltais - Kohya GUI 分支",
        "dtype": "kohya_gui_main",
        "url": "https://github.com/bmaltais/kohya_ss",
        "branch": "master",
        "use_submodule": True,
    },
]
"""SD Trainer 分支信息字典"""


def display_sd_trainer_branch_list(
    branch_list: list[SDTrainerBranchInfo],
) -> None:
    """显示 SD Trainer 分支列表

    Args:
        branch_list (list[SDTrainerBranchInfo]):
            SD Trainer 分支信息列表
    """
    for index, info in enumerate(branch_list, start=1):
        name = info["name"]
        dtype = info["dtype"]
        print(f"- {ANSIColor.GOLD}{index}{ANSIColor.RESET}、{ANSIColor.WHITE}{name}{ANSIColor.RESET} ({ANSIColor.BLUE}{dtype}{ANSIColor.RESET})")


def install_sd_trainer(
    sd_trainer_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    install_branch: SDTrainerBranchType | None = None,
    no_pre_download_model: bool | None = False,
    use_cn_model_mirror: bool | None = True,
) -> None:
    """安装 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        pytorch_mirror_type (PyTorchDeviceType | None):
            设置使用的 PyTorch 镜像源类型
        custom_pytorch_package (str | None):
            自定义 PyTorch 软件包版本声明, 例如: `torch==2.3.0+cu118 torchvision==0.18.0+cu118`
        custom_xformers_package (str | None):
            自定义 xFormers 软件包版本声明, 例如: `xformers===0.0.26.post1+cu118`
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        install_branch (SDTrainerBranchType | None):
            安装的 SD Trainer 分支
        no_pre_download_model (bool | None):
            是否禁用预下载模型
        use_cn_model_mirror (bool | None):
            是否使用国内镜像下载模型

    Raises:
        ValueError:
            安装的 SD Trainer 分支未知时
        FileNotFoundError:
            SD Trainer 依赖文件缺失时
    """
    logger.info("准备 SD Trainer 安装配置")

    # 准备 SD Trainer 安装分支信息
    need_switch_branch = True
    if install_branch is None:
        need_switch_branch = False
        install_branch = SD_TRAINER_BRANCH_LIST[0]

    if install_branch not in SD_TRAINER_BRANCH_LIST:
        raise ValueError(f"未知的 SD Trainer 类型: {install_branch}")

    for info in SD_TRAINER_BRANCH_INFO_DICT:
        if info["dtype"] == install_branch:
            branch_info = info
            break

    # 准备 PyTorch 安装信息
    pytorch_package, xformers_package, custom_env_pytorch = prepare_pytorch_install_info(
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=custom_pytorch_package,
        custom_xformers_package=custom_xformers_package,
        use_cn_mirror=use_pypi_mirror,
    )

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(use_pypi_mirror)

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=custom_env,
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    logger.debug("安装的 PyTorch 版本: %s", pytorch_package)
    logger.debug("安装的 xformers: %s", xformers_package)

    logger.info("SD Trainer 安装配置准备完成")
    logger.info("开始安装 SD Trainer, 安装路径: %s", sd_trainer_path)
    logger.info("安装的 SD Trainer 分支: '%s'", branch_info["name"])

    logger.info("安装 SD Trainer 内核中")
    clone_repo(
        repo=branch_info["url"],
        path=sd_trainer_path,
    )
    git_warpper.update_submodule(sd_trainer_path)

    if need_switch_branch:
        logger.info("切换 SD Trainer 分支中")
        git_warpper.switch_branch(
            path=sd_trainer_path,
            branch=branch_info["branch"],
            new_url=branch_info["url"],
            recurse_submodules=branch_info["use_submodule"],
        )

    install_pytorch_for_webui(
        pytorch_package=pytorch_package,
        xformers_package=xformers_package,
        custom_env=custom_env_pytorch,
        use_uv=use_uv,
    )

    req_path = sd_trainer_path / "requirements.txt"
    if not req_path.is_file():
        raise FileNotFoundError("未找到 SD Trainer 依赖文件记录表, 请检查 SD Trainer 文件是否完整")

    logger.info("安装 SD Trainer 依赖中")
    install_requirements(
        path=req_path,
        use_uv=use_uv,
        custom_env=custom_env,
        cwd=sd_trainer_path,
    )

    if not no_pre_download_model:
        pre_download_model_for_webui(
            dtype="sd_trainer",
            model_path=sd_trainer_path / "sd-models",
            webui_base_path=sd_trainer_path,
            model_name="ChenkinNoob-XL-V0.2",
            download_resource_type="modelscope" if use_cn_model_mirror else "huggingface",
        )

    logger.info("安装 SD Trainer 完成")


def switch_sd_trainer_branch(
    sd_trainer_path: Path,
    branch: SDTrainerBranchType | None = None,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    interactive_mode: bool | None = False,
    list_only: bool | None = False,
) -> None:
    """切换 SD Trainer 分支

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        branch (SDTrainerBranchType | None):
            要切换的 SD Trainer 分支
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        interactive_mode (bool | None):
            是否启用交互模式
        list_only (bool | None):
            是否仅列出分支列表并退出

    Raises:
        ValueError:
            传入未知的 SD Trainer 分支时
    """

    def _switch(
        input_branch: SDTrainerBranchType | None = None,
        input_index: int | None = None,
    ) -> None:
        nonlocal branch
        if input_index is not None:
            if not 0 < input_index <= len(SD_TRAINER_BRANCH_INFO_DICT):
                raise ValueError(f"索引值 {input_index} 超出范围, 有效范围为: 1 ~ {len(SD_TRAINER_BRANCH_INFO_DICT)}")
            branch_info = SD_TRAINER_BRANCH_INFO_DICT[input_index - 1]
        elif input_branch is not None:
            if input_branch not in SD_TRAINER_BRANCH_LIST:
                raise ValueError(f"未知的 SD Trainer 分支: '{input_branch}'")
            branch_info = [x for x in SD_TRAINER_BRANCH_INFO_DICT if input_branch == x["dtype"]][0]
        else:
            raise ValueError("需要提供 `branch` 或 `index` 才能进行分支切换")

        # 准备 Git 配置
        custom_env = apply_git_base_config_and_github_mirror(
            use_github_mirror=use_github_mirror,
            custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
            origin_env=os.environ.copy(),
        )
        os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

        logger.info("切换 SD Trainer 分支到 %s", branch_info["name"])
        git_warpper.switch_branch(
            path=sd_trainer_path,
            branch=branch_info["branch"],
            new_url=branch_info["url"],
            recurse_submodules=branch_info["use_submodule"],
        )
        logger.info("切换 SD Trainer 分支完成")

    if list_only:
        print_divider("=")
        display_sd_trainer_branch_list(SD_TRAINER_BRANCH_INFO_DICT)
        print_divider("=")
        return

    if interactive_mode:
        input_err = (0, None)
        while True:
            print_divider("=")
            display_sd_trainer_branch_list(SD_TRAINER_BRANCH_INFO_DICT)
            print_divider("=")

            i, m = input_err
            if i == 1:
                logger.warning("输入有误, 请重试")
            elif i == 2:
                logger.warning("输入的数字有误, %s, 请重新输入", m)
            input_err = (0, None)

            print(
                "请选择要切换的 SD Trainer 分支\n"
                "提示:\n"
                "1. 输入数字后回车即可选择切换到指定的分支\n"
                "2. 输入 exit 后回车退出分支切换"
            )
            user_input = input("==> ").strip()

            if user_input == "exit":
                return

            try:
                index = int(user_input)
            except Exception:
                input_err = (1, None)
                continue

            try:
                _switch(input_index=index)
                return
            except ValueError as e:
                input_err = (2, str(e))
                continue
    else:
        _switch(input_branch=branch)


def update_sd_trainer(
    sd_trainer_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    logger.info("更新 SD Trainer 中")
    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    git_warpper.update(sd_trainer_path)

    logger.info("更新 SD Trainer 完成")


def check_sd_trainer_env(
    sd_trainer_path: Path,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
) -> None:
    """检查 SD Trainer 运行环境

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源

    Raises:
        AggregateError:
            检查 SD Trainer 环境发生错误时
        FileNotFoundError:
            未找到 SD Trainer 依赖文件记录表时
    """
    req_path = sd_trainer_path / "requirements.txt"

    if not req_path.is_file():
        raise FileNotFoundError("未找到 SD Trainer 依赖文件记录表, 请检查文件是否完整")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(
        use_cn_mirror=use_pypi_mirror,
        origin_env=custom_env,
    )

    # 检查任务列表
    tasks: list[tuple[Callable, dict[str, Any]]] = [
        (py_dependency_checker, {"requirement_path": req_path, "name": "SD Trainer", "use_uv": use_uv, "custom_env": custom_env}),
        (fix_torch_libomp, {}),
        (check_accelerate_bin, {"base_path": sd_trainer_path, "use_uv": use_uv, "custom_env": custom_env}),
        (check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": False, "custom_env": custom_env}),
        (check_numpy, {"use_uv": use_uv, "custom_env": custom_env}),
    ]
    err: list[Exception] = []

    for func, kwargs in tasks:
        try:
            func(**kwargs)
        except Exception as e:
            err.append(e)
            logger.error("执行 '%s' 时发生错误: %s", func.__name__, e)

    if err:
        raise AggregateError("检查 SD Trainer 环境时发生错误", err)

    logger.info("检查 SD Trainer 环境完成")


def launch_sd_trainer(
    sd_trainer_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool | None = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
    use_cuda_malloc: bool | None = True,
) -> None:
    """启动 SD Trainer

    Args:
        sd_trainer_path (list[str] | None):
            启动 SD Trainer 的参数
        use_hf_mirror (bool | None):
            是否启用 HuggingFace 镜像源
        custom_hf_mirror (str | list[str] | None):
            自定义 HuggingFace 镜像源
        use_github_mirror (bool | None):
            是否启用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool | None):
            是否启用 PyPI 镜像源
        use_cuda_malloc (bool | None):
            是否启用 CUDA Malloc 显存优化
    """
    logger.info("准备 SD Trainer 启动环境")

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    custom_env = apply_hf_mirror(
        use_hf_mirror=use_hf_mirror,
        custom_hf_mirror=(HUGGINGFACE_MIRROR_LIST if custom_hf_mirror is None else custom_hf_mirror) if use_hf_mirror else None,
        origin_env=custom_env,
    )

    custom_env = get_pypi_mirror_config(
        use_cn_mirror=use_pypi_mirror,
        origin_env=custom_env,
    )

    if use_cuda_malloc:
        cuda_malloc_config = get_cuda_malloc_var()
        if cuda_malloc_config is not None:
            custom_env["PYTORCH_ALLOC_CONF"] = cuda_malloc_config
            custom_env["PYTORCH_CUDA_ALLOC_CONF"] = cuda_malloc_config

    logger.info("启动 SD Trainer 中")
    launch_webui(
        webui_path=sd_trainer_path,
        launch_script="gui.py" if (sd_trainer_path / "gui.py").is_file() else "kohya_gui.py",
        webui_name="SD Trainer",
        launch_args=launch_args,
        custom_env=custom_env,
    )


def install_sd_trainer_model_from_library(
    sd_trainer_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = "aria2",
    interactive_mode: bool | None = False,
    list_only: bool | None = False,
) -> None:
    """为 SD Trainer 下载模型, 使用模型库进行下载

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        download_resource_type (ModelDownloadUrlType | None):
            模型下载源类型
        model_name (str | None):
            下载的模型名称
        model_index (int | None):
            下载的模型在列表中的索引值, 索引值从 1 开始. 当同时提供 `model_name` 和 `model_index` 时, 优先使用 `model_index` 查找模型
        downloader (DownloadToolType | None):
            下载模型使用的工具
        interactive_mode (bool | None):
            是否启用交互模式
        list_only (bool | None):
            是否仅列出模型列表并退出
    """
    install_webui_model_from_library(
        webui_path=sd_trainer_path,
        dtype="sd_trainer",
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )


def install_sd_trainer_model_from_url(
    sd_trainer_path: Path,
    model_url: str,
    model_type: str,
    downloader: DownloadToolType | None = "aria2",
) -> None:
    """从链接下载模型到 SD Trainer

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        model_url (str):
            模型下载地址
        model_type (str):
            模型的类型
        downloader (DownloadToolType | None):
            下载模型使用的工具
    """
    model_path = sd_trainer_path / "sd-models" / model_type
    download_file(
        url=model_url,
        path=model_path,
        tool=downloader,
    )


def list_sd_trainer_models(
    sd_trainer_path: Path,
) -> None:
    """列出 SD Trainer 的模型目录

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
    """
    models_path = sd_trainer_path / "sd-models"
    logger.info("SD Trainer 模型列表")
    for m in models_path.iterdir():
        logger.info("%s 的模型列表", m.name)
        generate_dir_tree(m)
        print("\n\n")


def uninstall_sd_trainer_model(
    sd_trainer_path: Path,
    model_name: str,
    model_type: str | None = None,
    interactive_mode: bool | None = False,
) -> None:
    """卸载 SD Trainer 中的模型

    Args:
        sd_trainer_path (Path):
            SD Trainer 根目录
        model_name (str):
            模型名称
        model_type (str | None):
            模型的类型
        interactive_mode (bool | None):
            是否启用交互模式

    Raises:
        FileNotFoundError:
            未找到要删除的模型时
    """
    if model_type is None:
        model_path = sd_trainer_path / "sd-models"
    else:
        model_path = sd_trainer_path / "sd-models" / model_type

    model_list = get_file_list(model_path)
    delete_list = [x for x in model_list if model_name.lower() in x.name.lower()]

    if not delete_list:
        raise FileNotFoundError(f"模型 '{model_name}' 不存在")

    logger.info("根据 '%s' 模型名找到的已有模型列表:\n", model_name)
    for d in delete_list:
        print(f"- `{d}`")

    print()
    if interactive_mode:
        logger.info("是否删除以上模型?")
        if input("[y/N]").strip().lower() not in ["yes", "y"]:
            logger.info("取消模型删除操作")
            return

    for i in delete_list:
        logger.info("删除模型: %s", i)
        remove_files(i)

    logger.info("模型删除完成")
