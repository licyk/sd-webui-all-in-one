"""ComfyUI 管理器模块"""

import os
from pathlib import Path
from typing import (
    Any,
    Callable,
    TypedDict,
)
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.base_manager.base import (
    apply_github_raw_file_mirror,
    apply_git_base_config_and_github_mirror,
    apply_hf_mirror,
    clone_repo,
    get_repo_name_from_url,
    install_pytorch_for_webui,
    install_webui_model_from_library,
    launch_webui,
    pre_download_model_for_webui,
    prepare_pytorch_install_info,
)
from sd_webui_all_in_one.base_manager.hotpatcher_manager import DEFAULT_RUNTIME_PORT, apply_hotpatcher_launch_env
from sd_webui_all_in_one.base_manager.repository_inspector import inspect_repository
from sd_webui_all_in_one.base_manager.comfy_registry import (
    read_comfy_registry_info,
    read_comfy_registry_nightly_id,
    switch_comfy_registry_node_version,
    install_comfy_registry_node,
)
from sd_webui_all_in_one.base_manager.snapshot import (
    ExtensionSnapshot,
    WebUiSnapshot,
    build_webui_snapshot,
    collect_repository_snapshot,
)
from sd_webui_all_in_one.base_manager.version_manager import ManagedExtension
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.downloader import (
    DownloadToolType,
    download_file,
)
from sd_webui_all_in_one.file_manager import (
    copy_files,
    generate_dir_tree,
    get_file_list,
    move_files,
    remove_files,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.config import (
    LOGGER_LEVEL,
    LOGGER_COLOR,
    ROOT_PATH,
    LOGGER_NAME,
)
from sd_webui_all_in_one.mirror_manager import (
    GITHUB_MIRROR_LIST,
    HUGGINGFACE_MIRROR_LIST,
    get_pypi_mirror_config,
)
from sd_webui_all_in_one.model_downloader import ModelDownloadUrlType
from sd_webui_all_in_one.optimize import (
    get_cuda_malloc_var,
    apply_pytorch_alloc_conf,
)
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.pytorch_manager import PyTorchDeviceType
from sd_webui_all_in_one.env_check import (
    py_dependency_checker,
    fix_torch_libomp,
    check_onnxruntime_gpu,
    comfyui_conflict_analyzer,
    check_comfyui_manager_dependence,
    check_torch_version,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


class ComfyUiCustomNodeInfo(TypedDict):
    """ComfyUI 扩展信息"""

    name: str
    """ComfyUI 扩展名称"""

    url: str
    """ComfyUI 扩展的 Git 仓库地址"""

    save_dir: str
    """ComfyUI 扩展安装路径 (使用相对路径, 初始位置为 WebUI 的根目录)"""


ComfyUiCustomNodeInfoList = list[ComfyUiCustomNodeInfo]
"""ComfyUI 扩展信息列表"""

COMFYUI_CUSTOM_NODES_INFO_DICT: ComfyUiCustomNodeInfoList = [
    {
        "name": "ComfyUI-Manager",
        "url": "https://github.com/Comfy-Org/ComfyUI-Manager",
        "save_dir": "custom_nodes/ComfyUI-Manager",
    },
    {
        "name": "comfyui_controlnet_aux",
        "url": "https://github.com/Fannovel16/comfyui_controlnet_aux",
        "save_dir": "custom_nodes/comfyui_controlnet_aux",
    },
    {
        "name": "ComfyUI-Advanced-ControlNet",
        "url": "https://github.com/Kosinkadink/ComfyUI-Advanced-ControlNet",
        "save_dir": "custom_nodes/ComfyUI-Advanced-ControlNet",
    },
    {
        "name": "ComfyUI_IPAdapter_plus",
        "url": "https://github.com/cubiq/ComfyUI_IPAdapter_plus",
        "save_dir": "custom_nodes/ComfyUI_IPAdapter_plus",
    },
    {
        "name": "ComfyUI-Marigold",
        "url": "https://github.com/kijai/ComfyUI-Marigold",
        "save_dir": "custom_nodes/ComfyUI-Marigold",
    },
    {
        "name": "ComfyUI-WD14-Tagger",
        "url": "https://github.com/pythongosssss/ComfyUI-WD14-Tagger",
        "save_dir": "custom_nodes/ComfyUI-WD14-Tagger",
    },
    {
        "name": "ComfyUI-Custom-Scripts",
        "url": "https://github.com/pythongosssss/ComfyUI-Custom-Scripts",
        "save_dir": "custom_nodes/ComfyUI-Custom-Scripts",
    },
    {
        "name": "ComfyUI_UltimateSDUpscale",
        "url": "https://github.com/ssitu/ComfyUI_UltimateSDUpscale",
        "save_dir": "custom_nodes/ComfyUI_UltimateSDUpscale",
    },
    {
        "name": "ComfyUI_Custom_Nodes_AlekPet",
        "url": "https://github.com/AlekPet/ComfyUI_Custom_Nodes_AlekPet",
        "save_dir": "custom_nodes/ComfyUI_Custom_Nodes_AlekPet",
    },
    {
        "name": "comfyui-browser",
        "url": "https://github.com/talesofai/comfyui-browser",
        "save_dir": "custom_nodes/comfyui-browser",
    },
    {
        "name": "ComfyUI-Inspire-Pack",
        "url": "https://github.com/ltdrdata/ComfyUI-Inspire-Pack",
        "save_dir": "custom_nodes/ComfyUI-Inspire-Pack",
    },
    {
        "name": "ComfyUI_Comfyroll_CustomNodes",
        "url": "https://github.com/Suzie1/ComfyUI_Comfyroll_CustomNodes",
        "save_dir": "custom_nodes/ComfyUI_Comfyroll_CustomNodes",
    },
    {
        "name": "ComfyUI-Crystools",
        "url": "https://github.com/crystian/ComfyUI-Crystools",
        "save_dir": "custom_nodes/ComfyUI-Crystools",
    },
    {
        "name": "ComfyUI-TiledDiffusion",
        "url": "https://github.com/shiimizu/ComfyUI-TiledDiffusion",
        "save_dir": "custom_nodes/ComfyUI-TiledDiffusion",
    },
    {
        "name": "ComfyUI-Restart-Sampler",
        "url": "https://github.com/licyk/ComfyUI-Restart-Sampler",
        "save_dir": "custom_nodes/ComfyUI-Restart-Sampler",
    },
    {
        "name": "WeiLin-Comfyui-Tools",
        "url": "https://github.com/weilin9999/WeiLin-Comfyui-Tools",
        "save_dir": "custom_nodes/WeiLin-Comfyui-Tools",
    },
    {
        "name": "ComfyUI-HakuImg",
        "url": "https://github.com/licyk/ComfyUI-HakuImg",
        "save_dir": "custom_nodes/ComfyUI-HakuImg",
    },
    {
        "name": "ComfyUI-Easy-Use",
        "url": "https://github.com/yolain/ComfyUI-Easy-Use",
        "save_dir": "custom_nodes/ComfyUI-Easy-Use",
    },
    {
        "name": "rgthree-comfy",
        "url": "https://github.com/rgthree/rgthree-comfy",
        "save_dir": "custom_nodes/rgthree-comfy",
    },
]

COMFYUI_REPO_URL = "https://github.com/Comfy-Org/ComfyUI"
"""ComfyUI 仓库地址"""

COMFYUI_CUSTOM_NODE_LIST_PATH = "Comfy-Org/ComfyUI-Manager/refs/heads/main/custom-node-list.json"
"""ComfyUI-Manager 自定义节点列表 GitHub raw 路径"""

COMFYUI_CONFIG_PATH = ROOT_PATH / "base_manager" / "config" / "comfy.settings.json"
"""ComfyUI 预设配置文件路径"""


def set_comfyui_custom_node_list_mirror(
    custom_github_mirror: str | list[str] | None = None,
) -> str | None:
    """配置 ComfyUI 自定义节点列表镜像源

    Args:
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源列表

    Returns:
        str | None:
            自定义节点列表镜像 URL, 未启用或无可用镜像时返回 None
    """
    return apply_github_raw_file_mirror(
        raw_file_path=COMFYUI_CUSTOM_NODE_LIST_PATH,
        custom_github_mirror=custom_github_mirror,
    )


def install_comfyui_config(
    comfyui_path: Path,
) -> None:
    """安装 ComfyUI 配置文件

    Args:
        comfyui_path (Path):
            ComfyUI 根目录

    """
    config_path = comfyui_path / "user" / "default" / "comfy.settings.json"
    if not config_path.exists():
        copy_files(COMFYUI_CONFIG_PATH, config_path)


def install_comfyui(
    comfyui_path: Path,
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_pypi_mirror: bool = True,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    no_pre_download_extension: bool = False,
    no_pre_download_model: bool = False,
    model_download_resource_type: ModelDownloadUrlType | None = "modelscope",
) -> None:
    """安装 ComfyUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        pytorch_mirror_type (PyTorchDeviceType | None):
            设置使用的 PyTorch 镜像源类型
        custom_pytorch_package (str | None):
            自定义 PyTorch 软件包版本声明, 例如: `torch==2.3.0+cu118 torchvision==0.18.0+cu118`
        custom_xformers_package (str | None):
            自定义 xFormers 软件包版本声明, 例如: `xformers===0.0.26.post1+cu118`
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像源
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        no_pre_download_extension (bool):
            是否禁用预下载 ComfyUI 扩展
        no_pre_download_model (bool):
            是否禁用预下载模型
        model_download_resource_type (ModelDownloadUrlType | None):
            下载模型使用的下载源

    Raises:
        FileNotFoundError:
            ComfyUI 依赖文件缺失时
    """
    logger.info("准备 ComfyUI 安装配置")

    # 准备 PyTorch 安装信息
    pytorch_package, xformers_package, custom_env_pytorch = prepare_pytorch_install_info(
        pytorch_mirror_type=pytorch_mirror_type,
        custom_pytorch_package=custom_pytorch_package,
        custom_xformers_package=custom_xformers_package,
        use_cn_mirror=use_pypi_mirror,
    )

    # 准备扩展安装信息
    comfyui_custom_node_list = COMFYUI_CUSTOM_NODES_INFO_DICT.copy() if not no_pre_download_extension else []

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(use_pypi_mirror)

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=custom_env,
    )
    git_config_global = custom_env.get("GIT_CONFIG_GLOBAL")
    if git_config_global is not None:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_global

    logger.debug("安装的 PyTorch 版本: %s", pytorch_package)
    logger.debug("安装的 xformers: %s", xformers_package)
    logger.debug("安装的扩展信息: %s", comfyui_custom_node_list)

    logger.info("ComfyUI 安装配置准备完成")
    logger.info("开始安装 ComfyUI, 安装路径: %s", comfyui_path)

    logger.info("安装 ComfyUI 内核中")
    clone_repo(
        repo=COMFYUI_REPO_URL,
        path=comfyui_path,
    )

    if comfyui_custom_node_list:
        logger.info("安装 ComfyUI 扩展中")
        for info in comfyui_custom_node_list:
            clone_repo(
                repo=info["url"],
                path=comfyui_path / info["save_dir"],
            )

    install_pytorch_for_webui(
        pytorch_package=pytorch_package,
        xformers_package=xformers_package,
        custom_env=custom_env_pytorch,
        use_uv=use_uv,
    )

    requirements_path = comfyui_path / "requirements.txt"

    if not requirements_path.is_file():
        raise FileNotFoundError("未找到 ComfyUI 依赖文件记录表, 请检查 ComfyUI 文件是否完整")

    logger.info("安装 ComfyUI 依赖中")
    install_requirements(
        path=requirements_path,
        use_uv=use_uv,
        custom_env=custom_env,
        cwd=comfyui_path,
    )

    if not no_pre_download_model:
        pre_download_model_for_webui(
            dtype="comfyui",
            model_path=comfyui_path / "models" / "checkpoints",
            webui_base_path=comfyui_path,
            model_name="ChenkinNoob-XL-V0.2",
            download_resource_type=model_download_resource_type,
        )

    install_comfyui_config(comfyui_path)

    logger.info("安装 ComfyUI 完成")


def update_comfyui(
    comfyui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 ComfyUI

    Args:
        comfyui_path (Path):
            Stable DIffusion WebUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
    """
    logger.info("更新 ComfyUI 中")
    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    git_config_global = custom_env.get("GIT_CONFIG_GLOBAL")
    if git_config_global is not None:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_global

    git_warpper.update(comfyui_path)

    logger.info("更新 ComfyUI 完成")


def check_comfyui_env(
    comfyui_path: Path,
    install_conflict_component_requirement: bool = False,
    interactive_mode: bool = False,
    use_uv: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
) -> None:
    """检查 ComfyUI 运行环境

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        install_conflict_component_requirement (bool):
            检测到冲突依赖时是否按顺序安装组件依赖
        interactive_mode (bool):
            是否启用交互模式, 当检测到冲突依赖时将询问是否安装冲突组件依赖
        use_uv (bool):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool):
            是否使用国内 PyPI 镜像源

    Raises:
        AggregateError:
            检查 ComfyUI 环境发生错误时
        FileNotFoundError:
            未找到 ComfyUI 依赖文件记录表时
    """
    req_path = comfyui_path / "requirements.txt"

    if not req_path.is_file():
        raise FileNotFoundError("未找到 ComfyUI 依赖文件记录表, 请检查文件是否完整")

    # 准备安装依赖的 PyPI 镜像源
    custom_env = get_pypi_mirror_config(
        use_cn_mirror=use_pypi_mirror,
        origin_env=os.environ.copy(),
    )

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=custom_env,
    )
    git_config_global = custom_env.get("GIT_CONFIG_GLOBAL")
    if git_config_global is not None:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_global

    # 检查任务列表
    tasks: list[tuple[Callable, dict[str, Any]]] = [
        (py_dependency_checker, {"requirement_path": req_path, "name": "ComfyUI", "use_uv": use_uv, "custom_env": custom_env}),
        (check_comfyui_manager_dependence, {"comfyui_root_path": comfyui_path, "use_uv": use_uv, "custom_env": custom_env}),
        (
            comfyui_conflict_analyzer,
            {
                "comfyui_root_path": comfyui_path,
                "install_conflict_component_requirement": install_conflict_component_requirement,
                "interactive_mode": interactive_mode,
                "use_uv": use_uv,
                "custom_env": custom_env,
            },
        ),
        (fix_torch_libomp, {}),
        (check_torch_version, {}),
        (check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": True, "custom_env": custom_env}),
    ]
    err: list[Exception] = []

    for func, kwargs in tasks:
        try:
            func(**kwargs)
        except Exception as e:
            err.append(e)
            logger.error("执行 '%s' 时发生错误: %s", getattr(func, "__name__", repr(func)), e)

    if err:
        raise AggregateError("检查 ComfyUI 环境时发生错误", err)

    logger.info("检查 ComfyUI 环境完成")


def launch_comfyui(
    comfyui_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
    use_cuda_malloc: bool = True,
    enable_hotpatcher: bool = False,
    hotpatcher_config_path: str | Path | None = None,
    hotpatcher_port: int = DEFAULT_RUNTIME_PORT,
    enable_hotpatcher_runtime: bool = False,
) -> None:
    """启动 ComfyUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        launch_args (list[str] | None):
            启动 ComfyUI 的参数
        use_hf_mirror (bool):
            是否启用 HuggingFace 镜像源
        custom_hf_mirror (str | list[str] | None):
            自定义 HuggingFace 镜像源
        use_github_mirror (bool):
            是否启用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        use_pypi_mirror (bool):
            是否启用 PyPI 镜像源
        use_cuda_malloc (bool):
            是否启用 CUDA Malloc 显存优化
        enable_hotpatcher (bool):
            是否启用补丁系统注入
        hotpatcher_config_path (str | Path | None):
            补丁系统配置文件路径
        hotpatcher_port (int):
            补丁系统 runtime 通信端口
        enable_hotpatcher_runtime (bool):
            是否启用补丁系统 runtime host 连接
    """
    logger.info("准备 ComfyUI 启动环境")
    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    git_config_global = custom_env.get("GIT_CONFIG_GLOBAL")
    if git_config_global is not None:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_global

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
            custom_env = apply_pytorch_alloc_conf(
                config=cuda_malloc_config,
                origin_env=custom_env,
            )
    custom_env = apply_hotpatcher_launch_env(
        origin_env=custom_env,
        enabled=enable_hotpatcher,
        config_path=hotpatcher_config_path,
        port=hotpatcher_port,
        enable_runtime=enable_hotpatcher_runtime,
    )

    logger.info("启动 ComfyUI 中")
    launch_webui(
        webui_path=comfyui_path,
        launch_script="main.py",
        webui_name="ComfyUI",
        launch_args=launch_args,
        custom_env=custom_env,
    )


def install_comfyui_custom_node(
    comfyui_path: Path,
    custom_node_url: str | list[str],
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """安装 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        custom_node_url (str | list[str]):
            ComfyUI 扩展下载链接
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            安装 ComfyUI 扩展发生错误时
    """
    urls = [custom_node_url] if isinstance(custom_node_url, str) else custom_node_url

    # 获取已安装扩展列表
    custom_node_list = list_comfyui_custom_nodes(comfyui_path)
    installed_names = {x["name"] for x in custom_node_list}
    err: list[Exception] = []

    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    git_config_global = custom_env.get("GIT_CONFIG_GLOBAL")
    if git_config_global is not None:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_global

    for url in urls:
        custom_node_name = get_repo_name_from_url(url)
        custom_node_path = comfyui_path / "custom_nodes" / custom_node_name
        custom_node_diaabled_path = comfyui_path / "custom_nodes" / f"{custom_node_name}.disabled"

        if custom_node_name in installed_names or custom_node_path.exists() or custom_node_diaabled_path.exists():
            logger.info("'%s' 扩展已安装", custom_node_name)
            continue

        logger.info("安装 '%s' 扩展到 '%s' 中", custom_node_name, custom_node_path)
        try:
            clone_repo(
                repo=url,
                path=custom_node_path,
            )
            logger.info("'%s' 扩展安装成功", custom_node_name)
            installed_names.add(custom_node_name)
        except Exception as e:
            err.append(e)
            logger.error("'%s' 扩展安装失败: %s", custom_node_name, e)

    if err:
        raise AggregateError("安装 ComfyUI 扩展时发生错误", err)

    logger.info("安装 ComfyUI 扩展完成")


class ComfyUiLocalExtensionInfo(TypedDict, total=False):
    """ComfyUI 本地扩展信息"""

    name: str
    """ComfyUI 扩展名称"""

    status: bool
    """当前 ComfyUI 扩展是否已经启用"""

    path: Path
    """ComfyUI 本地路径"""

    url: str | None
    """ComfyUI 扩展远程地址"""

    commit: str | None
    """ComfyUI 扩展的提交信息"""

    branch: str | None
    """ComfyUI 扩展的当前分支"""

    source_type: str
    """扩展安装来源"""

    registry_id: str | None
    """Comfy Registry 节点 ID"""

    registry_version: str | None
    """Comfy Registry 节点版本"""

    repository: str | None
    """Comfy Registry 记录的仓库地址"""

    error: str | None
    """扩展状态错误信息"""


ComfyUiLocalExtensionInfoList = list[ComfyUiLocalExtensionInfo]
"""ComfyUI 本地扩展信息"""


def _comfyui_custom_nodes_path(comfyui_path: Path) -> Path:
    return comfyui_path / "custom_nodes"


def _disabled_custom_nodes_path(comfyui_path: Path) -> Path:
    return _comfyui_custom_nodes_path(comfyui_path) / ".disabled"


def _normalize_custom_node_name(name: str) -> str:
    return name.removesuffix(".disabled").split("@", 1)[0]


def _iter_comfyui_custom_node_paths(
    comfyui_path: Path,
    include_files: bool = False,
) -> list[tuple[str, Path, bool]]:
    custom_nodes_path = _comfyui_custom_nodes_path(comfyui_path)
    if not custom_nodes_path.is_dir():
        return []

    result: list[tuple[str, Path, bool]] = []
    for path in sorted(custom_nodes_path.iterdir(), key=lambda item: item.name.lower()):
        if path.name in {".disabled", "__pycache__"}:
            continue
        if path.is_dir():
            result.append((path.name, path, not path.name.endswith(".disabled")))
        elif include_files and path.is_file() and (path.suffix == ".py" or path.name.endswith(".py.disabled")):
            result.append((path.name, path, not path.name.endswith(".disabled")))

    disabled_root = custom_nodes_path / ".disabled"
    if disabled_root.is_dir():
        for path in sorted(disabled_root.iterdir(), key=lambda item: item.name.lower()):
            if path.name == "__pycache__":
                continue
            if path.is_dir() or (include_files and path.is_file() and (path.suffix == ".py" or path.name.endswith(".py.disabled"))):
                result.append((_normalize_custom_node_name(path.name), path, False))
    return result


def resolve_comfyui_custom_node_path(
    comfyui_path: Path,
    custom_node_name: str,
) -> tuple[Path, bool] | None:
    """查找 ComfyUI 自定义节点路径和启用状态。

    Args:
        comfyui_path (Path):
            ComfyUI 根目录。
        custom_node_name (str):
            自定义节点名称。

    Returns:
        tuple[Path, bool] | None:
            节点路径和启用状态；未找到时返回 None。
    """
    custom_nodes_path = _comfyui_custom_nodes_path(comfyui_path)
    name = custom_node_name.removesuffix(".disabled")
    candidates = [
        (custom_nodes_path / name, True),
        (custom_nodes_path / f"{name}.disabled", False),
        (_disabled_custom_nodes_path(comfyui_path) / name, False),
    ]
    disabled_root = _disabled_custom_nodes_path(comfyui_path)
    if disabled_root.is_dir():
        candidates.extend((path, False) for path in disabled_root.glob(f"{name}@*"))
    for path, enabled in candidates:
        if path.exists():
            return path, enabled
    return None


def get_comfyui_custom_node_enabled(comfyui_path: Path, custom_node_name: str) -> bool | None:
    """读取 ComfyUI 自定义节点启用状态。

    Args:
        comfyui_path (Path):
            ComfyUI 根目录。
        custom_node_name (str):
            自定义节点名称。

    Returns:
        bool | None:
            启用状态；未找到节点时返回 None。
    """
    resolved = resolve_comfyui_custom_node_path(comfyui_path, custom_node_name)
    if resolved is None:
        return None
    return resolved[1]


def list_comfyui_custom_nodes(
    comfyui_path: Path,
    include_files: bool = False,
) -> ComfyUiLocalExtensionInfoList:
    """获取 ComfyUI 本地扩展列表

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        include_files (bool):
            是否包含单文件自定义节点

    Returns:
        ComfyUiLocalExtensionInfoList:
            ComfyUI 本地扩展列表
    """

    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    info_list: ComfyUiLocalExtensionInfoList = []
    ext_dirs = _iter_comfyui_custom_node_paths(comfyui_path, include_files=include_files)

    def _process_extension(entry: tuple[str, Path, bool]) -> ComfyUiLocalExtensionInfo | None:
        name, path, status = entry
        if path.name == "__pycache__":
            return None

        repo_state = inspect_repository(path)
        source_type = "git" if repo_state.is_git_repo else ("file" if path.is_file() else "unknown")
        registry_id = None
        registry_version = None
        repository = None
        if repo_state.is_git_repo:
            registry_id = read_comfy_registry_nightly_id(path)
        else:
            cnr_info = read_comfy_registry_info(path)
            if cnr_info is not None:
                source_type = "comfy-registry"
                registry_id = cnr_info.registry_id
                registry_version = cnr_info.version
                repository = cnr_info.repository

        return {
            "name": name,
            "status": status,
            "path": path,
            "url": repo_state.url,
            "commit": repo_state.commit,
            "branch": repo_state.branch,
            "source_type": source_type,
            "registry_id": registry_id,
            "registry_version": registry_version,
            "repository": repository,
            "error": repo_state.error,
        }

    logger.info("获取 ComfyUI 扩展列表中")
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_ext = {executor.submit(_process_extension, ext): ext for ext in ext_dirs}
        for future in tqdm(as_completed(future_to_ext), total=len(ext_dirs), desc="获取 ComfyUI 扩展数据"):
            try:
                result = future.result(timeout=5)
                if result:
                    info_list.append(result)
            except Exception as e:
                ext_name = future_to_ext[future][0]
                logger.error("处理扩展 '%s' 时发生异常: %s", ext_name, e)

    logger.info("获取 ComfyUI 扩展列表中完成")
    return info_list


def set_comfyui_custom_node_status(
    comfyui_path: Path,
    custom_node_name: str,
    status: bool,
) -> None:
    """设置 ComfyUI 启用状态

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        custom_node_name (str):
            ComfyUI 扩展名称
        status (bool):
            设置扩展的启用状态
            - `True`: 启用
            - `False`: 禁用

    Raises:
        FileNotFoundError:
            ComfyUI 扩展未找到时
    """
    custom_node_name = custom_node_name.removesuffix(".disabled")
    custom_node_path = _comfyui_custom_nodes_path(comfyui_path)
    resolved = resolve_comfyui_custom_node_path(comfyui_path, custom_node_name)
    if resolved is None:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未找到, 请检查该扩展是否已安装")

    enable_path = custom_node_path / f"{custom_node_name}"
    disabled_path = custom_node_path / f"{custom_node_name}.disabled"
    dot_disabled_path = _disabled_custom_nodes_path(comfyui_path) / custom_node_name
    current_path, current_enabled = resolved
    if status:
        if not current_enabled and current_path.parent.name == ".disabled":
            move_files(current_path, enable_path)
        elif disabled_path.exists():
            move_files(disabled_path, enable_path)
        logger.info("启用 '%s' 扩展成功", custom_node_name)
    else:
        if current_enabled and enable_path.exists():
            if read_comfy_registry_info(enable_path) is not None:
                dot_disabled_path.parent.mkdir(parents=True, exist_ok=True)
                move_files(enable_path, dot_disabled_path)
            else:
                move_files(enable_path, disabled_path)
        logger.info("禁用 '%s' 扩展成功", custom_node_name)


def update_comfyui_custom_nodes(
    comfyui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        AggregateError:
            检查 ComfyUI 环境发生错误时
        FileNotFoundError:
            未找到 ComfyUI 扩展目录时
    """
    custom_nodes_path = comfyui_path / "custom_nodes"
    err: list[Exception] = []
    # 准备 Git 配置
    custom_env = apply_git_base_config_and_github_mirror(
        use_github_mirror=use_github_mirror,
        custom_github_mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        origin_env=os.environ.copy(),
    )
    git_config_global = custom_env.get("GIT_CONFIG_GLOBAL")
    if git_config_global is not None:
        os.environ["GIT_CONFIG_GLOBAL"] = git_config_global

    if not custom_nodes_path.is_dir():
        raise FileNotFoundError("未找到 ComfyUI 扩展目录")

    update_targets = [ext for ext in custom_nodes_path.iterdir() if ext.is_dir() and (ext / ".git").exists()]
    task_sum = len(update_targets)
    count = 0

    for ext in update_targets:
        count += 1
        logger.info("[%s/%s] 更新 '%s' 扩展中", count, task_sum, ext.name)
        try:
            git_warpper.update(ext)
        except Exception as e:
            err.append(e)
            logger.error("[%s/%s] 更新 '%s' 扩展时发生错误: %s", count, task_sum, ext.name, e)

    cnr_targets = [item for item in list_comfyui_custom_nodes(comfyui_path) if item.get("source_type") == "comfy-registry"]
    for item in cnr_targets:
        node_id = item.get("registry_id") or _normalize_custom_node_name(item["name"])
        try:
            logger.info("更新 Comfy Registry 节点 '%s' 中", node_id)
            switch_comfy_registry_node_version(comfyui_path, node_id=node_id, version=None, target_path=item["path"])
        except Exception as e:
            err.append(e)
            logger.error("更新 Comfy Registry 节点 '%s' 时发生错误: %s", node_id, e)

    if err:
        raise AggregateError("更新 ComfyUI 扩展时发生错误", err)

    logger.info("更新 ComfyUI 扩展完成")


def collect_comfyui_extensions(comfyui_path: Path) -> list[ExtensionSnapshot]:
    """采集 ComfyUI 自定义节点快照。

    Args:
        comfyui_path (Path):
            ComfyUI 根目录。

    Returns:
        list[ExtensionSnapshot]:
            自定义节点快照列表，包含 Git、Comfy Registry 和文件节点。
    """
    extensions: list[ExtensionSnapshot] = []
    for info in list_comfyui_custom_nodes(comfyui_path, include_files=True):
        name = info["name"]
        path = info["path"]
        source_type = info.get("source_type") or "unknown"
        if source_type == "git":
            repo = collect_repository_snapshot(path)
            extensions.append(
                ExtensionSnapshot(
                    name=name,
                    path=path,
                    enabled=info.get("status"),
                    is_git_repo=True,
                    url=repo.url,
                    branch=repo.branch,
                    commit=repo.commit,
                    commit_date=repo.commit_date,
                    message=repo.message,
                    error=repo.error,
                    dirty=repo.dirty,
                    source_type="git",
                    registry_id=info.get("registry_id"),
                )
            )
            continue

        extensions.append(
            ExtensionSnapshot(
                name=name,
                path=path,
                enabled=info.get("status"),
                is_git_repo=False,
                url=info.get("url") or info.get("repository"),
                branch=info.get("branch"),
                commit=info.get("commit"),
                error=info.get("error"),
                source_type="comfy-registry" if source_type == "comfy-registry" else ("file" if source_type == "file" else "unknown"),
                registry_id=info.get("registry_id"),
                registry_version=info.get("registry_version"),
                repository=info.get("repository"),
            )
        )
    return extensions


class ComfyUiExtensionManager:
    """ComfyUI 专属扩展管理器，支持 Git 和 Comfy Registry 节点。"""

    def __init__(self, comfyui_path: Path, include_files: bool = True) -> None:
        self.root_path = Path(comfyui_path)
        self.extension_path = self.root_path / "custom_nodes"
        self.include_files = include_files

    def list_extensions(self) -> list[ManagedExtension]:
        """获取本地 ComfyUI 自定义节点列表。

        Returns:
            list[ManagedExtension]:
                本地自定义节点列表。
        """
        result: list[ManagedExtension] = []
        for info in list_comfyui_custom_nodes(self.root_path, include_files=self.include_files):
            path = info["path"]
            if path.is_file() and not self.include_files:
                continue
            source_type = info.get("source_type") or "unknown"
            result.append(
                ManagedExtension(
                    name=info["name"],
                    path=path,
                    enabled=bool(info["status"]),
                    is_git_repo=source_type == "git",
                    url=info.get("url") or info.get("repository"),
                    branch=info.get("branch"),
                    commit=info.get("commit"),
                    error=info.get("error"),
                    source_type="comfy-registry" if source_type == "comfy-registry" else ("git" if source_type == "git" else ("file" if source_type == "file" else "unknown")),
                    registry_id=info.get("registry_id"),
                    registry_version=info.get("registry_version"),
                    repository=info.get("repository"),
                )
            )
        return result

    def set_extension_enabled(self, name: str, enabled: bool) -> None:
        """设置自定义节点启用状态。

        Args:
            name (str):
                自定义节点名称。
            enabled (bool):
                是否启用。
        """
        set_comfyui_custom_node_status(self.root_path, name, enabled)

    def install_extension(
        self,
        url: str,
        use_github_mirror: bool = False,
        custom_github_mirror: str | list[str] | None = None,
    ) -> Path:
        """从 Git URL 安装自定义节点。

        Args:
            url (str):
                Git 仓库地址。
            use_github_mirror (bool):
                是否启用 GitHub 镜像。
            custom_github_mirror (str | list[str] | None):
                自定义 GitHub 镜像。

        Returns:
            Path:
                自定义节点安装路径。
        """
        install_comfyui_custom_node(
            comfyui_path=self.root_path,
            custom_node_url=url,
            use_github_mirror=use_github_mirror,
            custom_github_mirror=custom_github_mirror,
        )
        return self.extension_path / get_repo_name_from_url(url)

    def install_registry_extension(self, node_id: str, version: str | None = None, use_uv: bool = True) -> Path:
        """从 Comfy Registry 安装自定义节点。

        Args:
            node_id (str):
                Comfy Registry 节点 ID。
            version (str | None):
                指定安装版本。
            use_uv (bool):
                是否使用 uv 安装依赖。

        Returns:
            Path:
                自定义节点安装路径。
        """
        install_comfy_registry_node(self.root_path, node_id=node_id, version=version, use_uv=use_uv)
        return self.extension_path / node_id

    def update_extension(self, name: str) -> None:
        """更新自定义节点。

        Args:
            name (str):
                自定义节点名称。

        Raises:
            FileNotFoundError:
                节点未安装时抛出。
            ValueError:
                节点不是可更新来源时抛出。
        """
        ext = next((item for item in self.list_extensions() if item.name == name), None)
        if ext is None:
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        self._update_extension(ext)

    def _update_extension(self, ext: ManagedExtension) -> None:
        """根据已解析的扩展信息更新自定义节点。

        Args:
            ext (ManagedExtension):
                已解析的自定义节点信息。

        Raises:
            ValueError:
                节点不是可更新来源时抛出。
        """
        if ext.source_type == "comfy-registry":
            node_id = ext.registry_id or _normalize_custom_node_name(ext.name)
            switch_comfy_registry_node_version(self.root_path, node_id=node_id, version=None, target_path=ext.path)
            return
        if not ext.is_git_repo:
            raise ValueError(f"'{ext.name}' 不是 Git 仓库或 Comfy Registry 节点，无法更新")
        git_warpper.update(ext.path)

    def update_all(self) -> None:
        """更新所有可更新的自定义节点。

        Raises:
            AggregateError:
                一个或多个节点更新失败时抛出。
        """
        errors: list[Exception] = []
        for ext in self.list_extensions():
            if ext.source_type not in {"git", "comfy-registry"}:
                continue
            try:
                self._update_extension(ext)
            except Exception as e:
                errors.append(e)
        if errors:
            raise AggregateError("更新 ComfyUI 扩展时发生错误", errors)

    def uninstall_extension(self, name: str) -> None:
        """卸载自定义节点。

        Args:
            name (str):
                自定义节点名称。
        """
        uninstall_comfyui_custom_node(self.root_path, name)

    def switch_extension_commit(self, name: str, commit: str) -> None:
        """切换 Git 自定义节点到指定提交。

        Args:
            name (str):
                自定义节点名称。
            commit (str):
                目标提交 ID。

        Raises:
            FileNotFoundError:
                节点未安装时抛出。
        """
        resolved = resolve_comfyui_custom_node_path(self.root_path, name)
        if resolved is None:
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        git_warpper.switch_commit(path=resolved[0], commit=commit)

    def switch_extension_branch(self, name: str, branch: str) -> None:
        """切换 Git 自定义节点分支。

        Args:
            name (str):
                自定义节点名称。
            branch (str):
                目标分支。

        Raises:
            FileNotFoundError:
                节点未安装时抛出。
        """
        resolved = resolve_comfyui_custom_node_path(self.root_path, name)
        if resolved is None:
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        git_warpper.switch_branch(path=resolved[0], branch=branch)

    def switch_registry_extension_version(self, name: str, version: str, use_uv: bool = True) -> None:
        """切换 Comfy Registry 自定义节点版本。

        Args:
            name (str):
                自定义节点名称。
            version (str):
                目标 Registry 版本。
            use_uv (bool):
                是否使用 uv 安装依赖。

        Raises:
            FileNotFoundError:
                节点未安装时抛出。
            ValueError:
                节点不是 Comfy Registry 来源时抛出。
        """
        ext = next((item for item in self.list_extensions() if item.name == name), None)
        if ext is None:
            raise FileNotFoundError(f"'{name}' 扩展未安装")
        if ext.source_type != "comfy-registry":
            raise ValueError(f"'{name}' 不是 Comfy Registry 节点")
        node_id = ext.registry_id or _normalize_custom_node_name(ext.name)
        switch_comfy_registry_node_version(self.root_path, node_id=node_id, version=version, target_path=ext.path, use_uv=use_uv)


def get_comfyui_snapshot(
    comfyui_path: Path,
    include_packages: bool = True,
) -> WebUiSnapshot:
    """获取 ComfyUI 环境快照

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        include_packages (bool):
            是否记录当前 Python 环境已安装软件包

    Returns:
        WebUiSnapshot:
            ComfyUI 环境快照
    """
    return build_webui_snapshot(
        webui_name="ComfyUI",
        webui_type="comfyui",
        webui_path=comfyui_path,
        include_packages=include_packages,
        extensions=collect_comfyui_extensions(comfyui_path),
    )


def uninstall_comfyui_custom_node(
    comfyui_path: Path,
    custom_node_name: str,
) -> None:
    """卸载 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        custom_node_name (str):
            ComfyUI 扩展名称

    Raises:
        FileNotFoundError:
            要卸载的扩展未找到时
        RuntimeError:
            卸载扩展发生错误时
    """
    resolved = resolve_comfyui_custom_node_path(comfyui_path, custom_node_name)
    if resolved is None:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未安装")
    custom_node_path, _enabled = resolved

    try:
        logger.info("卸载 '%s' 扩展中", custom_node_name)
        remove_files(custom_node_path)
        logger.info("卸载 '%s' 扩展完成", custom_node_name)
    except Exception as e:
        logger.info("卸载 '%s' 扩展时发生错误: %s", custom_node_name, e)
        raise RuntimeError(f"卸载 '{custom_node_name}' 扩展时发生错误:{e}") from e


def install_comfyui_model_from_library(
    comfyui_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = None,
    interactive_mode: bool = False,
    list_only: bool = False,
) -> None:
    """为 ComfyUI 下载模型, 使用模型库进行下载

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        download_resource_type (ModelDownloadUrlType | None):
            模型下载源类型
        model_name (str | None):
            下载的模型名称
        model_index (int | None):
            下载的模型在列表中的索引值, 索引值从 1 开始. 当同时提供 `model_name` 和 `model_index` 时, 优先使用 `model_index` 查找模型
        downloader (DownloadToolType | None):
            下载模型使用的工具
        interactive_mode (bool):
            是否启用交互模式
        list_only (bool):
            是否仅列出模型列表并退出
    """
    install_webui_model_from_library(
        webui_path=comfyui_path,
        dtype="comfyui",
        download_resource_type=download_resource_type,
        model_name=model_name,
        model_index=model_index,
        downloader=downloader,
        interactive_mode=interactive_mode,
        list_only=list_only,
    )


def install_comfyui_model_from_url(
    comfyui_path: Path,
    model_url: str,
    model_type: str,
    downloader: DownloadToolType | None = None,
) -> None:
    """从链接下载模型到 ComfyUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        model_url (str):
            模型下载地址
        model_type (str):
            模型的类型
        downloader (DownloadToolType | None):
            下载模型使用的工具
    """
    model_path = comfyui_path / "models" / model_type
    download_file(
        url=model_url,
        path=model_path,
        tool=downloader,
    )


def list_comfyui_models(
    comfyui_path: Path,
) -> None:
    """列出 ComfyUI 的模型目录

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
    """
    models_path = comfyui_path / "models"
    logger.info("ComfyUI 模型列表")
    for m in models_path.iterdir():
        logger.info("%s 的模型列表", m.name)
        generate_dir_tree(m)
        print("\n\n")


def uninstall_comfyui_model(
    comfyui_path: Path,
    model_name: str,
    model_type: str | None = None,
    interactive_mode: bool = False,
) -> None:
    """卸载 ComfyUI 中的模型

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        model_name (str):
            模型名称
        model_type (str | None):
            模型的类型
        interactive_mode (bool):
            是否启用交互模式

    Raises:
        FileNotFoundError:
            未找到要删除的模型时
    """
    if model_type is None:
        model_path = comfyui_path / "models"
    else:
        model_path = comfyui_path / "models" / model_type

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


def launch_comfyui_version_gui(
    comfyui_path: Path,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """启动 ComfyUI 版本管理 GUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        use_github_mirror (bool):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源

    Raises:
        RuntimeError:
            环境未安装 tkinter 或者导入 GUI 模块失败时
    """
    try:
        from sd_webui_all_in_one.base_manager.gui.comfyui_version_gui import (
            launch_comfyui_version_gui as _launch_comfyui_version_gui,
        )
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动版本管理 GUI") from e
        raise RuntimeError(f"导入 GUI 管理模块发生错误: {e}") from e

    _launch_comfyui_version_gui(
        comfyui_path=comfyui_path,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )


def launch_comfyui_snapshot_gui(
    comfyui_path: Path,
    snapshot_dir: Path | None = None,
    use_uv: bool = True,
    use_pypi_mirror: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """启动 ComfyUI 快照管理 GUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录。
        snapshot_dir (Path | None):
            快照文件目录。
        use_uv (bool):
            是否使用 uv 执行 Python 包安装。
        use_pypi_mirror (bool):
            是否使用 PyPI 镜像源。
        use_github_mirror (bool):
            是否使用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。

    Raises:
        RuntimeError:
            当恢复或 GUI 启动无法安全继续时抛出。
    """
    try:
        from sd_webui_all_in_one.base_manager.gui.snapshot_gui import launch_snapshot_manager_gui
    except ModuleNotFoundError as e:
        if e.name == "tkinter":
            raise RuntimeError("当前 Python 环境未安装 tkinter, 无法启动快照管理 GUI") from e
        raise RuntimeError(f"导入 GUI 管理模块发生错误: {e}") from e

    launch_snapshot_manager_gui(
        title="ComfyUI",
        webui_type="comfyui",
        webui_path=comfyui_path,
        snapshot_factory=lambda include_packages: get_comfyui_snapshot(comfyui_path, include_packages=include_packages),
        snapshot_dir=snapshot_dir,
        use_uv=use_uv,
        use_pypi_mirror=use_pypi_mirror,
        use_github_mirror=use_github_mirror,
        custom_github_mirror=custom_github_mirror,
    )
