"""CLI 其他模块"""

import argparse
import json
import sys
import os
import time
from pathlib import Path
from typing import cast

from sd_webui_all_in_one.proxy import (
    get_system_proxy_address,
    test_proxy_connectivity,
)
from sd_webui_all_in_one import config as app_config
from sd_webui_all_in_one.updater import (
    check_aria2_version,
    check_and_update_uv,
    check_and_update_pip,
)
from sd_webui_all_in_one.cli_manager.auto_mirror import (
    add_auto_mirror_argument,
    with_auto_mirror,
)
from sd_webui_all_in_one.base_manager.hotpatcher_manager import (
    DEFAULT_HOTPATCHER_CONFIG_PATH,
    apply_hotpatcher_config,
    ensure_hotpatcher_pythonpath_first,
    export_hotpatcher_default_config,
    get_hotpatcher_catalog,
    launch_hotpatcher_manager_gui,
    load_hotpatcher_config,
    save_hotpatcher_config,
)
from sd_webui_all_in_one.downloader import download_file
from sd_webui_all_in_one.downloader.types import (
    DOWNLOAD_TOOL_TYPE_LIST,
    DownloadToolType,
)
from sd_webui_all_in_one.downloader.requests_downloader import (
    DEFAULT_MAX_CONNECTION_PER_SERVER,
    DEFAULT_MIN_SPLIT_SIZE,
    DEFAULT_PIECE_LENGTH,
    DEFAULT_SPLIT,
)
from sd_webui_all_in_one.archive_manager import (
    create_archive,
    extract_archive,
)
from sd_webui_all_in_one.mirror_manager import get_pypi_mirror_config
from sd_webui_all_in_one.repo_manager import (
    ApiType,
    RepoManager,
    RepoType,
)
from sd_webui_all_in_one.portable_manager import (
    PortableRepoSourceConfig,
    PortableUploadTargetConfig,
    build_portable_list_from_repositories,
    save_portable_list,
    upload_portable_package_to_repositories,
)
from sd_webui_all_in_one.config import (
    LOGGER_NAME,
    LOGGER_COLOR,
    LOGGER_LEVEL,
    SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH,
)
from sd_webui_all_in_one.optimize import (
    get_cuda_malloc_var,
    get_tcmalloc_path,
    get_tcmalloc_var,
)
from sd_webui_all_in_one.tunnel import TunnelManager
from sd_webui_all_in_one.logger import get_logger, silence_logger_output
from sd_webui_all_in_one.utils import (
    print_divider,
    normalized_filepath,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

REPO_API_TYPE_LIST = ["huggingface", "modelscope"]
"""支持的仓库 API 类型"""

REPO_TYPE_LIST = ["model", "dataset", "space"]
"""支持的仓库类型"""

REPO_OUTPUT_FORMAT_LIST = ["json", "text"]
"""仓库信息输出格式"""

REPO_METADATA_TEXT_FIELDS = ["path", "type", "size", "sha256", "revision"]
"""仓库元数据文本输出字段"""


def check_pip(
    use_pypi_mirror: bool = False,
) -> None:
    """检查 Pip 版本并尝试更新

    Args:
        use_pypi_mirror (bool):
            是否使用 PyPI 国内镜像
    """
    check_and_update_pip(
        custom_env=get_pypi_mirror_config(use_cn_mirror=use_pypi_mirror),
    )


def check_uv(
    use_pypi_mirror: bool = False,
) -> None:
    """检查 uv 版本并尝试更新

    Args:
        use_pypi_mirror (bool):
            是否使用 PyPI 国内镜像
    """
    check_and_update_uv(
        custom_env=get_pypi_mirror_config(use_cn_mirror=use_pypi_mirror),
    )


def check_aria2() -> None:
    """检查 Aria2 是否需要更新"""
    if check_aria2_version():
        sys.exit(1)
    else:
        sys.exit(0)


def get_proxy() -> None:
    """获取当前系统中的代理地址"""
    addr = get_system_proxy_address()
    if addr is not None and test_proxy_connectivity(addr):
        print(addr)


def get_cuda_malloc() -> None:
    """获取支持当前设备的 CUDA 内存分配器配置"""
    silence_logger_output()
    conf = get_cuda_malloc_var()
    if conf is not None:
        print(conf)


def get_tcmalloc(
    output_path: bool = False,
) -> None:
    """获取支持当前系统的 TCMalloc 配置

    Args:
        output_path (bool):
            是否只输出可用的 TCMalloc 库路径
    """
    silence_logger_output()
    conf = get_tcmalloc_path() if output_path else get_tcmalloc_var()
    if conf is not None:
        print(conf)


def get_env_config() -> None:
    """获取 SD WebUI All In One 使用的环境变量信息"""
    env_config = {
        "SD_WEBUI_ALL_IN_ONE_LOGGER_NAME": app_config.LOGGER_NAME,
        "SD_WEBUI_ALL_IN_ONE_LOGGER_LEVEL": app_config.LOGGER_LEVEL,
        "SD_WEBUI_ALL_IN_ONE_LOGGER_COLOR": app_config.LOGGER_COLOR,
        "SD_WEBUI_ALL_IN_ONE_RETRY_TIMES": app_config.RETRY_TIMES,
        "SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH": app_config.SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH,
        "SD_WEBUI_ROOT": app_config.SD_WEBUI_ROOT_PATH,
        "COMFYUI_ROOT": app_config.COMFYUI_ROOT_PATH,
        "FOOOCUS_ROOT": app_config.FOOOCUS_ROOT_PATH,
        "INVOKEAI_ROOT": app_config.INVOKEAI_ROOT_PATH,
        "SD_TRAINER_ROOT": app_config.SD_TRAINER_ROOT_PATH,
        "SD_SCRIPTS_ROOT": app_config.SD_SCRIPTS_ROOT_PATH,
        "QWEN_TTS_WEBUI_ROOT": app_config.QWEN_TTS_WEBUI_ROOT_PATH,
        "SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR": app_config.SD_WEBUI_ALL_IN_ONE_EXTRA_PYPI_MIRROR,
        "SD_WEBUI_ALL_IN_ONE_PROXY": app_config.SD_WEBUI_ALL_IN_ONE_PROXY,
        "SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH": app_config.SD_WEBUI_ALL_IN_ONE_SET_CACHE_PATH,
        "SD_WEBUI_ALL_IN_ONE_SET_CONFIG": app_config.SD_WEBUI_ALL_IN_ONE_SET_CONFIG,
        "SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY": app_config.SD_WEBUI_ALL_IN_ONE_SKIP_TORCH_DEVICE_COMPATIBILITY,
        "SD_WEBUI_ALL_IN_ONE_RAISE_WEBUI_RUNTIME_ERROR": app_config.SD_WEBUI_ALL_IN_ONE_RAISE_WEBUI_RUNTIME_ERROR,
        "SD_WEBUI_ALL_IN_ONE_RAISE_CHECK_ENV_ERROR_ON_LAUNCH": app_config.SD_WEBUI_ALL_IN_ONE_RAISE_CHECK_ENV_ERROR_ON_LAUNCH,
        "SD_WEBUI_ALL_IN_ONE_IGNORE_INSTALL_DEP_TYPE": app_config.SD_WEBUI_ALL_IN_ONE_IGNORE_INSTALL_DEP_TYPE,
    }
    for name, value in env_config.items():
        if isinstance(value, Path):
            value = value.as_posix()
        print(f"{name}: '{value}'")


def download_file_cli(
    url: str,
    path: Path | None = None,
    save_name: str | None = None,
    tool: DownloadToolType | None = None,
    progress: bool = True,
    split: int = DEFAULT_SPLIT,
    max_connection_per_server: int = DEFAULT_MAX_CONNECTION_PER_SERVER,
    min_split_size: int = DEFAULT_MIN_SPLIT_SIZE,
    piece_length: int = DEFAULT_PIECE_LENGTH,
    allow_piece_length_change: bool = False,
    continue_download: bool = False,
    max_tries: int = 5,
    retry_wait: int = 0,
    conditional_get: bool = False,
    remote_time: bool = True,
) -> None:
    """下载文件并输出保存路径

    Args:
        url (str):
            文件下载链接
        path (Path | None):
            文件下载路径
        save_name (str | None):
            文件保存名称
        tool (DownloadToolType | None):
            下载工具
        progress (bool):
            是否启用下载进度条
        split (int):
            aria2 风格的单文件最大分割数
        max_connection_per_server (int):
            aria2 风格的单服务器最大连接数
        min_split_size (int):
            aria2 风格的最小切分大小
        piece_length (int):
            aria2 风格的 piece 大小
        allow_piece_length_change (bool):
            piece_length 与已有控制文件不一致时, 是否允许转换已完成 bitfield
        continue_download (bool):
            没有匹配控制文件时, 是否从已有文件推断断点续传进度
        max_tries (int):
            单个分片的最大尝试次数
        retry_wait (int):
            HTTP 503 重试前等待秒数
        conditional_get (bool):
            已有本地文件时是否发送 If-Modified-Since, 远端返回 304 时复用本地文件
        remote_time (bool):
            下载完成后是否把本地文件 mtime 设置为远端 Last-Modified
    """
    download_file(
        url=url,
        path=path,
        save_name=save_name,
        tool=tool,
        progress=progress,
        split=split,
        max_connection_per_server=max_connection_per_server,
        min_split_size=min_split_size,
        piece_length=piece_length,
        allow_piece_length_change=allow_piece_length_change,
        continue_download=continue_download,
        max_tries=max_tries,
        retry_wait=retry_wait,
        conditional_get=conditional_get,
        remote_time=remote_time,
    )


def extract_archive_cli(
    archive_path: Path,
    output: Path,
    progress: bool = True,
) -> None:
    """解压压缩包

    Args:
        archive_path (Path):
            压缩包路径
        output (Path):
            解压输出路径
        progress (bool):
            是否启用解压进度条
    """
    extract_archive(
        archive_path=archive_path,
        extract_to=output,
        progress=progress,
    )


def compress_archive_cli(
    sources: list[Path],
    output: Path,
    progress: bool = True,
) -> None:
    """创建压缩包

    Args:
        sources (list[Path]):
            要压缩的文件或目录列表
        output (Path):
            压缩包保存路径
        progress (bool):
            是否启用压缩进度条
    """
    create_archive(
        sources=sources,
        archive_path=output,
        progress=progress,
    )


def start_tunnel(
    port: int,
    workspace: Path | None = None,
    use_ngrok: bool = False,
    ngrok_token: str | None = None,
    use_cloudflare: bool = False,
    use_remote_moe: bool = False,
    use_localhost_run: bool = False,
    use_gradio: bool = False,
    use_pinggy_io: bool = False,
    use_zrok: bool = False,
    zrok_token: str | None = None,
) -> None:
    """启动内网穿透

    Args:
        port (int):
            要进行端口映射的端口
        workspace (Path | None):
            工作区路径，默认为当前目录
        use_ngrok (bool):
            启用 Ngrok 内网穿透
        ngrok_token (str | None):
            Ngrok 账号 Token
        use_cloudflare (bool):
            启用 CloudFlare 内网穿透
        use_remote_moe (bool):
            启用 remote.moe 内网穿透
        use_localhost_run (bool):
            使用 localhost.run 内网穿透
        use_gradio (bool):
            使用 Gradio 内网穿透
        use_pinggy_io (bool):
            使用 pinggy.io 内网穿透
        use_zrok (bool):
            使用 Zrok 内网穿透
        zrok_token (str | None):
            Zrok 账号 Token
    """
    if workspace is None:
        workspace = Path.cwd()

    logger.info("启动内网穿透，端口: %s", port)
    logger.info("工作区: %s", workspace)

    try:
        with TunnelManager(workspace=workspace, port=port) as manager:
            tunnel_url = manager.start_tunnel(
                use_ngrok=use_ngrok,
                ngrok_token=ngrok_token,
                use_cloudflare=use_cloudflare,
                use_remote_moe=use_remote_moe,
                use_localhost_run=use_localhost_run,
                use_gradio=use_gradio,
                use_pinggy_io=use_pinggy_io,
                use_zrok=use_zrok,
                zrok_token=zrok_token,
                check=False,
            )

            print_divider()
            logger.info("本地地址: %s", tunnel_url["local_url"])
            logger.info("内网穿透地址:")
            for service, url in tunnel_url.items():
                if service != "local_url" and url:
                    print(f"  - {service}: {url}")
            print_divider()
            logger.info("按 Ctrl + C 停止内网穿透")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("正在停止内网穿透")
    except Exception as e:
        logger.error("启动内网穿透失败: %s", e)
        sys.exit(1)


def _print_json(data: dict | list) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _create_repo_manager(
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> RepoManager:
    """创建仓库管理器, 命令参数未传 token 时回退到环境变量"""
    return RepoManager(
        hf_token=hf_token if hf_token is not None else os.environ.get("HF_TOKEN"),
        ms_token=ms_token if ms_token is not None else os.environ.get("MODELSCOPE_API_TOKEN"),
    )


def _print_repo_files(files: list[str], output_format: str) -> None:
    """输出仓库文件列表"""
    if output_format == "json":
        _print_json(files)
        return

    for file in files:
        print(file)


def _repo_metadata_text_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _print_repo_metadata(
    metadata: list[dict[str, object]],
    output_format: str,
) -> None:
    """输出仓库文件元数据"""
    if output_format == "json":
        _print_json(metadata)
        return

    print("\t".join(REPO_METADATA_TEXT_FIELDS))
    for item in metadata:
        print("\t".join(_repo_metadata_text_value(item.get(field)) for field in REPO_METADATA_TEXT_FIELDS))


def _default_portable_list_output() -> Path:
    """获取默认整合包资源列表输出路径"""
    return SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH / "portable_list.json"


def _validate_repo_type(
    value: str,
) -> RepoType:
    """校验仓库类型并转换为 RepoType"""
    if value not in REPO_TYPE_LIST:
        raise ValueError(f"未知的仓库类型: {value}")
    return cast(RepoType, value)


def _add_portable_source_config(
    sources: list[PortableRepoSourceConfig],
    source: ApiType,
    repo_id: str | None,
    repo_type: str,
) -> None:
    """添加整合包下载源配置"""
    if not repo_id:
        return
    sources.append(
        {
            "source": source,
            "repo_id": repo_id,
            "repo_type": _validate_repo_type(repo_type),
        }
    )


def portable_list_cli(
    output: Path,
    hf_repo_id: str | None = None,
    hf_repo_type: str = "model",
    ms_repo_id: str | None = None,
    ms_repo_type: str = "model",
    revision: str | None = None,
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> None:
    """生成整合包资源列表

    Args:
        output (Path):
            输出文件路径
        hf_repo_id (str | None):
            HuggingFace 仓库 ID
        hf_repo_type (str):
            HuggingFace 仓库类型
        ms_repo_id (str | None):
            ModelScope 仓库 ID
        ms_repo_type (str):
            ModelScope 仓库类型
        revision (str | None):
            仓库分支、标签或提交哈希
        hf_token (str | None):
            HuggingFace Token
        ms_token (str | None):
            ModelScope Token
    """
    sources: list[PortableRepoSourceConfig] = []
    _add_portable_source_config(sources, "huggingface", hf_repo_id, hf_repo_type)
    _add_portable_source_config(sources, "modelscope", ms_repo_id, ms_repo_type)

    manager = _create_repo_manager(hf_token=hf_token, ms_token=ms_token)
    portable_list = build_portable_list_from_repositories(
        manager=manager,
        sources=sources,
        revision=revision,
    )
    save_portable_list(portable_list, output)
    logger.info("整合包资源列表已保存: %s", output)


def portable_upload_cli(
    upload_path: Path,
    hf_repo_id: str | None = None,
    hf_repo_type: str = "model",
    ms_repo_id: str | None = None,
    ms_repo_type: str = "model",
    path_in_repo: str | None = None,
    revision: str | None = None,
    visibility: bool = False,
    num_threads: int = 1,
    target_workers: int | None = None,
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> None:
    """上传整合包目录到 HuggingFace / ModelScope 仓库

    Args:
        upload_path (Path):
            要上传的本地目录
        hf_repo_id (str | None):
            HuggingFace 仓库 ID
        hf_repo_type (str):
            HuggingFace 仓库类型
        ms_repo_id (str | None):
            ModelScope 仓库 ID
        ms_repo_type (str):
            ModelScope 仓库类型
        path_in_repo (str | None):
            仓库中的上传路径前缀
        revision (str | None):
            仓库分支、标签或提交哈希
        visibility (bool):
            创建仓库时是否设为公开
        num_threads (int):
            单个目标仓库内部的上传线程数
        target_workers (int | None):
            上传目标之间的并发数
        hf_token (str | None):
            HuggingFace Token
        ms_token (str | None):
            ModelScope Token
    """
    targets: list[PortableUploadTargetConfig] = []
    _add_portable_source_config(targets, "huggingface", hf_repo_id, hf_repo_type)
    _add_portable_source_config(targets, "modelscope", ms_repo_id, ms_repo_type)

    manager = _create_repo_manager(hf_token=hf_token, ms_token=ms_token)
    upload_portable_package_to_repositories(
        manager=manager,
        upload_path=upload_path,
        targets=targets,
        path_in_repo=path_in_repo,
        revision=revision,
        visibility=visibility,
        num_threads=num_threads,
        target_workers=target_workers,
    )


def repo_list_cli(
    api_type: ApiType,
    repo_id: str,
    repo_type: RepoType = "model",
    revision: str | None = None,
    output_format: str = "json",
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> None:
    """输出 HuggingFace / ModelScope 仓库文件列表

    Args:
        api_type (ApiType):
            仓库 API 类型
        repo_id (str):
            仓库 ID
        repo_type (RepoType):
            仓库类型
        revision (str | None):
            仓库分支、标签或提交哈希
        output_format (str):
            输出格式
        hf_token (str | None):
            HuggingFace Token
        ms_token (str | None):
            ModelScope Token
    """
    manager = _create_repo_manager(hf_token=hf_token, ms_token=ms_token)
    files = manager.get_repo_file(
        api_type=api_type,
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
    )
    _print_repo_files(files, output_format)


def repo_metadata_cli(
    api_type: ApiType,
    repo_id: str,
    repo_type: RepoType = "model",
    revision: str | None = None,
    include_dirs: bool = False,
    include_raw: bool = False,
    output_format: str = "json",
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> None:
    """输出 HuggingFace / ModelScope 仓库文件元数据

    Args:
        api_type (ApiType):
            仓库 API 类型
        repo_id (str):
            仓库 ID
        repo_type (RepoType):
            仓库类型
        revision (str | None):
            仓库分支、标签或提交哈希
        include_dirs (bool):
            是否包含目录条目
        include_raw (bool):
            是否包含第三方库原始返回
        output_format (str):
            输出格式
        hf_token (str | None):
            HuggingFace Token
        ms_token (str | None):
            ModelScope Token
    """
    manager = _create_repo_manager(hf_token=hf_token, ms_token=ms_token)
    metadata = manager.get_repo_files_metadata(
        api_type=api_type,
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
        include_dirs=include_dirs,
        include_raw=include_raw,
    )
    _print_repo_metadata(metadata, output_format)


def repo_url_cli(
    api_type: ApiType,
    repo_id: str,
    file_path: str,
    repo_type: RepoType = "model",
    revision: str | None = None,
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> None:
    """输出 HuggingFace / ModelScope 仓库文件下载地址

    Args:
        api_type (ApiType):
            仓库 API 类型
        repo_id (str):
            仓库 ID
        file_path (str):
            仓库中的文件路径
        repo_type (RepoType):
            仓库类型
        revision (str | None):
            仓库分支、标签或提交哈希
        hf_token (str | None):
            HuggingFace Token
        ms_token (str | None):
            ModelScope Token
    """
    manager = _create_repo_manager(hf_token=hf_token, ms_token=ms_token)
    url = manager.get_repo_file_download_url(
        api_type=api_type,
        repo_id=repo_id,
        file_path=file_path,
        repo_type=repo_type,
        revision=revision,
    )
    print(url)


def repo_check_cli(
    api_type: ApiType,
    repo_id: str,
    repo_type: RepoType = "model",
    visibility: bool = False,
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> None:
    """检查 HuggingFace / ModelScope 仓库是否存在, 不存在时创建

    Args:
        api_type (ApiType):
            仓库 API 类型
        repo_id (str):
            仓库 ID
        repo_type (RepoType):
            仓库类型
        visibility (bool):
            创建仓库时是否设为公开
        hf_token (str | None):
            HuggingFace Token
        ms_token (str | None):
            ModelScope Token
    """
    manager = _create_repo_manager(hf_token=hf_token, ms_token=ms_token)
    manager.check_repo(
        api_type=api_type,
        repo_id=repo_id,
        repo_type=repo_type,
        visibility=visibility,
    )


def repo_upload_cli(
    api_type: ApiType,
    repo_id: str,
    upload_path: Path,
    repo_type: RepoType = "model",
    path_in_repo: str | None = None,
    visibility: bool = False,
    num_threads: int = 1,
    revision: str | None = None,
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> None:
    """上传本地目录到 HuggingFace / ModelScope 仓库

    Args:
        api_type (ApiType):
            仓库 API 类型
        repo_id (str):
            仓库 ID
        upload_path (Path):
            要上传的本地目录
        repo_type (RepoType):
            仓库类型
        path_in_repo (str | None):
            仓库中的上传路径前缀
        visibility (bool):
            创建仓库时是否设为公开
        num_threads (int):
            上传线程数
        revision (str | None):
            上传目标分支、标签或提交哈希
        hf_token (str | None):
            HuggingFace Token
        ms_token (str | None):
            ModelScope Token
    """
    manager = _create_repo_manager(hf_token=hf_token, ms_token=ms_token)
    manager.upload_files_to_repo(
        api_type=api_type,
        repo_id=repo_id,
        upload_path=upload_path,
        path_in_repo=path_in_repo,
        repo_type=repo_type,
        visibility=visibility,
        num_threads=num_threads,
        revision=revision,
    )


def repo_download_cli(
    api_type: ApiType,
    repo_id: str,
    local_dir: Path,
    repo_type: RepoType = "model",
    folder: str | None = None,
    num_threads: int = 8,
    revision: str | None = None,
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> None:
    """从 HuggingFace / ModelScope 仓库下载文件

    Args:
        api_type (ApiType):
            仓库 API 类型
        repo_id (str):
            仓库 ID
        local_dir (Path):
            本地下载目录
        repo_type (RepoType):
            仓库类型
        folder (str | None):
            指定下载路径前缀或文件
        num_threads (int):
            下载线程数
        revision (str | None):
            下载来源分支、标签或提交哈希
        hf_token (str | None):
            HuggingFace Token
        ms_token (str | None):
            ModelScope Token
    """
    manager = _create_repo_manager(hf_token=hf_token, ms_token=ms_token)
    manager.download_files_from_repo(
        api_type=api_type,
        repo_id=repo_id,
        local_dir=local_dir,
        repo_type=repo_type,
        folder=folder,
        num_threads=num_threads,
        revision=revision,
    )


def repo_mirror_cli(
    src_api_type: ApiType,
    dst_api_type: ApiType,
    src_repo_id: str,
    dst_repo_id: str,
    src_repo_type: RepoType = "model",
    dst_repo_type: RepoType = "model",
    visibility: bool = False,
    revision: str | None = None,
    num_threads: int = 1,
    retry_times: int = app_config.RETRY_TIMES,
    use_fast_download: bool = False,
    download_tool: DownloadToolType | None = "requests",
    download_split: int = 5,
    download_progress: bool = True,
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> None:
    """镜像 HuggingFace / ModelScope 仓库文件

    Args:
        src_api_type (ApiType):
            源仓库 API 类型
        dst_api_type (ApiType):
            目标仓库 API 类型
        src_repo_id (str):
            源仓库 ID
        dst_repo_id (str):
            目标仓库 ID
        src_repo_type (RepoType):
            源仓库类型
        dst_repo_type (RepoType):
            目标仓库类型
        visibility (bool):
            创建目标仓库时是否设为公开
        revision (str | None):
            源仓库读取和目标仓库上传的分支、标签或提交哈希
        num_threads (int):
            镜像线程数
        retry_times (int):
            单个文件镜像重试次数
        use_fast_download (bool):
            是否使用内置 downloader 下载源文件
        download_tool (DownloadToolType | None):
            启用快速下载时使用的下载工具
        download_split (int):
            启用快速下载时的下载分片数
        download_progress (bool):
            启用快速下载时是否显示下载进度
        hf_token (str | None):
            HuggingFace Token
        ms_token (str | None):
            ModelScope Token
    """
    manager = _create_repo_manager(hf_token=hf_token, ms_token=ms_token)
    manager.mirror_repo_files(
        src_api_type=src_api_type,
        dst_api_type=dst_api_type,
        src_repo_id=src_repo_id,
        dst_repo_id=dst_repo_id,
        src_repo_type=src_repo_type,
        dst_repo_type=dst_repo_type,
        visibility=visibility,
        revision=revision,
        num_threads=num_threads,
        retry_times=retry_times,
        use_fast_download=use_fast_download,
        download_tool=download_tool,
        download_split=download_split,
        download_progress=download_progress,
    )


def _add_repo_auth_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--hf-token", type=str, default=None, help="HuggingFace Token, 默认读取 HF_TOKEN")
    parser.add_argument("--ms-token", type=str, default=None, help="ModelScope Token, 默认读取 MODELSCOPE_API_TOKEN")


def _add_repo_type_argument(
    parser: argparse.ArgumentParser,
    default: str = "model",
) -> None:
    parser.add_argument("--repo-type", choices=REPO_TYPE_LIST, default=default, help="仓库类型")


def _add_repo_revision_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--revision", type=str, default=None, help="仓库分支、标签或提交哈希")


def _add_repo_output_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", dest="output_format", choices=REPO_OUTPUT_FORMAT_LIST, default="json", help="输出格式")


def export_hotpatcher_config_cli(output: Path | None = None, force: bool = False) -> None:
    """导出 hotpatcher 默认配置

    Args:
        output (Path | None):
            配置导出路径
        force (bool):
            是否覆盖已有文件
    """
    path = export_hotpatcher_default_config(output, overwrite=force)
    logger.info("Hotpatcher 默认配置已导出: %s", path)


def normalize_hotpatcher_config_cli(config: Path | None = None, write_back: bool = False) -> None:
    """规范化 hotpatcher 配置

    Args:
        config (Path | None):
            配置文件路径
        write_back (bool):
            是否写回配置文件
    """
    normalized = load_hotpatcher_config(config, normalize=True)
    if write_back:
        save_hotpatcher_config(config, normalized)
        logger.info("Hotpatcher 配置已规范化并写回: %s", config)
        return
    _print_json(normalized)


def apply_hotpatcher_config_cli(config: Path | None = None) -> None:
    """应用 hotpatcher 配置到当前进程

    Args:
        config (Path | None):
            配置文件路径
    """
    _print_json(apply_hotpatcher_config(config))


def show_hotpatcher_catalog_cli() -> None:
    """显示 hotpatcher 功能目录"""
    _print_json(get_hotpatcher_catalog())


def launch_hotpatcher_gui_cli(
    config: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    token: str = "",
) -> None:
    """启动 hotpatcher 配置管理 GUI

    Args:
        config (Path | None):
            配置文件路径
        host (str):
            runtime host 监听地址
        port (int):
            runtime host 监听端口
        token (str):
            runtime host 访问令牌
    """
    launch_hotpatcher_manager_gui(config_path=config, host=host, port=port, token=token)


def get_hotpatcher_pythonpath_cli() -> None:
    """输出注入 Hotpatcher 路径后的 PYTHONPATH"""
    print(ensure_hotpatcher_pythonpath_first(os.environ.copy()).get("PYTHONPATH", ""))


def register_manager(
    subparsers: "argparse._SubParsersAction",
) -> None:
    """注册 SD WebUI All In One 模块及其子命令

    Args:
        subparsers (argparse._SubParsersAction):
            子命令行解析器
    """
    sd_webui_all_in_one_parser: argparse.ArgumentParser = subparsers.add_parser("self-manager", help="SD WebUI All In One 相关命令")
    sd_webui_all_in_one_sub = sd_webui_all_in_one_parser.add_subparsers(dest="sd_webui_all_in_one_action", required=True)

    check_p = sd_webui_all_in_one_sub.add_parser("check", help="检查并更新组件")
    check_sub = check_p.add_subparsers(dest="check_action", required=True)

    # check aria2
    check_aria2_p = check_sub.add_parser("aria2", help="检查 Aria2 是否需要更新 (当退出代码非 0 时则说明需要更新)")
    check_aria2_p.set_defaults(func=lambda args: check_aria2())

    # check pip
    check_pip_p = check_sub.add_parser("pip", help="检查 Pip 是否需要更新并尝试更新")
    check_pip_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    add_auto_mirror_argument(check_pip_p)
    check_pip_p.set_defaults(
        func=with_auto_mirror(
            lambda args: check_pip(
                use_pypi_mirror=args.use_pypi_mirror,
            )
        )
    )

    # check uv
    check_uv_p = check_sub.add_parser("uv", help="检查 uv 是否需要更新并尝试更新")
    check_uv_p.add_argument("--no-pypi-mirror", action="store_false", dest="use_pypi_mirror", help="不使用国内 PyPI 镜像源")
    add_auto_mirror_argument(check_uv_p)
    check_uv_p.set_defaults(
        func=with_auto_mirror(
            lambda args: check_uv(
                use_pypi_mirror=args.use_pypi_mirror,
            )
        )
    )

    patcher_p = sd_webui_all_in_one_sub.add_parser("patcher", help="Hotpatcher 配置管理")
    patcher_sub = patcher_p.add_subparsers(dest="patcher_action", required=True)

    patcher_export_p = patcher_sub.add_parser("export-config", help="导出 Hotpatcher 默认配置")
    patcher_export_p.add_argument("--output", type=normalized_filepath, default=DEFAULT_HOTPATCHER_CONFIG_PATH, help="输出配置文件路径")
    patcher_export_p.add_argument("--force", action="store_true", help="覆盖已有配置文件")
    patcher_export_p.set_defaults(
        func=lambda args: export_hotpatcher_config_cli(
            output=args.output,
            force=args.force,
        )
    )

    patcher_normalize_p = patcher_sub.add_parser("normalize-config", help="规范化 Hotpatcher 配置")
    patcher_normalize_p.add_argument("--config", type=normalized_filepath, default=DEFAULT_HOTPATCHER_CONFIG_PATH, help="配置文件路径")
    patcher_normalize_p.add_argument("--write-back", action="store_true", help="将规范化后的配置写回文件")
    patcher_normalize_p.set_defaults(
        func=lambda args: normalize_hotpatcher_config_cli(
            config=args.config,
            write_back=args.write_back,
        )
    )

    patcher_apply_p = patcher_sub.add_parser("apply-config", help="应用 Hotpatcher 配置到当前进程")
    patcher_apply_p.add_argument("--config", type=normalized_filepath, default=DEFAULT_HOTPATCHER_CONFIG_PATH, help="配置文件路径")
    patcher_apply_p.set_defaults(
        func=lambda args: apply_hotpatcher_config_cli(
            config=args.config,
        )
    )

    patcher_catalog_p = patcher_sub.add_parser("catalog", help="显示 Hotpatcher 功能目录")
    patcher_catalog_p.set_defaults(func=lambda args: show_hotpatcher_catalog_cli())

    patcher_pythonpath_p = patcher_sub.add_parser("get-pythonpath", help="输出注入 Hotpatcher 路径后的 PYTHONPATH")
    patcher_pythonpath_p.set_defaults(func=lambda args: get_hotpatcher_pythonpath_cli())

    patcher_gui_p = patcher_sub.add_parser("gui", help="启动 Hotpatcher 配置管理 GUI")
    patcher_gui_p.add_argument("--config", type=normalized_filepath, default=DEFAULT_HOTPATCHER_CONFIG_PATH, help="配置文件路径")
    patcher_gui_p.add_argument("--host", type=str, default="127.0.0.1", help="Runtime host 监听地址")
    patcher_gui_p.add_argument("--port", type=int, default=8765, help="Runtime host 监听端口")
    patcher_gui_p.add_argument("--token", type=str, default="", help="Runtime host 连接 token")
    patcher_gui_p.set_defaults(
        func=lambda args: launch_hotpatcher_gui_cli(
            config=args.config,
            host=args.host,
            port=args.port,
            token=args.token,
        )
    )

    get_p = sd_webui_all_in_one_sub.add_parser("get", help="获取配置或环境信息")
    get_sub = get_p.add_subparsers(dest="get_action", required=True)

    # get proxy
    get_proxy_p = get_sub.add_parser("proxy", help="获取系统代理地址")
    get_proxy_p.set_defaults(func=lambda args: get_proxy())

    # get cuda-malloc
    get_cuda_malloc_p = get_sub.add_parser("cuda-malloc", help="获取支持当前设备的 CUDA 内存分配器配置")
    get_cuda_malloc_p.set_defaults(func=lambda args: get_cuda_malloc())

    # get tcmalloc
    get_tcmalloc_p = get_sub.add_parser("tcmalloc", help="获取支持当前系统的 TCMalloc 配置")
    get_tcmalloc_p.add_argument("--path", action="store_true", help="只输出可用的 TCMalloc 库路径")
    get_tcmalloc_p.set_defaults(func=lambda args: get_tcmalloc(output_path=args.path))

    # get env-config
    get_env_config_p = get_sub.add_parser("env-config", help="获取 SD WebUI All In One 使用的环境变量配置")
    get_env_config_p.set_defaults(func=lambda args: get_env_config())

    portable_p = sd_webui_all_in_one_sub.add_parser("portable", help="整合包资源管理")
    portable_sub = portable_p.add_subparsers(dest="portable_action", required=True)

    portable_list_p = portable_sub.add_parser("list", help="生成整合包资源列表")
    portable_list_p.add_argument("--output", type=normalized_filepath, default=_default_portable_list_output(), help="输出 JSON 文件路径")
    portable_list_p.add_argument("--hf-repo-id", type=str, default=None, help="HuggingFace 仓库 ID")
    portable_list_p.add_argument("--hf-repo-type", choices=REPO_TYPE_LIST, default="model", help="HuggingFace 仓库类型")
    portable_list_p.add_argument("--ms-repo-id", type=str, default=None, help="ModelScope 仓库 ID")
    portable_list_p.add_argument("--ms-repo-type", choices=REPO_TYPE_LIST, default="model", help="ModelScope 仓库类型")
    portable_list_p.add_argument("--revision", type=str, default=None, help="仓库分支、标签或提交哈希")
    _add_repo_auth_arguments(portable_list_p)
    portable_list_p.set_defaults(
        func=lambda args: portable_list_cli(
            output=args.output,
            hf_repo_id=args.hf_repo_id,
            hf_repo_type=args.hf_repo_type,
            ms_repo_id=args.ms_repo_id,
            ms_repo_type=args.ms_repo_type,
            revision=args.revision,
            hf_token=args.hf_token,
            ms_token=args.ms_token,
        )
    )

    portable_upload_p = portable_sub.add_parser("upload", help="上传整合包目录到仓库")
    portable_upload_p.add_argument("upload_path", type=normalized_filepath, help="要上传的本地目录")
    portable_upload_p.add_argument("--hf-repo-id", type=str, default=None, help="HuggingFace 仓库 ID")
    portable_upload_p.add_argument("--hf-repo-type", choices=REPO_TYPE_LIST, default="model", help="HuggingFace 仓库类型")
    portable_upload_p.add_argument("--ms-repo-id", type=str, default=None, help="ModelScope 仓库 ID")
    portable_upload_p.add_argument("--ms-repo-type", choices=REPO_TYPE_LIST, default="model", help="ModelScope 仓库类型")
    portable_upload_p.add_argument("--revision", type=str, default=None, help="上传目标分支、标签或提交哈希")
    portable_upload_p.add_argument("--path-in-repo", type=str, default=None, help="仓库中的上传路径前缀，默认上传到仓库根目录")
    portable_upload_p.add_argument("--public", action="store_true", help="仓库不存在并需要创建时设为公开仓库")
    portable_upload_p.add_argument("--threads", type=int, default=1, dest="num_threads", help="单个目标仓库内部的上传线程数")
    portable_upload_p.add_argument("--target-workers", type=int, default=None, help="上传目标之间的并发数，默认按目标数量并发")
    _add_repo_auth_arguments(portable_upload_p)
    portable_upload_p.set_defaults(
        func=lambda args: portable_upload_cli(
            upload_path=args.upload_path,
            path_in_repo=args.path_in_repo,
            hf_repo_id=args.hf_repo_id,
            hf_repo_type=args.hf_repo_type,
            ms_repo_id=args.ms_repo_id,
            ms_repo_type=args.ms_repo_type,
            revision=args.revision,
            visibility=args.public,
            num_threads=args.num_threads,
            target_workers=args.target_workers,
            hf_token=args.hf_token,
            ms_token=args.ms_token,
        )
    )

    repo_p = sd_webui_all_in_one_sub.add_parser("repo", help="HuggingFace / ModelScope 仓库管理")
    repo_sub = repo_p.add_subparsers(dest="repo_action", required=True)

    repo_list_p = repo_sub.add_parser("list", help="获取仓库文件列表")
    repo_list_p.add_argument("api_type", choices=REPO_API_TYPE_LIST, help="仓库 API 类型")
    repo_list_p.add_argument("repo_id", type=str, help="仓库 ID")
    _add_repo_type_argument(repo_list_p)
    _add_repo_revision_argument(repo_list_p)
    _add_repo_output_format_argument(repo_list_p)
    _add_repo_auth_arguments(repo_list_p)
    repo_list_p.set_defaults(
        func=lambda args: repo_list_cli(
            api_type=args.api_type,
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            revision=args.revision,
            output_format=args.output_format,
            hf_token=args.hf_token,
            ms_token=args.ms_token,
        )
    )

    repo_metadata_p = repo_sub.add_parser("metadata", help="获取仓库文件元数据")
    repo_metadata_p.add_argument("api_type", choices=REPO_API_TYPE_LIST, help="仓库 API 类型")
    repo_metadata_p.add_argument("repo_id", type=str, help="仓库 ID")
    _add_repo_type_argument(repo_metadata_p)
    _add_repo_revision_argument(repo_metadata_p)
    _add_repo_output_format_argument(repo_metadata_p)
    repo_metadata_p.add_argument("--include-dirs", action="store_true", help="包含目录条目")
    repo_metadata_p.add_argument("--include-raw", action="store_true", help="包含第三方库原始返回")
    _add_repo_auth_arguments(repo_metadata_p)
    repo_metadata_p.set_defaults(
        func=lambda args: repo_metadata_cli(
            api_type=args.api_type,
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            revision=args.revision,
            include_dirs=args.include_dirs,
            include_raw=args.include_raw,
            output_format=args.output_format,
            hf_token=args.hf_token,
            ms_token=args.ms_token,
        )
    )

    repo_url_p = repo_sub.add_parser("url", help="获取仓库文件下载地址")
    repo_url_p.add_argument("api_type", choices=REPO_API_TYPE_LIST, help="仓库 API 类型")
    repo_url_p.add_argument("repo_id", type=str, help="仓库 ID")
    repo_url_p.add_argument("file_path", type=str, help="仓库中的文件路径")
    _add_repo_type_argument(repo_url_p)
    _add_repo_revision_argument(repo_url_p)
    _add_repo_auth_arguments(repo_url_p)
    repo_url_p.set_defaults(
        func=lambda args: repo_url_cli(
            api_type=args.api_type,
            repo_id=args.repo_id,
            file_path=args.file_path,
            repo_type=args.repo_type,
            revision=args.revision,
            hf_token=args.hf_token,
            ms_token=args.ms_token,
        )
    )

    repo_check_p = repo_sub.add_parser("check", help="检查仓库是否存在, 不存在时创建")
    repo_check_p.add_argument("api_type", choices=REPO_API_TYPE_LIST, help="仓库 API 类型")
    repo_check_p.add_argument("repo_id", type=str, help="仓库 ID")
    _add_repo_type_argument(repo_check_p)
    repo_check_p.add_argument("--public", action="store_true", help="创建仓库时设为公开仓库")
    _add_repo_auth_arguments(repo_check_p)
    repo_check_p.set_defaults(
        func=lambda args: repo_check_cli(
            api_type=args.api_type,
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            visibility=args.public,
            hf_token=args.hf_token,
            ms_token=args.ms_token,
        )
    )

    repo_upload_p = repo_sub.add_parser("upload", help="上传本地目录到仓库")
    repo_upload_p.add_argument("api_type", choices=REPO_API_TYPE_LIST, help="仓库 API 类型")
    repo_upload_p.add_argument("repo_id", type=str, help="仓库 ID")
    repo_upload_p.add_argument("upload_path", type=normalized_filepath, help="要上传的本地目录")
    _add_repo_type_argument(repo_upload_p)
    _add_repo_revision_argument(repo_upload_p)
    repo_upload_p.add_argument("--path-in-repo", type=str, default=None, help="仓库中的上传路径前缀，默认上传到仓库根目录")
    repo_upload_p.add_argument("--public", action="store_true", help="创建仓库时设为公开仓库")
    repo_upload_p.add_argument("--threads", type=int, default=1, dest="num_threads", help="上传线程数")
    _add_repo_auth_arguments(repo_upload_p)
    repo_upload_p.set_defaults(
        func=lambda args: repo_upload_cli(
            api_type=args.api_type,
            repo_id=args.repo_id,
            upload_path=args.upload_path,
            path_in_repo=args.path_in_repo,
            repo_type=args.repo_type,
            visibility=args.public,
            num_threads=args.num_threads,
            revision=args.revision,
            hf_token=args.hf_token,
            ms_token=args.ms_token,
        )
    )

    repo_download_p = repo_sub.add_parser("download", help="从仓库下载文件")
    repo_download_p.add_argument("api_type", choices=REPO_API_TYPE_LIST, help="仓库 API 类型")
    repo_download_p.add_argument("repo_id", type=str, help="仓库 ID")
    repo_download_p.add_argument("local_dir", type=normalized_filepath, help="本地下载目录")
    _add_repo_type_argument(repo_download_p)
    _add_repo_revision_argument(repo_download_p)
    repo_download_p.add_argument("--folder", type=str, default=None, help="只下载指定路径前缀或文件")
    repo_download_p.add_argument("--threads", type=int, default=8, dest="num_threads", help="下载线程数")
    _add_repo_auth_arguments(repo_download_p)
    repo_download_p.set_defaults(
        func=lambda args: repo_download_cli(
            api_type=args.api_type,
            repo_id=args.repo_id,
            local_dir=args.local_dir,
            repo_type=args.repo_type,
            folder=args.folder,
            num_threads=args.num_threads,
            revision=args.revision,
            hf_token=args.hf_token,
            ms_token=args.ms_token,
        )
    )

    repo_mirror_p = repo_sub.add_parser("mirror", help="镜像仓库文件")
    repo_mirror_p.add_argument("src_api_type", choices=REPO_API_TYPE_LIST, help="源仓库 API 类型")
    repo_mirror_p.add_argument("dst_api_type", choices=REPO_API_TYPE_LIST, help="目标仓库 API 类型")
    repo_mirror_p.add_argument("src_repo_id", type=str, help="源仓库 ID")
    repo_mirror_p.add_argument("dst_repo_id", type=str, help="目标仓库 ID")
    repo_mirror_p.add_argument("--src-repo-type", choices=REPO_TYPE_LIST, default="model", help="源仓库类型")
    repo_mirror_p.add_argument("--dst-repo-type", choices=REPO_TYPE_LIST, default="model", help="目标仓库类型")
    _add_repo_revision_argument(repo_mirror_p)
    repo_mirror_p.add_argument("--public", action="store_true", help="创建目标仓库时设为公开仓库")
    repo_mirror_p.add_argument("--threads", type=int, default=1, dest="num_threads", help="镜像线程数")
    repo_mirror_p.add_argument("--retry-times", type=int, default=app_config.RETRY_TIMES, help="单个文件镜像重试次数")
    repo_mirror_p.add_argument("--fast-download", action="store_true", dest="use_fast_download", help="使用内置 downloader 下载源文件")
    repo_mirror_p.add_argument("--download-tool", choices=DOWNLOAD_TOOL_TYPE_LIST, default="requests", help="启用 fast-download 时使用的下载工具")
    repo_mirror_p.add_argument("--download-split", type=int, default=5, help="启用 fast-download 时的分片数")
    repo_mirror_p.add_argument("--no-download-progress", action="store_false", dest="download_progress", default=True, help="禁用 fast-download 进度条")
    _add_repo_auth_arguments(repo_mirror_p)
    repo_mirror_p.set_defaults(
        func=lambda args: repo_mirror_cli(
            src_api_type=args.src_api_type,
            dst_api_type=args.dst_api_type,
            src_repo_id=args.src_repo_id,
            dst_repo_id=args.dst_repo_id,
            src_repo_type=args.src_repo_type,
            dst_repo_type=args.dst_repo_type,
            visibility=args.public,
            revision=args.revision,
            num_threads=args.num_threads,
            retry_times=args.retry_times,
            use_fast_download=args.use_fast_download,
            download_tool=args.download_tool,
            download_split=args.download_split,
            download_progress=args.download_progress,
            hf_token=args.hf_token,
            ms_token=args.ms_token,
        )
    )

    # download-file
    download_file_p = sd_webui_all_in_one_sub.add_parser("download-file", help="下载文件")
    download_file_p.add_argument("url", type=str, help="文件下载链接")
    download_file_p.add_argument("--path", type=normalized_filepath, default=None, help="文件下载路径, 默认为当前目录")
    download_file_p.add_argument("--save-name", type=str, default=None, help="文件保存名称")
    download_file_p.add_argument("--downloader", dest="tool", default=None, choices=DOWNLOAD_TOOL_TYPE_LIST, help="下载工具")
    download_file_p.add_argument("--no-progress", action="store_false", dest="progress", default=True, help="禁用下载进度条")
    download_file_p.add_argument("--split", type=int, default=DEFAULT_SPLIT, help="aria2 风格的单文件最大分割数")
    download_file_p.add_argument("--max-connection-per-server", type=int, default=DEFAULT_MAX_CONNECTION_PER_SERVER, help="aria2 风格的单服务器最大连接数")
    download_file_p.add_argument("--min-split-size", type=int, default=DEFAULT_MIN_SPLIT_SIZE, help="aria2 风格的最小切分大小, 单位为字节")
    download_file_p.add_argument("--piece-length", type=int, default=DEFAULT_PIECE_LENGTH, help="aria2 风格的 piece 大小, 单位为字节")
    download_file_p.add_argument("--allow-piece-length-change", action="store_true", default=False, help="piece-length 与控制文件不一致时转换已完成 bitfield")
    download_file_p.add_argument("--continue", action="store_true", dest="continue_download", default=False, help="没有匹配控制文件时从已有文件继续下载")
    download_file_p.add_argument("--max-tries", type=int, default=5, help="单个分片最大尝试次数")
    download_file_p.add_argument("--retry-wait", type=int, default=0, help="HTTP 503 重试前等待秒数")
    download_file_p.add_argument("--conditional-get", action="store_true", default=False, help="已有本地文件时发送 If-Modified-Since, 远端返回 304 时复用本地文件")
    download_file_p.add_argument("--no-remote-time", action="store_false", dest="remote_time", default=True, help="禁用按远端 Last-Modified 设置本地文件时间")
    download_file_p.set_defaults(
        func=lambda args: download_file_cli(
            url=args.url,
            path=args.path,
            save_name=args.save_name,
            progress=args.progress,
            split=args.split,
            max_connection_per_server=args.max_connection_per_server,
            min_split_size=args.min_split_size,
            piece_length=args.piece_length,
            allow_piece_length_change=args.allow_piece_length_change,
            continue_download=args.continue_download,
            max_tries=args.max_tries,
            retry_wait=args.retry_wait,
            conditional_get=args.conditional_get,
            remote_time=args.remote_time,
            tool=args.tool,
        )
    )

    archive_p = sd_webui_all_in_one_sub.add_parser("archive", help="压缩包解压和压缩")
    archive_sub = archive_p.add_subparsers(dest="archive_action", required=True)

    archive_extract_p = archive_sub.add_parser("extract", help="解压压缩包")
    archive_extract_p.add_argument("archive_path", type=normalized_filepath, help="压缩包路径")
    archive_extract_p.add_argument("--output", type=normalized_filepath, required=True, help="解压输出路径")
    archive_extract_p.add_argument("--no-progress", action="store_false", dest="progress", default=True, help="禁用解压进度条")
    archive_extract_p.set_defaults(
        func=lambda args: extract_archive_cli(
            archive_path=args.archive_path,
            output=args.output,
            progress=args.progress,
        )
    )

    archive_compress_p = archive_sub.add_parser("compress", help="创建压缩包")
    archive_compress_p.add_argument("sources", type=normalized_filepath, nargs="+", help="要压缩的文件或目录路径")
    archive_compress_p.add_argument("--output", type=normalized_filepath, required=True, help="压缩包保存路径，文件扩展名决定实际使用的压缩格式")
    archive_compress_p.add_argument("--no-progress", action="store_false", dest="progress", default=True, help="禁用压缩进度条")
    archive_compress_p.set_defaults(
        func=lambda args: compress_archive_cli(
            sources=args.sources,
            output=args.output,
            progress=args.progress,
        )
    )

    # start-tunnel
    start_tunnel_p = sd_webui_all_in_one_sub.add_parser("start-tunnel", help="启动内网穿透")
    start_tunnel_p.add_argument("port", type=int, help="要进行端口映射的端口")
    start_tunnel_p.add_argument("--workspace", type=normalized_filepath, default=SD_WEBUI_ALL_IN_ONE_LAUNCH_PATH, help="工作区路径（默认为当前目录）")
    start_tunnel_p.add_argument("--ngrok", action="store_true", help="启用 Ngrok 内网穿透")
    start_tunnel_p.add_argument("--ngrok-token", type=str, default=None, help="Ngrok 账号 Token, 可从 https://dashboard.ngrok.com/get-started/your-authtoken 获取")
    start_tunnel_p.add_argument("--cloudflare", action="store_true", help="启用 CloudFlare 内网穿透")
    start_tunnel_p.add_argument("--remote-moe", action="store_true", help="启用 remote.moe 内网穿透")
    start_tunnel_p.add_argument("--localhost-run", action="store_true", help="启用 localhost.run 内网穿透")
    start_tunnel_p.add_argument("--gradio", action="store_true", help="启用 Gradio 内网穿透")
    start_tunnel_p.add_argument("--pinggy-io", action="store_true", help="启用 pinggy.io 内网穿透")
    start_tunnel_p.add_argument("--zrok", action="store_true", help="启用 Zrok 内网穿透")
    start_tunnel_p.add_argument("--zrok-token", type=str, default=None, help="Zrok 账号 Token, 可从 https://netfoundry.io/docs/zrok/get-started/get-token 获取")
    start_tunnel_p.set_defaults(
        func=lambda args: start_tunnel(
            port=args.port,
            workspace=args.workspace,
            use_ngrok=args.ngrok,
            ngrok_token=args.ngrok_token,
            use_cloudflare=args.cloudflare,
            use_remote_moe=args.remote_moe,
            use_localhost_run=args.localhost_run,
            use_gradio=args.gradio,
            use_pinggy_io=args.pinggy_io,
            use_zrok=args.zrok,
            zrok_token=args.zrok_token,
        )
    )
