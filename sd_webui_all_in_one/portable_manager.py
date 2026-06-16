"""整合包资源列表生成工具"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from functools import cmp_to_key
from pathlib import Path
from typing import Literal, TypeAlias, TypedDict, get_args

from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.logger import get_logger
from sd_webui_all_in_one.custom_exceptions import AggregateError
from sd_webui_all_in_one.package_analyzer.ver_cmp import CommonVersionComparison
from sd_webui_all_in_one.repo_manager import (
    ApiType,
    RepoManager,
    RepoType,
)

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

PortableSourceType: TypeAlias = ApiType
"""整合包下载源类型"""

PortableChannelType: TypeAlias = Literal["stable", "nightly"]
"""整合包发行通道类型"""

PORTABLE_SOURCE_TYPE_LIST: list[PortableSourceType] = list(get_args(PortableSourceType))
"""整合包下载源类型列表"""

PORTABLE_CHANNEL_TYPE_LIST: list[PortableChannelType] = list(get_args(PortableChannelType))
"""整合包发行通道类型列表"""

DEFAULT_PORTABLE_PATH_IN_REPO = "portable"
"""默认整合包仓库目录"""

PORTABLE_NAME_PATTERN = r"""
    ^
    (?P<software>[\w_]+?)
    -
    (?P<signature>[a-z0-9]+)
    -
    (?:
        (?P<build_date>\d{8})
        -
        nightly
    |
        v
        (?P<version>[\d.]+)
    )
    \.
    (?P<extension>[a-z0-9]+(?:\.[a-z0-9]+)?)
    $
"""
"""整合包文件名解析正则"""

PORTABLE_NAME_REGEX = re.compile(PORTABLE_NAME_PATTERN, re.VERBOSE | re.IGNORECASE)
"""整合包文件名解析正则对象"""

PORTABLE_DISPLAY_NAMES = {
    "sd_webui": "Stable Diffusion WebUI",
    "sd_webui_forge": "Stable Diffusion WebUI Forge",
    "sd_webui_reforge": "Stable Diffusion WebUI reForge",
    "sd_webui_forge_classic": "Stable Diffusion WebUI Forge Classic",
    "sd_webui_forge_neo": "Stable Diffusion WebUI Forge Neo",
    "sd_next": "SD Next",
    "comfyui": "ComfyUI",
    "comfyui_rocm": "ComfyUI (ROCm)",
    "comfyui_xpu": "ComfyUI (XPU)",
    "fooocus": "Fooocus",
    "invokeai": "InvokeAI",
    "sd_trainer": "SD Trainer",
    "sd_trainer_next": "SD Trainer Next",
    "kohya_gui": "Kohya GUI",
    "sd_scripts": "SD Scripts",
    "musubi_tuner": "Musubi Tuner",
    "qwen_tts_webui": "Qwen TTS WebUI",
}
"""整合包展示名称"""

PORTABLE_DESCRIPTIONS = {
    "sd_webui": "上手简单，操作方便，适合入门使用。",
    "sd_webui_forge": "基于 Stable Diffusion WebUI，有更强的显存优化，多了 FLUX 模型支持。",
    "sd_webui_reforge": "基于旧版 Stable Diffusion WebUI Forge 开发，插件兼容性比 Stable Diffusion WebUI Forge 好一点。",
    "sd_webui_forge_classic": "Stable Diffusion WebUI Forge 的经典版本整合包。",
    "sd_webui_forge_neo": "基于旧版 Stable Diffusion WebUI Forge 开发，精简了无用组件，更轻量。",
    "sd_next": "基于 Stable Diffusion WebUI 开发，支持的模型种类多，就是比较臃肿。",
    "comfyui": "流程高度自定义，可玩性高，显存优化强，支持的模型丰富。",
    "comfyui_rocm": "ComfyUI 的 AMD 显卡整合包，流程高度自定义，可玩性高。",
    "comfyui_xpu": "ComfyUI 的 Intel 显卡整合包，流程高度自定义，可玩性高。",
    "fooocus": "化繁为简，更专注于提示词书写。",
    "invokeai": "拥有最强大的画布系统，更适合作为辅助绘画工具。",
    "sd_trainer": "训练模型如此简单。",
    "sd_trainer_next": "训练模型如此简单。基于 SD Trainer 分支，并且新增了 Anima 模型的支持。",
    "kohya_gui": "支持训练更多种类的模型，不过操作麻烦一点。",
    "sd_scripts": "支持训练 SD1.5，SDXL，FLUX，ControlNet 等多种模型，并且是 SD-Trainer 和 Kohya GUI 的训练核心，不过操作比较麻烦。",
    "musubi_tuner": "支持训练 Hunyuan，Wan 等视频生成模型。",
    "qwen_tts_webui": "支持使用 Qwen3 TTS 生成语音。",
}
"""整合包描述"""


class PortableFilenameInfo(TypedDict):
    """解析后的整合包文件名信息"""

    software: str
    """整合包软件标识"""

    signature: str
    """整合包签名标识"""

    channel: PortableChannelType
    """整合包发行通道"""

    build_date: str | None
    """Nightly 构建日期"""

    version: str | None
    """Stable 版本号"""

    extension: str
    """文件扩展名"""


class PortableFileResource(TypedDict):
    """整合包文件资源"""

    filename: str
    """文件名"""

    path: str
    """仓库内文件路径"""

    url: str
    """文件下载地址"""

    signature: str
    """整合包签名标识"""

    channel: PortableChannelType
    """整合包发行通道"""

    version: str | None
    """Stable 版本号"""

    build_date: str | None
    """Nightly 构建日期"""

    extension: str
    """文件扩展名"""


class PortableSoftwareResource(TypedDict):
    """单个软件的整合包资源"""

    display_name: str
    """展示名称"""

    description: str
    """整合包描述"""

    stable: list[PortableFileResource]
    """Stable 资源列表"""

    nightly: list[PortableFileResource]
    """Nightly 资源列表"""


PortableSourceResources: TypeAlias = dict[str, PortableSoftwareResource]
"""单个下载源的整合包资源"""


class PortableListData(TypedDict):
    """整合包资源列表数据"""

    update_time: str
    """更新时间"""

    resources: dict[str, PortableSourceResources]
    """按下载源分组的整合包资源"""


class PortableRepoSourceConfig(TypedDict):
    """整合包仓库下载源配置"""

    source: PortableSourceType
    """下载源类型"""

    repo_id: str
    """仓库 ID"""

    repo_type: RepoType
    """仓库类型"""


PortableUploadTargetConfig: TypeAlias = PortableRepoSourceConfig
"""整合包上传目标配置"""


def utc_update_time() -> str:
    """获取 UTC ISO 格式更新时间

    Returns:
        str: UTC ISO 格式时间字符串
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_portable_filename(filename: str) -> PortableFilenameInfo:
    """解析整合包文件名

    Args:
        filename (str):
            整合包文件名

    Returns:
        PortableFilenameInfo: 解析后的整合包文件名信息

    Raises:
        ValueError: 文件名不符合整合包命名规则时抛出
    """
    match = PORTABLE_NAME_REGEX.match(filename)
    if match is None:
        raise ValueError(f"整合包文件名不符合规范: {filename}")

    groups = match.groupdict()
    build_date = groups.get("build_date")
    version = groups.get("version")
    channel: PortableChannelType = "nightly" if build_date is not None else "stable"
    return {
        "software": groups["software"],
        "signature": groups["signature"],
        "channel": channel,
        "build_date": build_date,
        "version": version,
        "extension": groups["extension"].lower(),
    }


def build_portable_file_resource(
    path: str,
    url: str,
) -> tuple[str, PortableFileResource]:
    """构建整合包文件资源

    Args:
        path (str):
            仓库内文件路径
        url (str):
            文件下载地址

    Returns:
        tuple[str, PortableFileResource]: 软件标识和文件资源

    Raises:
        ValueError: 文件名不符合整合包命名规则时抛出
    """
    filename = Path(path).name
    info = parse_portable_filename(filename)
    return info["software"], {
        "filename": filename,
        "path": path,
        "url": url,
        "signature": info["signature"],
        "channel": info["channel"],
        "version": info["version"],
        "build_date": info["build_date"],
        "extension": info["extension"],
    }


def normalize_portable_path_in_repo(
    path_in_repo: str | None = DEFAULT_PORTABLE_PATH_IN_REPO,
) -> str:
    """规范化整合包仓库目录

    Args:
        path_in_repo (str | None):
            仓库中的整合包目录, 为空字符串时不限制目录

    Returns:
        str: 规范化后的仓库目录

    Raises:
        ValueError: 路径包含父目录引用时抛出
    """
    if path_in_repo is None:
        return ""

    parts = []
    for part in path_in_repo.replace("\\", "/").strip("/").split("/"):
        if part in ["", "."]:
            continue
        if part == "..":
            raise ValueError("整合包仓库目录不能包含 '..'")
        parts.append(part)
    return "/".join(parts)


def filter_portable_paths(
    paths: list[str],
    path_in_repo: str | None = DEFAULT_PORTABLE_PATH_IN_REPO,
) -> list[str]:
    """筛选有效整合包路径

    Args:
        paths (list[str]):
            仓库文件路径列表
        path_in_repo (str | None):
            仓库中的整合包目录, 为空字符串时不限制目录

    Returns:
        list[str]: 有效整合包路径列表
    """
    normalized_path_in_repo = normalize_portable_path_in_repo(path_in_repo)
    path_prefix = f"{normalized_path_in_repo}/" if normalized_path_in_repo else ""
    portable_paths = []
    for path in paths:
        if path_prefix and not path.startswith(path_prefix):
            continue
        try:
            parse_portable_filename(Path(path).name)
        except ValueError as e:
            logger.warning("%s", e)
            continue
        portable_paths.append(path)
    return portable_paths


def collect_portable_files_from_repo(
    manager: RepoManager,
    source: PortableSourceType,
    repo_id: str,
    repo_type: RepoType = "model",
    revision: str | None = None,
    path_in_repo: str | None = DEFAULT_PORTABLE_PATH_IN_REPO,
) -> list[PortableFileResource]:
    """从仓库收集整合包文件资源

    Args:
        manager (RepoManager):
            仓库管理器
        source (PortableSourceType):
            下载源类型
        repo_id (str):
            仓库 ID
        repo_type (RepoType):
            仓库类型
        revision (str | None):
            仓库分支、标签或提交哈希
        path_in_repo (str | None):
            仓库中的整合包目录, 为空字符串时不限制目录

    Returns:
        list[PortableFileResource]: 整合包文件资源列表
    """
    repo_files = manager.get_repo_file(
        api_type=source,
        repo_id=repo_id,
        repo_type=repo_type,
        revision=revision,
    )
    portable_files = []
    for path in filter_portable_paths(repo_files, path_in_repo=path_in_repo):
        url = manager.get_repo_file_download_url(
            api_type=source,
            repo_id=repo_id,
            file_path=path,
            repo_type=repo_type,
            revision=revision,
        )
        _, resource = build_portable_file_resource(path=path, url=url)
        portable_files.append(resource)
    return portable_files


def build_portable_source_resources(
    files: list[PortableFileResource],
) -> PortableSourceResources:
    """按软件标识构建下载源资源

    Args:
        files (list[PortableFileResource]):
            整合包文件资源列表

    Returns:
        PortableSourceResources: 按软件标识分组的下载源资源
    """
    grouped: PortableSourceResources = {}
    for file in files:
        software = parse_portable_filename(file["filename"])["software"]
        if software not in grouped:
            grouped[software] = {
                "display_name": PORTABLE_DISPLAY_NAMES.get(software, software),
                "description": PORTABLE_DESCRIPTIONS.get(software, ""),
                "stable": [],
                "nightly": [],
            }
        grouped[software][file["channel"]].append(file)

    result: PortableSourceResources = {}
    for software in sorted(grouped):
        resource = grouped[software]
        resource["stable"] = sort_portable_files(resource["stable"])
        resource["nightly"] = sort_portable_files(resource["nightly"])
        result[software] = resource
    return result


def sort_portable_files(
    files: list[PortableFileResource],
) -> list[PortableFileResource]:
    """排序整合包文件资源

    Args:
        files (list[PortableFileResource]):
            整合包文件资源列表

    Returns:
        list[PortableFileResource]: 排序后的整合包文件资源列表
    """

    def _compare(left: PortableFileResource, right: PortableFileResource) -> int:
        left_version = left["version"] if left["version"] is not None else left["build_date"] or "0"
        right_version = right["version"] if right["version"] is not None else right["build_date"] or "0"
        version_cmp = CommonVersionComparison(left_version).compare_versions(left_version, right_version)
        if version_cmp != 0:
            return -version_cmp
        if left["filename"] < right["filename"]:
            return -1
        if left["filename"] > right["filename"]:
            return 1
        return 0

    return sorted(files, key=cmp_to_key(_compare))


def build_portable_list_data(
    resources: dict[PortableSourceType, list[PortableFileResource]],
    update_time: str | None = None,
) -> PortableListData:
    """构建整合包资源列表数据

    Args:
        resources (dict[PortableSourceType, list[PortableFileResource]]):
            按下载源分组的文件资源
        update_time (str | None):
            更新时间, 未指定时使用当前 UTC 时间

    Returns:
        PortableListData: 整合包资源列表数据
    """
    output_resources: dict[str, PortableSourceResources] = {}
    for source in PORTABLE_SOURCE_TYPE_LIST:
        source_files = resources.get(source)
        if source_files is None:
            continue
        output_resources[source] = build_portable_source_resources(source_files)

    return {
        "update_time": update_time or utc_update_time(),
        "resources": output_resources,
    }


def build_portable_list_from_repositories(
    manager: RepoManager,
    sources: list[PortableRepoSourceConfig],
    revision: str | None = None,
    update_time: str | None = None,
    path_in_repo: str | None = DEFAULT_PORTABLE_PATH_IN_REPO,
) -> PortableListData:
    """从仓库构建整合包资源列表数据

    Args:
        manager (RepoManager):
            仓库管理器
        sources (list[PortableRepoSourceConfig]):
            仓库下载源配置列表
        revision (str | None):
            仓库分支、标签或提交哈希
        update_time (str | None):
            更新时间, 未指定时使用当前 UTC 时间
        path_in_repo (str | None):
            仓库中的整合包目录, 为空字符串时不限制目录

    Returns:
        PortableListData: 整合包资源列表数据

    Raises:
        ValueError: 下载源配置为空时抛出
    """
    if not sources:
        raise ValueError("至少需要配置一个整合包下载源")

    resources: dict[PortableSourceType, list[PortableFileResource]] = {}
    for source in sources:
        resources[source["source"]] = collect_portable_files_from_repo(
            manager=manager,
            source=source["source"],
            repo_id=source["repo_id"],
            repo_type=source["repo_type"],
            revision=revision,
            path_in_repo=path_in_repo,
        )
    return build_portable_list_data(resources=resources, update_time=update_time)


def _portable_target_name(target: PortableUploadTargetConfig) -> str:
    """获取上传目标的日志展示名称"""
    return f"{target['source']}:{target['repo_id']} ({target['repo_type']})"


def upload_portable_package_to_repositories(
    manager: RepoManager,
    upload_path: Path,
    targets: list[PortableUploadTargetConfig],
    revision: str | None = None,
    path_in_repo: str | None = None,
    visibility: bool = False,
    num_threads: int = 1,
    target_workers: int | None = None,
) -> None:
    """上传整合包目录到多个 HuggingFace / ModelScope 仓库

    Args:
        manager (RepoManager):
            仓库管理器
        upload_path (Path):
            要上传的本地目录
        targets (list[PortableUploadTargetConfig]):
            上传目标配置列表
        revision (str | None):
            上传目标分支、标签或提交哈希
        path_in_repo (str | None):
            仓库中的上传路径前缀, 为`None`时上传到仓库根目录
        visibility (bool):
            创建仓库时是否设为公开
        num_threads (int):
            单个目标仓库内部的上传线程数
        target_workers (int | None):
            上传目标之间的并发数, 未指定时按目标数量并发

    Raises:
        FileNotFoundError: 上传路径不是目录时抛出
        ValueError: 上传目标配置为空时抛出
        AggregateError: 任一上传目标最终失败时抛出
    """
    if not upload_path.is_dir():
        raise FileNotFoundError(f"整合包上传目录不存在: {upload_path}")
    if not targets:
        raise ValueError("至少需要配置一个整合包上传目标")

    upload_targets = list(targets)
    upload_threads = max(1, num_threads)
    max_workers = max(1, target_workers if target_workers is not None else len(upload_targets))
    errors: list[Exception] = []

    def _upload_target(target: PortableUploadTargetConfig) -> None:
        target_name = _portable_target_name(target)
        logger.info("开始上传整合包到 %s", target_name)
        manager.upload_files_to_repo(
            api_type=target["source"],
            repo_id=target["repo_id"],
            upload_path=upload_path,
            path_in_repo=path_in_repo,
            repo_type=target["repo_type"],
            visibility=visibility,
            num_threads=upload_threads,
            revision=revision,
        )
        logger.info("整合包上传到 %s 完成", target_name)

    def _record_error(target: PortableUploadTargetConfig, exc: Exception) -> None:
        target_name = _portable_target_name(target)
        logger.error("整合包上传到 %s 失败: %s", target_name, exc)
        target_error = RuntimeError(f"{target_name} 上传失败: {exc}")
        target_error.__cause__ = exc
        errors.append(target_error)

    if max_workers == 1:
        for target in upload_targets:
            try:
                _upload_target(target)
            except Exception as exc:
                _record_error(target, exc)
    else:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_target = {executor.submit(_upload_target, target): target for target in upload_targets}
            for future in as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    future.result()
                except Exception as exc:
                    _record_error(target, exc)

    if errors:
        raise AggregateError("上传整合包时发生错误", errors)


def save_portable_list(
    data: PortableListData,
    output: Path,
) -> None:
    """保存整合包资源列表数据

    Args:
        data (PortableListData):
            整合包资源列表数据
        output (Path):
            输出文件路径
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
