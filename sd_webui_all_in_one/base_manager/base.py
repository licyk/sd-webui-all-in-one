import os
import sys
import importlib.metadata
import urllib.parse
from pathlib import Path
from tempfile import TemporaryDirectory

from sd_webui_all_in_one.downloader import DownloadToolType
from sd_webui_all_in_one.mirror_manager import GITHUB_MIRROR_LIST, set_git_base_config, set_github_mirror
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
    export_pytorch_list,
    display_pytorch_config,
    query_pytorch_info_from_library,
)
from sd_webui_all_in_one.env_manager import generate_uv_and_pip_env_mirror_config
from sd_webui_all_in_one.package_analyzer.pkg_check import get_package_name, is_package_has_version, get_package_version
from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.file_operations.file_manager import is_folder_empty, copy_files, remove_files
from sd_webui_all_in_one.config import LOGGER_LEVEL, LOGGER_COLOR
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.pkg_manager import install_pytorch
from sd_webui_all_in_one.model_downloader.model_utils import download_model, export_model_list, display_model_table, search_models_from_library
from sd_webui_all_in_one.model_downloader.base import SupportedWebUiType, ModelDownloadUrlType
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
        device_type = pytorch_info["dtype"]
        index_url = pytorch_info["index_mirror"]["mirror"] if use_cn_mirror else pytorch_info["index_mirror"]["official"]
        extra_index_url = pytorch_info["extra_index_mirror"]["mirror"] if use_cn_mirror else pytorch_info["extra_index_mirror"]["official"]
        find_links = pytorch_info["find_links"]["mirror"] if use_cn_mirror else pytorch_info["find_links"]["official"]
        torch_ver = pytorch_info["torch_ver"]
        xformers_ver = pytorch_info["xformers_ver"]
    else:
        device_type = None
        torch_part = [x for x in custom_pytorch_package.split() if get_package_name(x) == "torch"]
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
                    device_type=auto_detect_pytorch_device_category() if device_type is None else device_type,
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


def reinstall_pytorch(
    pytorch_name: str | None = None,
    pytorch_index: int | None = None,
    use_pypi_mirror: bool | None = True,
    use_uv: bool | None = None,
    interactive_mode: bool | None = False,
    list_only: bool | None = False,
) -> None:
    """PyTorch 重装工具

    Args:
        pytorch_name (str | None):
            PyTorch 版本组合名称
        pytorch_index (int | None):
            PyTorch 版本组合索引值
        use_pypi_mirror (bool | None):
            是否使用 PyPI 国内镜像
        use_uv (bool | None):
            是否使用 uv 进行 PyTorch 安装
        interactive_mode (bool | None):
            是否启用交互模式
        list_only (bool | None):
            是否仅列出 PyTorch 列表并退出
    """

    def _install(
        input_name: str | None = None,
        input_index: int | None = None,
    ) -> None:
        info = query_pytorch_info_from_library(
            pytorch_name=input_name,
            pytorch_index=input_index,
        )
        custom_env = generate_uv_and_pip_env_mirror_config(
            index_url=info["index_mirror"]["mirror"] if use_pypi_mirror else info["index_mirror"]["official"],
            extra_index_url=info["extra_index_mirror"]["mirror"] if use_pypi_mirror else info["extra_index_mirror"]["official"],
            find_links=info["find_links"]["mirror"] if use_pypi_mirror else info["find_links"]["official"],
        )
        logger.info("安装 PyTorch 中")
        _uninstall()
        install_pytorch(
            torch_package=info["torch_ver"],
            xformers_package=info["xformers_ver"],
            custom_env=custom_env,
            use_uv=use_uv,
        )

    def _uninstall() -> None:
        if force_reinstall:
            run_cmd([Path(sys.executable), "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "xformers", "-y"])

    pytorch_list = export_pytorch_list()

    if list_only:
        print_divider("=")
        display_pytorch_config(pytorch_list)
        print_divider("=")
        return

    display_model = True
    input_err = (0, None)
    force_reinstall = False

    if interactive_mode:
        while True:
            if display_model:
                print_divider("=")
                display_pytorch_config(pytorch_list)
                print_divider("=")

            display_model = True
            force_reinstall = False
            i, m = input_err
            if i == 1:
                logger.warning("输入有误, 请重试")
            elif i == 2:
                logger.warning("输入的数字有误, %s, 请重新输入", m)
            input_err = (0, None)
            print(
                "请选择 PyTorch 版本\n"
                "提示:\n"
                "1. PyTorch 版本通常来说选择最新版的即可\n"
                "2. 驱动支持的最高 CUDA 版本需要大于或等于要安装的 PyTorch 中所带的 CUDA 版本, 若驱动支持的最高 CUDA 版本低于要安装的 PyTorch 中所带的 CUDA 版本, 可尝试更新显卡驱动, 或者选择 CUDA 版本更低的 PyTorch\n"
                "3. 输入数字后回车即可选择安装指定的 PyTorch 版本组合\n" \
                "4. 输入 auto 后回车可以自动根据设备支持情况选择最佳 PyTorch 版本组合进行安装\n"
                "5. 输入 exit 后回车退出 PyTorch 重装"
            )
            user_input = input("==> ").strip()

            if user_input == "exit":
                return

            if user_input == "auto":
                if input("是否启用强制重装? [y/N] ").strip().lower() in ["yes", "y"]:
                    force_reinstall = True

                logger.info("自动根据设备支持情况选择最佳 PyTorch 版本组合中")
                pytorch, xformers, custom_env = prepare_pytorch_install_info(use_cn_mirror=use_pypi_mirror)
                logger.info("安装 PyTorch 中")
                _uninstall()
                install_pytorch(
                    torch_package=pytorch,
                    xformers_package=xformers,
                    custom_env=custom_env,
                    use_uv=use_uv,
                )
                return

            try:
                index = int(user_input)
            except Exception:
                input_err = (1, None)
                continue

            try:
                if input("是否启用强制重装? [y/N] ").strip().lower() in ["yes", "y"]:
                    force_reinstall = True

                _install(input_index=index)
                return
            except ValueError as e:
                input_err = (1, str(e))
                continue

    else:
        _install(
            input_name=pytorch_name,
            input_index=pytorch_index,
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
) -> Path | None:
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

    Returns:
        (Path | None):
            模型的保存路径
    """
    if model_path.is_dir() and not any(model_path.rglob("*.safetensors")):
        logger.info("预下载模型中")
        path = download_model(
            dtype=dtype,
            base_path=webui_base_path,
            download_resource_type=download_resource_type,
            model_name=model_name,
        )
        if len(path) > 0:
            return path[0]

    return None


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

    cmd = [Path(sys.executable).as_posix(), webui_path / launch_script] + launch_args
    try:
        run_cmd(cmd, custom_env=custom_env, cwd=webui_path)
    except KeyboardInterrupt:
        logger.info("已关闭 WebUI")
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
    list_only: bool | None = False,
) -> list[Path] | None:
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
        list_only (bool | None):
            是否仅列出模型列表并退出

    Returns:
        list[Path]:
            模型的保存地址
    """

    def _input_to_int_list(_input: str) -> list[str] | None:
        try:
            return list({int(_i) for _i in _input.split()})
        except Exception:
            return None

    model_list = export_model_list(dtype)

    if list_only:
        print_divider("=")
        display_model_table(model_list)
        print_divider("=")
        return None

    display_model = True
    input_err = (0, None)

    if interactive_mode:
        while True:
            if display_model:
                print_divider("=")
                display_model_table(model_list)
                print_divider("=")

            display_model = True
            i, m = input_err
            if i == 1:
                logger.warning("输入有误, 请重试")
            elif i == 2:
                logger.warning("输入的数字有误, %s, 请重新输入", m)
            input_err = (0, None)
            print(
                "请选择要下载的模型\n"
                "提示:\n"
                "1. 输入数字后回车\n"
                "2. 如果需要下载多个模型, 可以输入多个数字并使用空格隔开\n"
                "3. 输入 search 可以进入列表搜索模式, 可搜索列表中已有的模型\n"
                "4. 输入 exit 退出模型下载"
            )
            user_input = input("==> ").strip()

            if user_input == "exit":
                return None

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

            if result is None or len(result) == 0:
                input_err = (1, None)
                continue

            try:
                return download_model(
                    dtype=dtype,
                    base_path=webui_path,
                    download_resource_type=download_resource_type,
                    model_index=result,
                    downloader=downloader,
                )
            except ValueError as e:
                input_err = (2, str(e))
                continue
    else:
        return download_model(
            dtype=dtype,
            base_path=webui_path,
            download_resource_type=download_resource_type,
            model_name=model_name,
            model_index=model_index,
            downloader=downloader,
        )


def apply_git_base_config_and_github_mirror(
    git_config_path: Path | None = None,
    use_github_mirror: bool | None = False,
    custom_github_mirror: str | list[str] | None = None,
    origin_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """为 Git 应用基本配置并设置 Github 镜像源

    Args:
        git_config_path (Path | None):
            Git 配置文件路径
        use_github_mirror (bool | None):
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
        git_config_path = Path().cwd() / ".gitconfig"
    else:
        git_config_path = Path(config_path_env)
        git_config_path.parent.mkdir(parents=True, exist_ok=True)

    set_github_mirror(
        mirror=(GITHUB_MIRROR_LIST if custom_github_mirror is None else custom_github_mirror) if use_github_mirror else None,
        config_path=git_config_path,
    )
    set_git_base_config(git_config_path)
    custom_env["GIT_CONFIG_GLOBAL"] = git_config_path.as_posix()

    return custom_env
