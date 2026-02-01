import os
import sys
import importlib.metadata
import urllib.parse
from pathlib import Path
from tempfile import TemporaryDirectory

from sd_webui_all_in_one.downloader import DownloadToolType
from sd_webui_all_in_one.pytorch_manager.base import (
    PyTorchDeviceType,
    PYPI_INDEX_MIRROR_OFFICIAL,
    PYPI_INDEX_MIRROR_TENCENT,
    PYPI_EXTRA_INDEX_MIRROR_CERNET,
    PYTORCH_FIND_LINKS_MIRROR_OFFICIAL,
    PYTORCH_FIND_LINKS_MIRROR_ALIYUN,
)
from sd_webui_all_in_one.pytorch_manager.pytorch_mirror import (
    auto_detect_avaliable_pytorch_type,
    find_latest_pytorch_info,
    get_pytorch_mirror,
    get_pytorch_mirror_type,
    auto_detect_pytorch_device_category,
)
from sd_webui_all_in_one.env_manager import generate_uv_and_pip_env_mirror_config
from sd_webui_all_in_one.package_analyzer.pkg_check import is_package_has_version, get_package_version
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.file_operations.file_manager import is_folder_empty, copy_files, remove_files
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import install_pytorch
from sd_webui_all_in_one.model_downloader.model_utils import download_model, query_model_info, display_model_table, search_models_from_library
from sd_webui_all_in_one.model_downloader.base import MODEL_DOWNLOAD_DICT, SupportedWebUiType, ModelDownloadUrlType
from sd_webui_all_in_one.cmd import run_cmd
from sd_webui_all_in_one.utils import print_divider

logger = get_logger(
    name="Base Manager",
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


def prepare_pytorch_install_info(
    pytorch_mirror_type: PyTorchDeviceType | None = None,
    custom_pytorch_package: str | None = None,
    custom_xformers_package: str | None = None,
    use_cn_mirror: bool | None = False,
) -> tuple[str | None, str | None, dict[str, str]]:
    """配置安装 PyTorch 所需的 PyTorch, xFormers 包版本声明和 PyTorch 镜像源

    Args:
        pytorch_mirror_type (PyTorchDeviceType | None):
            指定的 PyTorch 镜像源类型
        custom_pytorch_package (str | None):
            自定义 PyTorch 软件包版本声明, 例如: `torch==2.3.0+cu118 torchvision==0.18.0+cu118 torchaudio==2.3.0+cu118`
        custom_xformers_package (str | None):
            自定义 xFormers 软件包版本声明, 例如: `xformers===0.0.26.post1+cu118`
        use_cn_mirror (bool | None):
            是否使用国内镜像

    Returns:
        (tuple[str, | None, str | None, dict[str, str]]):
            PyTorch 软件包版本声明, xFormers 软件包版本声明, 带有 PyPI 镜像源配置的环境变量字典
    """
    torch_part: list[str] = []

    # 配置 PyTorch 软件包列表
    if custom_pytorch_package is None:
        dtype = auto_detect_avaliable_pytorch_type()
        pytorch_info = find_latest_pytorch_info(dtype)
        mirror_type = pytorch_info["dtype"]
        index_url = pytorch_info["index_mirror"]["mirror"] if use_cn_mirror else pytorch_info["index_mirror"]["official"]
        extra_index_url = pytorch_info["extra_index_mirror"]["mirror"] if use_cn_mirror else pytorch_info["extra_index_mirror"]["official"]
        find_links = pytorch_info["find_links"]["mirror"] if use_cn_mirror else pytorch_info["find_links"]["official"]
        torch_ver = pytorch_info["torch_ver"]
        xformers_ver = pytorch_info["xformers_ver"]
    else:
        mirror_type = None
        torch_part = [x for x in custom_pytorch_package.split() if x.startswith("torch==")]
        torch_ver = custom_pytorch_package
        xformers_ver = custom_xformers_package
        extra_index_url = []
        find_links = []

    # 配置 PyTorch 镜像源
    if pytorch_mirror_type is not None:
        index_url = get_pytorch_mirror(
            dtype=pytorch_mirror_type,
            use_cn_mirror=use_cn_mirror,
        )
    elif torch_part and is_package_has_version(torch_part[0]):
        # 声明了 PyTorch 版本
        if "+" in torch_part[0]:
            # 存在类型声明
            index_url = get_pytorch_mirror(
                dtype=torch_part[0].split("+")[-1],
                use_cn_mirror=use_cn_mirror,
            )
        else:
            # 不存在类型声明时
            index_url = get_pytorch_mirror(
                dtype=get_pytorch_mirror_type(
                    torch_ver=get_package_version(torch_part[0]),
                    device_type=auto_detect_pytorch_device_category() if mirror_type is None else mirror_type,
                ),
                use_cn_mirror=use_cn_mirror,
            )
    else:
        index_url = get_pytorch_mirror(
            dtype=auto_detect_avaliable_pytorch_type(),
            use_cn_mirror=use_cn_mirror,
        )

    custom_env = generate_uv_and_pip_env_mirror_config(
        index_url=index_url,
        extra_index_url=extra_index_url,
        find_links=find_links,
    )

    return (torch_ver, xformers_ver, custom_env)


def install_pytorch_for_webui(
    pytorch_package: str | None = None,
    xformers_package: str | None = None,
    custom_env: dict[str, str] | None = None,
    use_uv: bool | None = True,
) -> None:
    """为 WebUI 环境安装 PyTorch

    Args:
        pytorch_package: (str | None):
            PyTorch 包版本声明
        xformers_package (str | None):
            xFormers 包版本声明
        custom_env (dict[str, str] | None):
            环境变量字典, 用于设置安装 PyTorch 时使用的 PyTorch 镜像源
        use_uv (bool | None):
            是否使用 uv 进行 PyTorch 安装
    """
    logger.info("检查 PyTorc / xFormers 是否需要安装")
    need_install_pytorch = False
    need_install_xformers = False
    if pytorch_package is not None:
        try:
            importlib.metadata.version("torch")
        except Exception:
            need_install_pytorch = True

    if xformers_package is not None:
        try:
            importlib.metadata.version("xformers")
        except Exception:
            need_install_xformers = True

    if not need_install_pytorch and not need_install_xformers:
        logger.info("PyTorch / xFormers 已安装")
        return

    install_pytorch(
        torch_package=pytorch_package,
        xformers_package=xformers_package,
        custom_env=custom_env,
        use_uv=use_uv,
    )

    logger.info("PyTorch / xFormers 安装完成")


def reinstall_pytorch() -> None: ...


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


def get_pypi_mirror_config(
    use_cn_mirror: bool | None = False,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """获取带有 PyPI 镜像源配置的环境变量字典

    Args:
        use_cn_mirror (bool | None):
            是否使用国内镜像源
        origin_env (dict[str, str] | None):
            原始的环境变量字典

    Returns:
        (dict[str, str]):
            带有 PyPI 镜像源配置的环境变量字典
    """
    if use_cn_mirror:
        return generate_uv_and_pip_env_mirror_config(
            index_url=PYPI_INDEX_MIRROR_TENCENT,
            extra_index_url=PYPI_EXTRA_INDEX_MIRROR_CERNET,
            find_links=PYTORCH_FIND_LINKS_MIRROR_ALIYUN,
            origin_env=origin_env,
        )
    else:
        return generate_uv_and_pip_env_mirror_config(
            index_url=PYPI_INDEX_MIRROR_OFFICIAL,
            extra_index_url=[],
            find_links=PYTORCH_FIND_LINKS_MIRROR_OFFICIAL,
            origin_env=origin_env,
        )


def pre_download_model_for_webui(
    dtype: SupportedWebUiType,
    model_path: Path,
    webui_base_path: Path,
    model_name: str,
    download_resource_type: ModelDownloadUrlType,
) -> None:
    """为 WebUI 预下载模型

    Args:
        dtype (SupportedWebUiType):
            WebUI 的类型
        model_path (Path):
            预下载模型的路径
        webui_base_path (Path):
            WebUI 的根路径
        model_name (str):
            预下载的模型名称
        download_resource_type (ModelDownloadUrlType):
            模型下载源类型
    """
    if model_path.is_dir() and not any(model_path.rglob("*.safetensors")):
        logger.info("预下载模型中")
        download_model(
            dtype=dtype,
            base_path=webui_base_path,
            download_resource_type=download_resource_type,
            model_name=model_name,
        )


def launch_webui(
    webui_path: Path,
    launch_script: str,
    launch_args: list[str] | None = None,
    custom_env: dict[str, str] | None = None,
) -> None:
    """运行 WebUI

    Args:
        webui_path (Path):
            WebUI 的根目录
        launch_script (str):
            启动 WebUI 的脚本名称, 使用相对路径
        launch_args (list[str] | None):
            启动 WebUI 的参数
        custom_env (dict[str, str] | None):
            自定义环境变量

    Raises:
        RuntimeError:
            运行 WebUI 时出现错误
    """
    if launch_args is None:
        launch_args = []

    if custom_env is None:
        custom_env = os.environ.copy()

    cmd = [Path(sys.executable).as_posix(), webui_path / launch_script] + launch_args
    try:
        run_cmd(cmd, custom_env=custom_env, cwd=webui_path)
    except RuntimeError as e:
        raise RuntimeError(f"运行 WebUI 时出现错误: {e}") from e


def get_repo_name_from_url(url: str) -> str:
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


def install_webui_model_from_library(
    webui_path: Path,
    dtype: SupportedWebUiType,
    download_resource_type: ModelDownloadUrlType | None = "modelscope",
    model_name: str | None = None,
    model_index: int | None = None,
    downloader: DownloadToolType | None = "aria2",
    interactive_mode: bool | None = False,
) -> None:
    """为 WebUI 下载模型, 使用模型库进行下载

    Args:
        webui_path (Path):
            WebUI 根目录
        dtype (SupportedWebUiType):
            WebUI 的类型
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
    """

    def _input_to_int_list(_input: str) -> list[str] | None: #FIXME
        try:
            return [int(_i) for _i in _input.split()]
        except Exception:
            return None

    model_list = MODEL_DOWNLOAD_DICT.copy()
    display_model = True

    if interactive_mode:
        while True:
            if display_model:
                print_divider("=")
                display_model_table(model_list)
                print_divider("=")

            display_model = True
            print(
                "请选择要下载的模型\n"
                "提示:\n"
                "1. 输入数字后回车\n"
                "2. 如果需要下载多个模型, 可以输入多个数字并使用空格隔开\n"
                "3. 输入 search 可以进入列表搜索模式, 可搜索列表中已有的模型\n"
                "4. 输入 exit 退出模型下载脚本"
            )
            user_input = input("==> ").strip()

            if user_input == "exit":
                return

            if user_input == "search":
                display_model = False
                print_divider("=")
                search_models_from_library(
                    query=input("请输入要从模型列表搜索的模型名称: "),
                    models=model_list,
                )
                print_divider("=")
                continue

            result = _input_to_int_list(user_input)

            if result is None or len(result):
                logger.warning("输入有误, 请重试")
                continue

            download_model(
                dtype=dtype,
                base_path=webui_path,
                download_resource_type=download_resource_type,
                model_index=result,
                downloader=downloader,
            )
    else:
        download_model(
            dtype=dtype,
            base_path=webui_path,
            download_resource_type=download_resource_type,
            model_name=model_name,
            model_index=model_index,
            downloader=downloader,
        )
