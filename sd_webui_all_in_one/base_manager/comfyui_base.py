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
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.downloader import (
    DownloadToolType,
    download_file,
)
from sd_webui_all_in_one.env_check.fix_dependencies import py_dependency_checker
from sd_webui_all_in_one.env_check.fix_torch import fix_torch_libomp
from sd_webui_all_in_one.env_check.onnxruntime_gpu_check import check_onnxruntime_gpu
from sd_webui_all_in_one.file_operations.file_manager import (
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
from sd_webui_all_in_one.model_downloader.base import ModelDownloadUrlType
from sd_webui_all_in_one.optimize.cuda_malloc import get_cuda_malloc_var
from sd_webui_all_in_one.pkg_manager import install_requirements
from sd_webui_all_in_one.pytorch_manager.base import PyTorchDeviceType
from sd_webui_all_in_one.env_check.comfyui_env_analyze import comfyui_conflict_analyzer

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
        "name": "ComfyUI_TiledKSampler",
        "url": "https://github.com/BlenderNeko/ComfyUI_TiledKSampler",
        "save_dir": "custom_nodes/ComfyUI_TiledKSampler",
    },
    {
        "name": "ComfyUI-Custom-Scripts",
        "url": "https://github.com/pythongosssss/ComfyUI-Custom-Scripts",
        "save_dir": "custom_nodes/ComfyUI-Custom-Scripts",
    },
    {
        "name": "images-grid-comfy-plugin",
        "url": "https://github.com/LEv145/images-grid-comfy-plugin",
        "save_dir": "custom_nodes/images-grid-comfy-plugin",
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
        "name": "ComfyUI-openpose-editor",
        "url": "https://github.com/huchenlei/ComfyUI-openpose-editor",
        "save_dir": "custom_nodes/ComfyUI-openpose-editor",
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

COMFYUI_CONFIG_PATH = ROOT_PATH / "base_manager" / "config" / "comfy.settings.json"
"""ComfyUI 预设配置文件路径"""


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
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    no_pre_download_extension: bool | None = False,
    no_pre_download_model: bool | None = False,
    use_cn_model_mirror: bool | None = True,
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
        use_pypi_mirror (bool | None):
            是否使用国内 PyPI 镜像源
        use_uv (bool | None):
            是否使用 uv 安装 Python 软件包
        use_github_mirror (bool | None):
            是否使用 Github 镜像源
        custom_github_mirror (str | list[str] | None):
            自定义 Github 镜像源
        no_pre_download_extension (bool | None):
            是否禁用预下载 ComfyUI 扩展
        no_pre_download_model (bool | None):
            是否禁用预下载模型
        use_cn_model_mirror (bool | None):
            是否使用国内镜像下载模型

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
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

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
            download_resource_type="modelscope" if use_cn_model_mirror else "huggingface",
        )

    install_comfyui_config(comfyui_path)

    logger.info("安装 ComfyUI 完成")


def update_comfyui(
    comfyui_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 ComfyUI

    Args:
        comfyui_path (Path):
            Stable DIffusion WebUI 根目录
        use_github_mirror (bool | None):
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
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    git_warpper.update(comfyui_path)

    logger.info("更新 ComfyUI 完成")


def check_comfyui_env(
    comfyui_path: Path,
    install_conflict_component_requirement: bool | None = False,
    interactive_mode: bool | None = False,
    use_uv: bool | None = True,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
) -> None:
    """检查 ComfyUI 运行环境

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        install_conflict_component_requirement (bool | None):
            检测到冲突依赖时是否按顺序安装组件依赖
        interactive_mode (bool | None):
            是否启用交互模式, 当检测到冲突依赖时将询问是否安装冲突组件依赖
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
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

    # 检查任务列表
    tasks: list[tuple[Callable, dict[str, Any]]] = [
        (py_dependency_checker, {"requirement_path": req_path, "name": "ComfyUI", "use_uv": use_uv, "custom_env": custom_env}),
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
        (check_onnxruntime_gpu, {"use_uv": use_uv, "skip_if_missing": True, "custom_env": custom_env}),
    ]
    err: list[Exception] = []

    for func, kwargs in tasks:
        try:
            func(**kwargs)
        except Exception as e:
            err.append(e)
            logger.error("执行 '%s' 时发生错误: %s", func.__name__, e)

    if err:
        raise AggregateError("检查 ComfyUI 环境时发生错误", err)

    logger.info("检查 ComfyUI 环境完成")


def launch_comfyui(
    comfyui_path: Path,
    launch_args: list[str] | None = None,
    use_hf_mirror: bool | None = False,
    custom_hf_mirror: str | list[str] | None = None,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool | None = False,
    use_cuda_malloc: bool | None = True,
) -> None:
    """启动 ComfyUI

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        launch_args (list[str] | None):
            启动 ComfyUI 的参数
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
    logger.info("准备 ComfyUI 启动环境")
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
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """安装 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        custom_node_url (str | list[str]):
            ComfyUI 扩展下载链接
        use_github_mirror (bool | None):
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
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

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


ComfyUiLocalExtensionInfoList = list[ComfyUiLocalExtensionInfo]
"""ComfyUI 本地扩展信息"""


def list_comfyui_custom_nodes(
    comfyui_path: Path,
) -> ComfyUiLocalExtensionInfoList:
    """获取 ComfyUI 本地扩展列表

    Args:
        comfyui_path (Path):
            ComfyUI 根目录

    Returns:
        ComfyUiLocalExtensionInfoList:
            ComfyUI 本地扩展列表
    """

    try:
        from tqdm import tqdm
    except ImportError:
        from sd_webui_all_in_one.simple_tqdm import SimpleTqdm as tqdm

    custom_node_path = comfyui_path / "custom_nodes"
    info_list: ComfyUiLocalExtensionInfoList = []
    ext_dirs = list(custom_node_path.iterdir())

    def _process_extension(ext: Path) -> ComfyUiLocalExtensionInfo:
        if ext.is_file() or ext.name == "__pycache__":
            return None

        name = ext.name
        path = ext
        status = not name.endswith(".disabled")
        url = None
        commit = None
        branch = None

        try:
            url = git_warpper.get_current_branch_remote_url(ext)
        except (ValueError, Exception):
            pass

        try:
            commit = git_warpper.get_current_commit(ext)
        except (ValueError, Exception):
            pass

        try:
            branch = git_warpper.get_current_branch(ext)
        except (ValueError, Exception):
            pass

        return {"name": name, "status": status, "path": path, "url": url, "commit": commit, "branch": branch}

    logger.info("获取 ComfyUI 扩展列表中")
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_ext = {executor.submit(_process_extension, ext): ext for ext in ext_dirs}
        for future in tqdm(as_completed(future_to_ext), total=len(ext_dirs), desc="获取 ComfyUI 扩展数据"):
            try:
                result = future.result(timeout=5)
                if result:
                    info_list.append(result)
            except Exception as e:
                ext_name = future_to_ext[future].name
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
        extension_name (str):
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
    custom_node_path = comfyui_path / "custom_nodes"
    custom_node_list = [ext.name for ext in custom_node_path.iterdir() if ext.is_dir()]
    all_custom_nodes = [x.removesuffix(".disabled") for x in custom_node_list]

    if custom_node_name not in all_custom_nodes:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未找到, 请检查该扩展是否已安装")

    enable_path = custom_node_path / f"{custom_node_name}"
    disabled_path = custom_node_path / f"{custom_node_name}.disabled"
    if status:
        if disabled_path.is_dir():
            move_files(disabled_path, enable_path)
        logger.info("启用 '%s' 扩展成功", custom_node_name)
    else:
        if enable_path.is_dir():
            move_files(enable_path, disabled_path)
        logger.info("禁用 '%s' 扩展成功", custom_node_name)


def update_comfyui_custom_nodes(
    comfyui_path: Path,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
) -> None:
    """更新 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        use_github_mirror (bool | None):
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
    os.environ["GIT_CONFIG_GLOBAL"] = custom_env.get("GIT_CONFIG_GLOBAL")

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

    if err:
        raise AggregateError("更新 ComfyUI 扩展时发生错误", err)

    logger.info("更新 ComfyUI 扩展完成")


def uninstall_comfyui_custom_node(
    comfyui_path: Path,
    custom_node_name: str,
) -> None:
    """卸载 ComfyUI 扩展

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
        extension_name (str):
            ComfyUI 扩展名称

    Raises:
        FileNotFoundError:
            要卸载的扩展未找到时
        RuntimeError:
            卸载扩展发生错误时
    """
    custom_nodes_path = comfyui_path / "custom_nodes"
    custom_nodes_list = [ext.name for ext in custom_nodes_path.iterdir() if ext.is_dir()]
    if custom_node_name not in custom_nodes_list:
        raise FileNotFoundError(f"'{custom_node_name}' 扩展未安装")

    try:
        logger.info("卸载 '%s' 扩展中", custom_node_name)
        remove_files(custom_nodes_path / custom_node_name)
        logger.info("卸载 '%s' 扩展完成", custom_node_name)
    except Exception as e:
        logger.info("卸载 '%s' 扩展时发生错误: %s", custom_node_name, e)
        raise RuntimeError(f"卸载 '{custom_node_name}' 扩展时发生错误:{e}") from e


def install_comfyui_model_from_library(
    comfyui_path: Path,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = "aria2",
    interactive_mode: bool | None = False,
    list_only: bool | None = False,
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
        interactive_mode (bool | None):
            是否启用交互模式
        list_only (bool | None):
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
    downloader: DownloadToolType | None = "aria2",
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
        sd_webui_path (Path):
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
    interactive_mode: bool | None = False,
) -> None:
    """卸载 ComfyUI 中的模型

    Args:
        comfyui_path (Path):
            ComfyUI 根目录
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
