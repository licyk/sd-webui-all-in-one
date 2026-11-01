"""本地 Git 仓库信息读取工具"""

import configparser
import subprocess
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


@dataclass(slots=True)
class RepositoryProbe:
    """
    Git 仓库工作区探测结果

    Attributes:
        path (Path):
            仓库路径
        is_git_repo (bool):
            是否为 Git 仓库
        commit (str | None):
            当前提交 ID, 无法读取或仓库尚无提交时为 None
        branch (str | None):
            当前分支, detached HEAD 或无法读取时为 None
        dirty (bool | None):
            是否存在未提交变更, 无法确认时为 None
    """

    path: Path
    is_git_repo: bool
    commit: str | None = None
    branch: str | None = None
    dirty: bool | None = None


@dataclass(slots=True)
class RepositoryTrackingState:
    """
    Git 仓库当前分支与上游分支的跟踪状态

    Attributes:
        commit (str | None):
            当前提交 ID, 仓库尚无提交时为 None
        branch (str | None):
            当前分支, detached HEAD 时为 None
        upstream (str | None):
            上游分支的短名称 (如 origin/main), 未配置时为 None
        upstream_exists (bool):
            上游引用在本地是否存在, 仅在存在时 ahead/behind 有效
        ahead (int):
            本地领先上游的提交数
        behind (int):
            本地落后上游的提交数
        dirty (bool):
            已跟踪文件是否存在未提交变更
    """

    commit: str | None = None
    branch: str | None = None
    upstream: str | None = None
    upstream_exists: bool = False
    ahead: int = 0
    behind: int = 0
    dirty: bool = False


@dataclass(slots=True)
class BranchUpstream:
    """
    Git 配置中当前分支的上游信息

    Attributes:
        remote (str):
            上游远程源名称, 为 "." 时上游是本地分支
        merge (str):
            上游分支的完整引用 (如 refs/heads/main)
        tracking_ref (str | None):
            按默认 fetch refspec 映射得到的远程跟踪引用 (如 refs/remotes/origin/main);
            远程源使用自定义 refspec 时为 None
    """

    remote: str
    merge: str
    tracking_ref: str | None = None


GIT_READ_TIMEOUT = 60.0
"""只读 Git 命令的超时时间 (秒), 避免单个卡住的 Git 进程无限期阻塞并行检查"""


def run_git_output(path: Path, *args: str, timeout: float | None = GIT_READ_TIMEOUT) -> str:
    """
    执行只读 Git 命令并返回输出

    Args:
        path (Path):
            Git 仓库路径
        *args (str):
            Git 命令参数
        timeout (float | None):
            命令超时时间 (秒), 为 None 时不限制

    Returns:
        str: 命令输出

    Raises:
        RuntimeError:
            Git 命令执行失败或超时时
    """
    logger.debug("执行 Git 命令: '%s' %s", path, " ".join(args))
    try:
        output = git_warpper.run_git(*args, path=path, live=False, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        logger.warning("Git 命令执行超时 (%s 秒): '%s' %s", timeout, path, " ".join(args))
        raise RuntimeError(f"在 '{path}' 中执行 git {' '.join(args)} 超时 ({timeout} 秒)") from e
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


def _load_git_config(git_dir: Path) -> configparser.ConfigParser | None:
    """
    解析仓库的 Git config 文件

    Args:
        git_dir (Path):
            .git 目录路径

    Returns:
        configparser.ConfigParser | None: 解析结果, 文件不存在或解析失败时返回 None
    """
    config_path = _resolve_common_git_dir(git_dir) / "config"
    if not config_path.is_file():
        logger.debug("未找到 Git config 文件: '%s'", config_path)
        return None

    parser = configparser.ConfigParser(interpolation=None, strict=False)
    try:
        parser.read(config_path, encoding="utf-8")
    except configparser.Error:
        logger.error("解析 Git config 失败: '%s'", config_path)
        return None
    return parser


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
    parser = _load_git_config(git_dir)
    if parser is None:
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


def _format_commit_subject(raw_message: str) -> str | None:
    """
    按 git show %s 的规则提取提交标题

    提交信息第一个空行之前的所有行 (跳过开头的空行) 去除行尾空白后以空格连接。

    Args:
        raw_message (str):
            提交信息原文

    Returns:
        str | None: 提交标题, 为空时返回 None
    """
    lines: list[str] = []
    for line in raw_message.splitlines():
        stripped = line.rstrip()
        if not stripped:
            if lines:
                break
            continue
        lines.append(stripped)
    return " ".join(lines) or None


def _parse_commit_body(body: bytes) -> tuple[str | None, str | None]:
    """
    解析 commit object 内容 (不含对象头) 中的提交时间和提交信息

    提交信息使用非 UTF-8 编码 (存在 ``encoding`` 头) 时不解析提交信息, 交由 Git 转码。

    Args:
        body (bytes):
            commit object 内容

    Returns:
        tuple[str | None, str | None]: 提交时间和提交信息
    """
    text = body.decode("utf-8", errors="replace")
    metadata, _sep, raw_message = text.partition("\n\n")
    commit_date: str | None = None
    encoding: str | None = None
    for line in metadata.splitlines():
        if line.startswith("committer ") and commit_date is None:
            parts = line.rsplit(" ", 2)
            if len(parts) == 3:
                commit_date = _format_git_commit_time(parts[1], parts[2])
        elif line.startswith("encoding "):
            encoding = line.removeprefix("encoding ").strip()

    if encoding is not None and encoding.replace("-", "").replace("_", "").lower() != "utf8":
        logger.debug("提交信息使用 '%s' 编码, 跳过解析提交信息", encoding)
        return commit_date, None
    message = _format_commit_subject(raw_message)
    logger.debug("解析 commit object 完成: 提交时间 '%s', 提交信息 '%s'", commit_date, message)
    return commit_date, message


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
    return _parse_commit_body(body)


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


_PACK_INDEX_V2_HEADER = b"\xfftOc\x00\x00\x00\x02"
"""pack index v2 文件头"""

_PACK_OBJECT_COMMIT = 1
"""pack 中 commit 对象的类型编号"""

_MAX_PACKED_COMMIT_SIZE = 1024 * 1024
"""从 pack 读取的 commit 对象大小上限 (字节), 超出时交由 Git 读取"""


def _find_pack_offset(index_path: Path, object_id: bytes) -> int | None:
    """
    在 pack index v2 文件中查找对象在 pack 文件中的偏移量

    Args:
        index_path (Path):
            ``.idx`` 文件路径
        object_id (bytes):
            20 字节的 SHA-1 对象 ID

    Returns:
        int | None: 对象偏移量, 未找到或格式不受支持时返回 None
    """
    with index_path.open("rb") as file:
        if file.read(8) != _PACK_INDEX_V2_HEADER:
            return None
        fanout = file.read(256 * 4)
        if len(fanout) != 256 * 4:
            return None
        first_byte = object_id[0]
        start = int.from_bytes(fanout[(first_byte - 1) * 4 : first_byte * 4], "big") if first_byte else 0
        end = int.from_bytes(fanout[first_byte * 4 : (first_byte + 1) * 4], "big")
        total = int.from_bytes(fanout[-4:], "big")
        if end <= start or end > total:
            return None

        names_offset = 8 + 256 * 4
        file.seek(names_offset + start * 20)
        names = file.read((end - start) * 20)
        low, high = 0, end - start
        while low < high:
            middle = (low + high) // 2
            name = names[middle * 20 : (middle + 1) * 20]
            if name < object_id:
                low = middle + 1
            elif name > object_id:
                high = middle
            else:
                break
        else:
            return None
        position = start + middle

        # 对象 ID 表之后依次为 CRC32 表 (4 字节/项)、32 位偏移表和 64 位偏移表
        offsets_offset = names_offset + total * 20 + total * 4
        file.seek(offsets_offset + position * 4)
        offset = int.from_bytes(file.read(4), "big")
        if offset & 0x80000000:
            file.seek(offsets_offset + total * 4 + (offset & 0x7FFFFFFF) * 8)
            offset = int.from_bytes(file.read(8), "big")
        return offset


def _read_pack_commit_body(pack_path: Path, offset: int) -> bytes | None:
    """
    读取 pack 文件中指定偏移量处的非 delta commit 对象内容

    Args:
        pack_path (Path):
            ``.pack`` 文件路径
        offset (int):
            对象偏移量

    Returns:
        bytes | None: commit 对象内容, 对象为 delta 或其他类型时返回 None
    """
    with pack_path.open("rb") as file:
        file.seek(offset)
        header = file.read(1)
        if not header:
            return None
        byte = header[0]
        object_type = (byte >> 4) & 0x7
        size = byte & 0x0F
        shift = 4
        while byte & 0x80:
            header = file.read(1)
            if not header:
                return None
            byte = header[0]
            size |= (byte & 0x7F) << shift
            shift += 7
        # delta 对象需要还原基础对象, 交由 Git 读取
        if object_type != _PACK_OBJECT_COMMIT or size > _MAX_PACKED_COMMIT_SIZE:
            return None

        decompressor = zlib.decompressobj()
        chunks: list[bytes] = []
        received = 0
        while received < size and not decompressor.eof:
            data = file.read(8192)
            if not data:
                break
            # zlib 流在对象末尾结束, 其后的数据会进入 unused_data, 不会混入输出
            chunk = decompressor.decompress(data)
            chunks.append(chunk)
            received += len(chunk)
    body = b"".join(chunks)
    return body if len(body) == size else None


def _read_packed_commit_details(git_dir: Path, commit: str) -> tuple[str | None, str | None]:
    """
    从 pack 文件读取提交时间和提交信息

    仅支持 SHA-1 仓库与 pack index v2 中以非 delta 形式存储的 commit 对象, 其他情况返回空结果交由 Git 读取。

    Args:
        git_dir (Path):
            Git 目录路径
        commit (str):
            提交哈希

    Returns:
        tuple[str | None, str | None]: 提交时间和提交信息
    """
    if len(commit) != 40:
        return None, None
    try:
        object_id = bytes.fromhex(commit)
    except ValueError:
        return None, None

    pack_dir = _resolve_common_git_dir(git_dir) / "objects" / "pack"
    try:
        index_paths = sorted(pack_dir.glob("pack-*.idx"))
    except OSError:
        return None, None
    for index_path in index_paths:
        try:
            offset = _find_pack_offset(index_path, object_id)
            if offset is None:
                continue
            body = _read_pack_commit_body(index_path.with_suffix(".pack"), offset)
        except (OSError, zlib.error) as exc:
            logger.debug("读取 pack 中的 commit 对象失败: '%s': %s", index_path, exc)
            return None, None
        if body is None:
            logger.debug("pack 中的 commit 对象为 delta 或格式不受支持: '%s'", index_path)
            return None, None
        return _parse_commit_body(body)
    logger.debug("pack 中未找到 commit 对象: '%s'", commit)
    return None, None


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
    except (RuntimeError, OSError) as exc:
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
    if commit_date is None and message is None:
        commit_date, message = _read_packed_commit_details(git_dir, commit)
    logger.debug("从 Git 目录解析 HEAD 完成: 提交 '%s', 时间 '%s'", commit, commit_date)
    return commit, commit_date, message


def inspect_repository(path: Path, details: bool = True) -> RepositoryState:
    """
    读取仓库状态

    非 Git 目录不会抛出未处理异常, 而是通过 RepositoryState.error 返回错误信息。

    Args:
        path (Path):
            仓库路径
        details (bool):
            是否读取提交时间和提交信息; 开启时优先从 loose object 或 pack 文件解析提交对象,
            无法解析 (如 delta 压缩的提交) 时才执行 git show; 关闭后优先直接解析 Git 目录, 不启动 Git 进程,
            此时提交时间和提交信息可能为 None

    Returns:
        RepositoryState: 仓库状态
    """
    path = Path(path)
    state = RepositoryState(path=path, is_git_repo=False, name=path.name)
    logger.debug("开始检查仓库: '%s'", path)
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
    head_info: tuple[str | None, str | None, str | None] | None = None
    if not details:
        commit = _read_head_commit(git_dir)
        if commit is not None:
            head_info = (commit, None, None)
    else:
        # 提交对象可直接从 loose object 或 pack 文件解析时无需启动 Git 进程
        parsed = _read_repository_head_from_git_dir(git_dir)
        if all(value is not None for value in parsed):
            head_info = parsed
    if head_info is None:
        head_info = _read_repository_head_from_git(path)
    if head_info is None:
        logger.warning("git show 读取 HEAD 失败, 回退到本地 Git 目录解析: '%s'", path)
        head_info = _read_repository_head_from_git_dir(git_dir)
    state.commit, state.commit_date, state.message = head_info
    logger.debug(
        "仓库检查完成: '%s', 分支 '%s', 提交 '%s', 远程地址 '%s'",
        path,
        state.branch,
        state.commit,
        state.url,
    )
    return state


def _parse_porcelain_v2_tracking(output: str) -> RepositoryTrackingState:
    """
    解析 git status --porcelain=v2 --branch 的输出, 包括上游分支和领先/落后提交数

    Args:
        output (str):
            Git 命令输出

    Returns:
        RepositoryTrackingState: 仓库跟踪状态
    """
    state = RepositoryTrackingState()
    for line in output.splitlines():
        if line.startswith("# branch.oid "):
            value = line.removeprefix("# branch.oid ").strip()
            state.commit = value if _is_full_commit_hash(value) else None
        elif line.startswith("# branch.head "):
            value = line.removeprefix("# branch.head ").strip()
            state.branch = None if value == "(detached)" else value
        elif line.startswith("# branch.upstream "):
            state.upstream = line.removeprefix("# branch.upstream ").strip() or None
        elif line.startswith("# branch.ab "):
            # 仅当上游引用在本地存在时 Git 才会输出 branch.ab, 格式为 "+<ahead> -<behind>"
            parts = line.removeprefix("# branch.ab ").split()
            if len(parts) == 2 and parts[0][1:].isdigit() and parts[1][1:].isdigit():
                state.ahead, state.behind = int(parts[0][1:]), int(parts[1][1:])
                state.upstream_exists = True
        elif line and not line.startswith("#"):
            # branch 头部信息总在变更条目之前输出, 发现变更即可停止解析
            state.dirty = True
            break
    return state


def _parse_porcelain_v2_status(output: str) -> tuple[str | None, str | None, bool]:
    """
    解析 git status --porcelain=v2 --branch 的输出

    Args:
        output (str):
            Git 命令输出

    Returns:
        tuple[str | None, str | None, bool]: 当前提交 ID、当前分支和是否存在未提交变更
    """
    state = _parse_porcelain_v2_tracking(output)
    return state.commit, state.branch, state.dirty


def probe_repository(path: Path) -> RepositoryProbe:
    """
    使用单次 Git 调用探测仓库的当前提交、分支和工作区变更状态

    只检查已跟踪文件的变更, 不扫描未跟踪文件: 恢复使用的 ``git reset --hard`` 不会删除未跟踪文件,
    与更新流程判断工作区是否有改动的方式一致, 同时避免在大型工作区中遍历未跟踪目录。

    Args:
        path (Path):
            仓库路径

    Returns:
        RepositoryProbe: 仓库工作区探测结果
    """
    path = Path(path)
    try:
        output = run_git_output(path, "status", "--porcelain=v2", "--branch", "--untracked-files=no")
    except (RuntimeError, OSError) as exc:
        logger.debug("git status 探测仓库失败, 回退到逐项检查: '%s': %s", path, exc)
        try:
            is_git_repo = git_warpper.is_git_repo(path)
        except OSError:
            is_git_repo = False
        if not is_git_repo:
            return RepositoryProbe(path=path, is_git_repo=False)
        # 仓库存在但无法读取工作区状态, dirty 保持 None 交由调用方按最保守方式处理
        git_dir = _resolve_git_dir(path)
        return RepositoryProbe(
            path=path,
            is_git_repo=True,
            commit=_read_head_commit(git_dir) if git_dir is not None else None,
            branch=_read_repository_branch(git_dir) if git_dir is not None else None,
        )

    commit, branch, dirty = _parse_porcelain_v2_status(output)
    logger.debug("仓库探测完成: '%s', 提交 '%s', 分支 '%s', dirty=%s", path, commit, branch, dirty)
    return RepositoryProbe(path=path, is_git_repo=True, commit=commit, branch=branch, dirty=dirty)


def repository_has_commit(path: Path, commit: str) -> bool:
    """
    检查仓库本地对象库中是否已存在指定提交

    Args:
        path (Path):
            仓库路径
        commit (str):
            提交 ID

    Returns:
        bool: 本地是否已存在该提交
    """
    try:
        run_git_output(path, "cat-file", "-e", f"{commit}^{{commit}}")
    except (RuntimeError, OSError):
        return False
    return True


def read_repository_tracking_state(path: Path) -> RepositoryTrackingState:
    """
    使用单次 Git 调用读取仓库的当前提交、分支、上游分支、领先/落后提交数和已跟踪文件变更状态

    不扫描未跟踪文件, 与更新流程判断工作区是否有改动的方式一致。

    Args:
        path (Path):
            仓库路径

    Returns:
        RepositoryTrackingState: 仓库跟踪状态

    Raises:
        RuntimeError:
            执行 git status 失败时
    """
    output = run_git_output(Path(path), "status", "--porcelain=v2", "--branch", "--untracked-files=no")
    state = _parse_porcelain_v2_tracking(output)
    logger.debug(
        "仓库跟踪状态: '%s', 分支 '%s', 上游 '%s', 领先 %s, 落后 %s, dirty=%s",
        path,
        state.branch,
        state.upstream,
        state.ahead,
        state.behind,
        state.dirty,
    )
    return state


def _maps_branch_to_tracking_ref(refspec: str, merge: str, tracking_ref: str) -> bool:
    """
    判断 fetch refspec 是否把上游分支映射到指定的远程跟踪引用

    Args:
        refspec (str):
            remote.<name>.fetch 配置值
        merge (str):
            上游分支的完整引用
        tracking_ref (str):
            期望的远程跟踪引用

    Returns:
        bool: refspec 是否产生该映射
    """
    src, sep, dst = refspec.strip().removeprefix("+").partition(":")
    if not sep:
        return False
    if src == merge and dst == tracking_ref:
        return True
    if src.endswith("/*") and dst.endswith("/*") and merge.startswith(src[:-1]):
        return dst[:-1] + merge.removeprefix(src[:-1]) == tracking_ref
    return False


def read_branch_upstream(path: Path, branch: str | None) -> BranchUpstream | None:
    """
    从 Git config 读取分支的上游配置, 不启动 Git 进程

    Args:
        path (Path):
            仓库路径
        branch (str | None):
            分支名称

    Returns:
        BranchUpstream | None: 上游配置, 分支未配置上游或无法解析配置时返回 None
    """
    if branch is None:
        return None
    git_dir = _resolve_git_dir(Path(path))
    parser = _load_git_config(git_dir) if git_dir is not None else None
    if parser is None:
        return None
    remote = parser.get(f'branch "{branch}"', "remote", fallback="").strip()
    merge = parser.get(f'branch "{branch}"', "merge", fallback="").strip()
    if not remote or not merge:
        return None
    upstream = BranchUpstream(remote=remote, merge=merge)
    if remote != "." and merge.startswith("refs/heads/"):
        expected = f"refs/remotes/{remote}/{merge.removeprefix('refs/heads/')}"
        refspec = parser.get(f'remote "{remote}"', "fetch", fallback="")
        if _maps_branch_to_tracking_ref(refspec, merge, expected):
            upstream.tracking_ref = expected
    return upstream


def read_ref_commit(path: Path, *refs: str) -> str | None:
    """
    依次从 loose refs 和 packed-refs 读取引用对应的提交, 不启动 Git 进程

    Args:
        path (Path):
            仓库路径
        *refs (str):
            候选完整引用名称, 按顺序尝试

    Returns:
        str | None: 第一个可解析引用对应的提交哈希, 均无法解析时返回 None
    """
    git_dir = _resolve_git_dir(Path(path))
    if git_dir is None:
        return None
    for ref in refs:
        commit = _read_ref_commit(git_dir, ref)
        if commit is not None:
            return commit
    return None


def read_head_commit(path: Path) -> str | None:
    """
    直接解析 Git 目录读取 HEAD 指向的提交, 不启动 Git 进程

    Args:
        path (Path):
            仓库路径

    Returns:
        str | None: 当前提交哈希, 路径不是 Git 仓库或无法解析 HEAD 时返回 None
    """
    git_dir = _resolve_git_dir(Path(path))
    if git_dir is None:
        return None
    return _read_head_commit(git_dir)
