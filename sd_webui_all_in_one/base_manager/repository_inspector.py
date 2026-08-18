"""本地 Git 仓库信息读取工具"""

import configparser
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sd_webui_all_in_one import git_warpper
from sd_webui_all_in_one.config import LOGGER_COLOR, LOGGER_LEVEL, LOGGER_NAME
from sd_webui_all_in_one.logger import get_logger

logger = get_logger(
    name=LOGGER_NAME,
    level=LOGGER_LEVEL,
    color=LOGGER_COLOR,
)


@dataclass(slots=True)
class RepositoryState:
    """
    Git 仓库状态

    Attributes:
        path (Path):
            仓库路径
        is_git_repo (bool):
            是否为 Git 仓库
        name (str):
            仓库名称
        url (str | None):
            当前远程地址
        branch (str | None):
            当前分支
        commit (str | None):
            当前提交 ID
        commit_date (str | None):
            当前提交时间
        message (str | None):
            当前提交信息
        error (str | None):
            仓库探测错误信息
    """

    path: Path
    is_git_repo: bool
    name: str
    url: str | None = None
    branch: str | None = None
    commit: str | None = None
    commit_date: str | None = None
    message: str | None = None
    error: str | None = None


def run_git_output(path: Path, *args: str) -> str:
    """
    执行 Git 命令并返回输出

    Args:
        path (Path):
            Git 仓库路径
        *args (str):
            Git 命令参数

    Returns:
        str: 命令输出
    """
    logger.debug("执行 Git 命令: '%s' %s", path, " ".join(args))
    output = git_warpper.run_git(*args, path=path, live=False)
    if output is None:
        return ""
    return output.strip()


def _resolve_git_dir(path: Path) -> Path | None:
    """
    解析仓库的 .git 目录

    Args:
        path (Path):
            仓库路径

    Returns:
        Path | None: .git 目录路径, 无法解析时返回 None
    """
    git_path = path / ".git"
    if git_path.is_dir():
        return git_path
    if not git_path.is_file():
        return None

    try:
        content = git_path.read_text(encoding="utf-8").strip()
    except OSError:
        logger.error("读取 .git 文件失败: '%s'", git_path)
        return None
    if not content.startswith("gitdir:"):
        logger.warning(".git 文件内容未指向 gitdir: '%s'", content)
        return None

    git_dir = Path(content.split(":", 1)[1].strip())
    if not git_dir.is_absolute():
        git_dir = path / git_dir
    return git_dir if git_dir.exists() else None


def _read_text(path: Path) -> str | None:
    """
    安全读取文本文件

    Args:
        path (Path):
            文本文件路径

    Returns:
        str | None: 文本内容, 读取失败时返回 None
    """
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        logger.debug("读取文本文件失败: '%s'", path)
        return None


def _resolve_common_git_dir(git_dir: Path) -> Path:
    """
    解析 Git 公共目录

    Args:
        git_dir (Path):
            .git 目录路径

    Returns:
        Path: Git 公共目录路径
    """
    common_dir_file = git_dir / "commondir"
    if not common_dir_file.is_file():
        return git_dir

    try:
        common_dir = Path(common_dir_file.read_text(encoding="utf-8").strip())
    except OSError:
        logger.error("读取 commondir 文件失败: '%s'", common_dir_file)
        return git_dir
    if not common_dir.is_absolute():
        common_dir = git_dir / common_dir
    logger.debug("解析到 Git 公共目录: '%s'", common_dir)
    return common_dir


def _is_full_commit_hash(value: str | None) -> bool:
    """
    判断字符串是否为完整 Git 提交哈希

    Args:
        value (str | None):
            待检查字符串

    Returns:
        bool: 字符串是否为 40 位十六进制提交哈希
    """
    if value is None or len(value) != 40:
        return False
    return all(char in "0123456789abcdefABCDEF" for char in value)


def _read_repository_branch(git_dir: Path) -> str | None:
    """
    从 HEAD 文件读取当前分支

    Args:
        git_dir (Path):
            .git 目录路径

    Returns:
        str | None: 当前分支, detached HEAD 或读取失败时返回 None
    """
    head = _read_text(git_dir / "HEAD")
    if head is None:
        return None
    ref_prefix = "ref: refs/heads/"
    if head.startswith(ref_prefix):
        branch = head.removeprefix(ref_prefix)
        logger.debug("从 HEAD 解析到当前分支: '%s'", branch)
        return branch
    logger.debug("HEAD 为 detached 状态: '%s'", head)
    return None


def _read_repository_remote_url(git_dir: Path, branch: str | None) -> str | None:
    """
    从 Git 配置读取当前分支远程地址

    Args:
        git_dir (Path):
            .git 目录路径
        branch (str | None):
            当前分支

    Returns:
        str | None: 远程地址
    """
    common_git_dir = _resolve_common_git_dir(git_dir)
    config_path = common_git_dir / "config"
    if not config_path.is_file():
        logger.debug("未找到 Git config 文件: '%s'", config_path)
        return None

    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(config_path, encoding="utf-8")
    except configparser.Error:
        logger.error("解析 Git config 失败: '%s'", config_path)
        return None

    remote_name = "origin"
    if branch is not None:
        branch_section = f'branch "{branch}"'
        remote_name = parser.get(branch_section, "remote", fallback=remote_name)

    remote_section = f'remote "{remote_name}"'
    remote_url = parser.get(remote_section, "url", fallback=None)
    if remote_url is not None:
        return remote_url
    return parser.get('remote "origin"', "url", fallback=None)


def _read_ref_from_packed_refs(git_dir: Path, ref: str) -> str | None:
    """
    从 packed-refs 读取引用对应的提交

    Args:
        git_dir (Path):
            Git 目录路径
        ref (str):
            Git 引用名称

    Returns:
        str | None: 提交哈希, 读取失败时返回 None
    """
    packed_refs = git_dir / "packed-refs"
    if not packed_refs.is_file():
        return None

    try:
        lines = packed_refs.read_text(encoding="utf-8").splitlines()
    except OSError:
        logger.error("读取 packed-refs 失败: '%s'", packed_refs)
        return None

    for line in lines:
        line = line.strip()
        if not line or line.startswith(("#", "^")):
            continue
        commit, sep, packed_ref = line.partition(" ")
        if sep and packed_ref == ref and _is_full_commit_hash(commit):
            logger.debug("从 packed-refs 找到引用 '%s' 对应提交: '%s'", ref, commit)
            return commit
    return None


def _read_ref_commit(git_dir: Path, ref: str) -> str | None:
    """
    从 loose refs 或 packed-refs 读取引用对应的提交

    Args:
        git_dir (Path):
            Git 目录路径
        ref (str):
            Git 引用名称

    Returns:
        str | None: 提交哈希, 读取失败时返回 None
    """
    common_git_dir = _resolve_common_git_dir(git_dir)
    search_dirs = [git_dir]
    if common_git_dir != git_dir:
        search_dirs.append(common_git_dir)
        logger.debug("引用搜索包含公共目录: '%s'", common_git_dir)

    for base_dir in search_dirs:
        commit = _read_text(base_dir / ref)
        if _is_full_commit_hash(commit):
            logger.debug("从 loose ref 找到引用 '%s' 对应提交: '%s'", ref, commit)
            return commit

    for base_dir in search_dirs:
        commit = _read_ref_from_packed_refs(base_dir, ref)
        if commit is not None:
            return commit
    logger.debug("未找到引用 '%s' 对应的提交", ref)
    return None


def _read_head_commit(git_dir: Path) -> str | None:
    """
    从 HEAD 文件读取当前提交哈希

    Args:
        git_dir (Path):
            Git 目录路径

    Returns:
        str | None: 当前提交哈希, 读取失败时返回 None
    """
    head = _read_text(git_dir / "HEAD")
    if head is None:
        return None
    if head.startswith("ref:"):
        commit = _read_ref_commit(git_dir, head.split(":", 1)[1].strip())
        if commit is not None:
            logger.debug("HEAD 引用的提交: '%s'", commit)
        return commit
    if _is_full_commit_hash(head):
        logger.debug("HEAD 为 detached 提交: '%s'", head)
        return head
    return None


def _format_git_commit_time(timestamp: str, offset: str) -> str | None:
    """
    将 Git commit object 时间戳格式化为 git show %ci 形式

    Args:
        timestamp (str):
            Unix 时间戳
        offset (str):
            时区偏移, 如 +0800

    Returns:
        str | None: 格式化时间
    """
    if len(offset) != 5 or offset[0] not in "+-" or not offset[1:].isdigit():
        logger.debug("无效时区偏移: '%s'", offset)
        return None
    try:
        seconds = int(timestamp)
    except ValueError:
        logger.debug("无效时间戳: '%s'", timestamp)
        return None

    sign = 1 if offset[0] == "+" else -1
    hours = int(offset[1:3])
    minutes = int(offset[3:5])
    tzinfo = timezone(sign * timedelta(hours=hours, minutes=minutes))
    return datetime.fromtimestamp(seconds, tz=tzinfo).strftime("%Y-%m-%d %H:%M:%S %z")


def _parse_loose_commit_object(content: bytes) -> tuple[str | None, str | None]:
    """
    解析 loose commit object 中的提交时间和提交信息

    Args:
        content (bytes):
            解压后的 Git object 内容

    Returns:
        tuple[str | None, str | None]: 提交时间和提交信息
    """
    header, sep, body = content.partition(b"\x00")
    if sep == b"" or not header.startswith(b"commit "):
        logger.debug("非 commit 类型的 loose object")
        return None, None

    text = body.decode("utf-8", errors="replace")
    metadata, _sep, raw_message = text.partition("\n\n")
    commit_date: str | None = None
    for line in metadata.splitlines():
        if not line.startswith("committer "):
            continue
        parts = line.rsplit(" ", 2)
        if len(parts) == 3:
            commit_date = _format_git_commit_time(parts[1], parts[2])
        break

    message = raw_message.splitlines()[0] if raw_message else None
    logger.debug("解析 commit object 完成: 提交时间 '%s', 提交信息 '%s'", commit_date, message)
    return commit_date, message


def _read_loose_commit_details(git_dir: Path, commit: str) -> tuple[str | None, str | None]:
    """
    从 loose object 读取提交时间和提交信息

    Args:
        git_dir (Path):
            Git 目录路径
        commit (str):
            提交哈希

    Returns:
        tuple[str | None, str | None]: 提交时间和提交信息
    """
    common_git_dir = _resolve_common_git_dir(git_dir)
    object_path = common_git_dir / "objects" / commit[:2] / commit[2:]
    try:
        content = zlib.decompress(object_path.read_bytes())
    except (OSError, zlib.error):
        logger.debug("读取或解压 loose object 失败: '%s'", object_path)
        return None, None
    return _parse_loose_commit_object(content)


def _read_repository_head_from_git(path: Path) -> tuple[str | None, str | None, str | None] | None:
    """
    使用 Git 命令读取当前提交信息

    Args:
        path (Path):
            仓库路径

    Returns:
        tuple[str | None, str | None, str | None] | None: 提交 ID、提交时间和提交信息, 读取失败时返回 None
    """
    try:
        output = run_git_output(path, "show", "-s", "--format=%H%x1f%ci%x1f%s", "HEAD")
    except Exception as exc:
        logger.error("执行 git show 读取 HEAD 失败: '%s'", exc)
        return None

    parts = output.split("\x1f", 2)
    if len(parts) == 3:
        commit, commit_date, message = parts
        logger.debug("git show 解析 HEAD 成功: 提交 '%s', 时间 '%s'", commit or None, commit_date or None)
        return commit or None, commit_date or None, message or None
    logger.debug("git show 输出格式不符合预期: '%s'", output)
    return None


def _read_repository_head_from_git_dir(git_dir: Path) -> tuple[str | None, str | None, str | None]:
    """
    从 Git 目录读取当前提交信息

    Args:
        git_dir (Path):
            Git 目录路径

    Returns:
        tuple[str | None, str | None, str | None]: 提交 ID、提交时间和提交信息
    """
    commit = _read_head_commit(git_dir)
    if commit is None:
        logger.debug("从 Git 目录未解析到当前提交")
        return None, None, None
    commit_date, message = _read_loose_commit_details(git_dir, commit)
    logger.debug("从 Git 目录解析 HEAD 完成: 提交 '%s', 时间 '%s'", commit, commit_date)
    return commit, commit_date, message


def inspect_repository(path: Path) -> RepositoryState:
    """
    读取仓库状态

    非 Git 目录不会抛出未处理异常, 而是通过 RepositoryState.error 返回错误信息。

    Args:
        path (Path):
            仓库路径

    Returns:
        RepositoryState: 仓库状态
    """
    path = Path(path)
    state = RepositoryState(path=path, is_git_repo=False, name=path.name)
    logger.info("开始检查仓库: '%s'", path)
    if not path.exists():
        state.error = "路径不存在"
        logger.warning("仓库路径不存在: '%s'", path)
        return state

    git_dir = _resolve_git_dir(path)
    if git_dir is None:
        state.error = "非 Git 仓库"
        logger.warning("非 Git 仓库: '%s'", path)
        return state

    state.is_git_repo = True
    state.branch = _read_repository_branch(git_dir)
    state.url = _read_repository_remote_url(git_dir, state.branch)
    head_info = _read_repository_head_from_git(path)
    if head_info is None:
        logger.warning("git show 读取 HEAD 失败, 回退到本地 Git 目录解析: '%s'", path)
        head_info = _read_repository_head_from_git_dir(git_dir)
    state.commit, state.commit_date, state.message = head_info
    logger.info(
        "仓库检查完成: '%s', 分支 '%s', 提交 '%s', 远程地址 '%s'",
        path,
        state.branch,
        state.commit,
        state.url,
    )
    return state
