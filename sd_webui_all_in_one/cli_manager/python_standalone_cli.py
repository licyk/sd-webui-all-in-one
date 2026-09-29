"""python-build-standalone 资源管理命令行"""

import argparse
import os
import sys
from pathlib import Path
from typing import cast

from sd_webui_all_in_one.archive_manager import SUPPORTED_CREATE_ARCHIVE_FORMAT
from sd_webui_all_in_one.cli_manager.argparse_helpers import add_subparsers_with_help
from sd_webui_all_in_one.config import (
    LOGGER_COLOR,
    LOGGER_LEVEL,
    LOGGER_NAME,
)
from sd_webui_all_in_one.downloader.types import DOWNLOAD_TOOL_TYPE_LIST, DownloadToolType
from sd_webui_all_in_one.logger import get_logger, silence_logger_output
from sd_webui_all_in_one.python_standalone import (
    DEFAULT_ARCHIVE_FORMAT,
    DEFAULT_GITHUB_API_URL,
    DEFAULT_HF_REPO_ID,
    DEFAULT_MS_REPO_ID,
    DEFAULT_PATH_IN_REPO,
    DEFAULT_PLATFORMS,
    DEFAULT_SOURCE_REPO,
    DEFAULT_VARIANT,
    DEFAULT_VERSIONS,
    RepoTarget,
    SyncConfig,
    build_resource_list_data,
    build_sync_report,
    collect_resources,
    create_sync_plan,
    filter_resources,
    list_releases,
    render_resources_markdown,
    render_resources_table,
    render_sync_plan,
    render_sync_report_markdown,
    run_sync,
    sync_exit_code,
)
from sd_webui_all_in_one.python_standalone.resources import render_json, render_table
from sd_webui_all_in_one.repo_manager import RepoManager, RepoType
from sd_webui_all_in_one.utils import normalized_filepath

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)

REPO_TYPE_LIST = ["model", "dataset", "space"]
"""支持的仓库类型"""


def split_list(
    value: str,
) -> list[str]:
    """把逗号分隔的参数拆分为列表

    Args:
        value (str): 逗号分隔的参数
    Returns:
        list[str]: 列表
    """
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_platform_map(
    values: list[str] | None,
) -> dict[str, str]:
    """解析自定义平台映射, 并与默认平台映射合并

    Args:
        values (list[str] | None): 形如 <系统>/<架构>=<三元组> 的映射列表
    Returns:
        dict[str, str]: 平台到构建目标三元组的映射
    Raises:
        ValueError: 映射格式不正确时
    """
    mapping = dict(DEFAULT_PLATFORMS)
    for value in values or []:
        platform, sep, triple = value.partition("=")
        if not sep or not platform.strip() or not triple.strip():
            raise ValueError(f"平台映射格式应为 <系统>/<架构>=<三元组>: {value}")
        mapping[platform.strip()] = triple.strip()
    return mapping


def select_platforms(
    mapping: dict[str, str],
    platforms: list[str] | None,
) -> dict[str, str]:
    """从平台映射中选出要处理的平台

    Args:
        mapping (dict[str, str]): 平台到构建目标三元组的映射
        platforms (list[str] | None): 要处理的平台, 为 None 时处理全部
    Returns:
        dict[str, str]: 选中的平台映射
    Raises:
        ValueError: 平台未知时
    """
    if platforms is None:
        return mapping
    unknown = [p for p in platforms if p not in mapping]
    if unknown:
        raise ValueError(f"未知的平台: {', '.join(unknown)}, 可选: {', '.join(mapping)}; 其他平台可通过 --platform-map 添加")
    return {p: mapping[p] for p in platforms}


def build_repo_targets(
    hf_repo_id: str | None,
    hf_repo_type: str,
    ms_repo_id: str | None,
    ms_repo_type: str,
) -> list[RepoTarget]:
    """根据命令行参数构建仓库列表, 仓库 ID 为空时不使用该下载源

    Args:
        hf_repo_id (str | None): HuggingFace 仓库 ID
        hf_repo_type (str): HuggingFace 仓库类型
        ms_repo_id (str | None): ModelScope 仓库 ID
        ms_repo_type (str): ModelScope 仓库类型
    Returns:
        list[RepoTarget]: 仓库列表
    """
    targets: list[RepoTarget] = []
    if hf_repo_id:
        targets.append(RepoTarget("huggingface", hf_repo_id, cast(RepoType, hf_repo_type)))
    if ms_repo_id:
        targets.append(RepoTarget("modelscope", ms_repo_id, cast(RepoType, ms_repo_type)))
    return targets


def create_repo_manager(
    hf_token: str | None = None,
    ms_token: str | None = None,
) -> RepoManager:
    """创建仓库管理器, 未传 Token 时回退到环境变量

    Args:
        hf_token (str | None): HuggingFace Token
        ms_token (str | None): ModelScope Token
    Returns:
        RepoManager: 仓库管理器
    """
    return RepoManager(
        hf_token=hf_token if hf_token is not None else os.environ.get("HF_TOKEN"),
        ms_token=ms_token if ms_token is not None else os.environ.get("MODELSCOPE_API_TOKEN"),
    )


def write_output(
    text: str,
    output: str | None,
) -> None:
    """输出文本到文件或标准输出

    Args:
        text (str): 文本
        output (str | None): 输出文件路径, 为 None 或 - 时输出到标准输出
    """
    if output is None or output == "-":
        print(text, flush=True)
        return
    path = normalized_filepath(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else f"{text}\n", encoding="utf-8")
    logger.info("已保存到: %s", path)


def silence_logs_for_stdout(
    output_format: str,
    output: str | None,
) -> None:
    """输出 JSON / Markdown 到标准输出时静默日志, 避免日志混入输出内容

    Args:
        output_format (str): 输出格式
        output (str | None): 输出文件路径
    """
    if output_format != "table" and (output is None or output == "-"):
        silence_logger_output()


def python_standalone_sync_cli(
    args: argparse.Namespace,
) -> None:
    """下载 python-build-standalone 构建的 Python, 重新打包并上传到仓库

    Args:
        args (argparse.Namespace): 命令行参数
    Raises:
        SystemExit: 有任务失败或被取消时
    """
    mapping = parse_platform_map(args.platform_map)
    targets = [] if args.no_upload else build_repo_targets(args.hf_repo_id, args.hf_repo_type, args.ms_repo_id, args.ms_repo_type)
    config = SyncConfig(
        targets=targets,
        release_tag=args.release_tag,
        source_repo=args.source_repo,
        github_api_url=args.github_api_url,
        github_token=args.github_token if args.github_token is not None else os.environ.get("GITHUB_TOKEN"),
        versions=args.versions,
        platforms=select_platforms(mapping, args.platforms),
        variant=args.variant,
        archive_format=args.archive_format,
        path_in_repo=args.path_in_repo,
        revision=args.revision,
        public=args.public,
        output_dir=args.output_dir or Path("python_dist"),
        temp_output=args.temp_output,
        work_dir=args.work_dir,
        keep_temp=args.keep_temp,
        force=args.force,
        workers=args.workers,
        upload_threads=args.upload_threads,
        download_tool=cast(DownloadToolType, args.download_tool),
        download_split=args.download_split,
        verify_hash=args.verify_hash,
        progress=args.progress if args.progress is not None else args.workers == 1 and sys.stdout.isatty(),
    )
    manager = create_repo_manager(args.hf_token, args.ms_token) if targets else None
    plan = create_sync_plan(config, manager)
    print(f"\n{render_sync_plan(plan)}\n", flush=True)
    if args.dry_run:
        logger.info("dry run 模式, 不执行任务")
        return

    results = run_sync(plan, config, manager, color=not args.no_color and LOGGER_COLOR)
    report = build_sync_report(plan, results, config)
    if args.report_markdown:
        write_output(render_sync_report_markdown(report), args.report_markdown)
    if args.report_json:
        write_output(render_json(report), args.report_json)
    code = sync_exit_code(results)
    if code != 0:
        raise SystemExit(code)


def python_standalone_list_cli(
    args: argparse.Namespace,
) -> None:
    """查询仓库中已上传的 Python 资源

    Args:
        args (argparse.Namespace): 命令行参数
    Raises:
        ValueError: 没有配置查询的仓库时
    """
    targets = build_repo_targets(args.hf_repo_id, args.hf_repo_type, args.ms_repo_id, args.ms_repo_type)
    if not targets:
        raise ValueError("至少需要配置 HuggingFace 或 ModelScope 中的一个仓库")
    silence_logs_for_stdout(args.output_format, args.output)
    manager = create_repo_manager(args.hf_token, args.ms_token)
    resources = collect_resources(manager, targets, args.path_in_repo, args.revision, parse_platform_map(args.platform_map))
    latest_only = not args.all
    resources = filter_resources(
        resources,
        versions=args.versions,
        platforms=args.platforms,
        variants=args.variants,
        archive_formats=args.archive_formats,
        build_date=args.build_date,
        latest_only=latest_only,
    )
    if args.output_format == "json":
        text = render_json(build_resource_list_data(resources, targets, latest_only))
    elif args.output_format == "markdown":
        text = render_resources_markdown(resources, title="Python 资源列表" + (" (最新)" if latest_only else ""))
    else:
        text = render_resources_table(resources)
    write_output(text, args.output)


def python_standalone_releases_cli(
    args: argparse.Namespace,
) -> None:
    """列出 python-build-standalone 最近的 Release

    Args:
        args (argparse.Namespace): 命令行参数
    """
    silence_logs_for_stdout(args.output_format, args.output)
    releases = list_releases(
        source_repo=args.source_repo,
        limit=args.limit,
        token=args.github_token if args.github_token is not None else os.environ.get("GITHUB_TOKEN"),
        api_url=args.github_api_url,
    )
    if args.output_format == "json":
        write_output(render_json(releases), args.output)
        return
    rows = [[str(r["tag"]), str(r["published_at"]), "是" if r["prerelease"] else "否", str(r["assets"])] for r in releases]
    write_output(render_table(["标签", "发布时间", "预发布", "文件数"], rows), args.output)


def _add_repo_arguments(
    parser: argparse.ArgumentParser,
    action: str,
) -> None:
    """添加仓库相关参数

    Args:
        parser (argparse.ArgumentParser): 参数解析器
        action (str): 仓库用途, 用于帮助信息
    """
    parser.add_argument("--hf-repo-id", type=str, default=DEFAULT_HF_REPO_ID, help=f"{action}的 HuggingFace 仓库 ID, 传入空字符串时不使用 (默认: {DEFAULT_HF_REPO_ID})")
    parser.add_argument("--hf-repo-type", choices=REPO_TYPE_LIST, default="model", help="HuggingFace 仓库类型 (默认: model)")
    parser.add_argument("--ms-repo-id", type=str, default=DEFAULT_MS_REPO_ID, help=f"{action}的 ModelScope 仓库 ID, 传入空字符串时不使用 (默认: {DEFAULT_MS_REPO_ID})")
    parser.add_argument("--ms-repo-type", choices=REPO_TYPE_LIST, default="model", help="ModelScope 仓库类型 (默认: model)")
    parser.add_argument("--no-hf", action="store_const", const="", dest="hf_repo_id", help="不使用 HuggingFace 仓库")
    parser.add_argument("--no-ms", action="store_const", const="", dest="ms_repo_id", help="不使用 ModelScope 仓库")
    parser.add_argument("--revision", type=str, default=None, help="仓库分支 (默认: 仓库默认分支)")
    parser.add_argument("--path-in-repo", type=str, default=DEFAULT_PATH_IN_REPO, help=f"仓库中的 Python 资源目录 (默认: {DEFAULT_PATH_IN_REPO})")
    parser.add_argument("--hf-token", type=str, default=None, help="HuggingFace Token, 默认读取 HF_TOKEN")
    parser.add_argument("--ms-token", type=str, default=None, help="ModelScope Token, 默认读取 MODELSCOPE_API_TOKEN")


def _add_github_arguments(
    parser: argparse.ArgumentParser,
) -> None:
    """添加 GitHub 相关参数

    Args:
        parser (argparse.ArgumentParser): 参数解析器
    """
    parser.add_argument("--source-repo", type=str, default=DEFAULT_SOURCE_REPO, help=f"python-build-standalone 发布仓库 (默认: {DEFAULT_SOURCE_REPO})")
    parser.add_argument("--github-api-url", type=str, default=DEFAULT_GITHUB_API_URL, help=f"GitHub API 地址 (默认: {DEFAULT_GITHUB_API_URL})")
    parser.add_argument("--github-token", type=str, default=None, help="GitHub Token, 默认读取 GITHUB_TOKEN")


def register_python_standalone(
    subparsers: "argparse._SubParsersAction",
) -> None:
    """注册 python-build-standalone 资源管理子命令

    Args:
        subparsers (argparse._SubParsersAction): 子命令行解析器
    """
    root_p = subparsers.add_parser("python-standalone", help="python-build-standalone 资源管理 (下载、打包、上传、查询)")
    root_sub = add_subparsers_with_help(root_p, dest="python_standalone_action")

    sync_p = root_sub.add_parser("sync", help="下载 Python, 重新打包并上传到仓库, 只处理仓库中缺失的部分")
    sync_p.add_argument("--release-tag", type=str, default="latest", help="python-build-standalone Release 标签 (默认: latest)")
    _add_github_arguments(sync_p)
    sync_p.add_argument("--versions", type=split_list, default=list(DEFAULT_VERSIONS), help=f"逗号分隔的 Python 主次版本号 (默认: {','.join(DEFAULT_VERSIONS)})")
    sync_p.add_argument("--platforms", type=split_list, default=None, help=f"逗号分隔的平台 (默认: 全部, 内置: {','.join(DEFAULT_PLATFORMS)})")
    sync_p.add_argument("--platform-map", action="append", default=None, metavar="OS/ARCH=TRIPLE", help="添加或覆盖平台到构建目标三元组的映射, 可重复使用")
    sync_p.add_argument("--variant", type=str, default=DEFAULT_VARIANT, help=f"构建变体, 如 install_only_stripped、freethreaded+pgo+lto-full (默认: {DEFAULT_VARIANT})")
    sync_p.add_argument("--archive-format", choices=SUPPORTED_CREATE_ARCHIVE_FORMAT, default=DEFAULT_ARCHIVE_FORMAT, help=f"重新打包的格式 (默认: {DEFAULT_ARCHIVE_FORMAT})")
    _add_repo_arguments(sync_p, "上传目标")
    sync_p.add_argument("--no-upload", action="store_true", help="只下载和打包, 不读取仓库状态也不上传")
    sync_p.add_argument("--public", action="store_true", help="仓库不存在需要创建时设为公开仓库")
    sync_p.add_argument("--force", action="store_true", help="忽略仓库状态, 强制重新下载、打包并上传全部任务")
    sync_p.add_argument("--dry-run", action="store_true", help="只显示将要执行的任务")
    sync_p.add_argument("--workers", type=int, default=4, help="同时执行的任务数 (默认: 4)")
    sync_p.add_argument("--upload-threads", type=int, default=1, help="单个仓库的上传线程数 (默认: 1)")
    sync_p.add_argument("--download-tool", choices=DOWNLOAD_TOOL_TYPE_LIST, default="requests", help="下载工具 (默认: requests)")
    sync_p.add_argument("--download-split", type=int, default=5, help="单个文件下载分片数 (默认: 5)")
    sync_p.add_argument("--no-verify-hash", action="store_false", dest="verify_hash", help="不校验下载文件的 SHA256")
    output_group = sync_p.add_mutually_exclusive_group()
    output_group.add_argument("--output-dir", type=normalized_filepath, default=None, help="打包结果保存目录, 目录结构与仓库相同 (默认: ./python_dist)")
    output_group.add_argument("--temp-output", action="store_true", help="打包结果只保存在临时目录中, 每个任务上传完成后删除; 需要至少一个上传目标")
    sync_p.add_argument("--work-dir", type=normalized_filepath, default=None, help="临时工作目录 (默认: 系统临时目录)")
    sync_p.add_argument("--keep-temp", action="store_true", help="保留临时工作目录中的文件")
    sync_p.add_argument("--progress", action=argparse.BooleanOptionalAction, default=None, help="是否显示进度条 (默认: 单任务并发且在终端中时显示)")
    sync_p.add_argument("--no-color", action="store_true", default="NO_COLOR" in os.environ, help="不为任务日志标签着色")
    sync_p.add_argument("--report-markdown", type=str, default=None, metavar="PATH", help="任务完成后输出 Markdown 报告到该文件, - 表示标准输出")
    sync_p.add_argument("--report-json", type=str, default=None, metavar="PATH", help="任务完成后输出 JSON 报告到该文件, - 表示标准输出")
    sync_p.set_defaults(func=python_standalone_sync_cli)

    list_p = root_sub.add_parser("list", help="查询仓库中已上传的 Python 资源, 默认只显示最新构建")
    _add_repo_arguments(list_p, "查询")
    list_p.add_argument("--all", action="store_true", help="显示全部构建, 不只显示最新构建")
    list_p.add_argument("--versions", type=split_list, default=None, help="逗号分隔的主次版本号或完整版本号")
    list_p.add_argument("--platforms", type=split_list, default=None, help="逗号分隔的平台 (如 linux/amd64) 或系统 (如 linux)")
    list_p.add_argument("--platform-map", action="append", default=None, metavar="OS/ARCH=TRIPLE", help="添加平台到构建目标三元组的映射, 用于解析自定义平台的文件名")
    list_p.add_argument("--variants", type=split_list, default=None, help="逗号分隔的构建变体")
    list_p.add_argument("--archive-formats", type=split_list, default=None, help="逗号分隔的压缩包格式, 如 .zip,.tar.gz")
    list_p.add_argument("--build-date", type=str, default=None, help="只显示该构建日期 (Release 标签) 的资源")
    list_p.add_argument("--format", dest="output_format", choices=["table", "markdown", "json"], default="table", help="输出格式 (默认: table)")
    list_p.add_argument("--output", type=str, default=None, metavar="PATH", help="输出到文件 (默认: 标准输出)")
    list_p.set_defaults(func=python_standalone_list_cli)

    releases_p = root_sub.add_parser("releases", help="列出 python-build-standalone 最近的 Release")
    _add_github_arguments(releases_p)
    releases_p.add_argument("--limit", type=int, default=10, help="显示数量 (默认: 10)")
    releases_p.add_argument("--format", dest="output_format", choices=["table", "json"], default="table", help="输出格式 (默认: table)")
    releases_p.add_argument("--output", type=str, default=None, metavar="PATH", help="输出到文件 (默认: 标准输出)")
    releases_p.set_defaults(func=python_standalone_releases_cli)
