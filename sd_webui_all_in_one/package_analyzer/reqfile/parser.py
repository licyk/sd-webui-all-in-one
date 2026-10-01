"""依赖文件解析器

将 ``requirements.txt`` 格式的依赖文件解析为依赖条目, 约束条目与全局选项.
该格式没有对应的 PEP 规范, 行为以 pip 的 ``pip._internal.req.req_file`` 与
``pip._internal.req.constructors`` 为准.

参考:
    - https://pip.pypa.io/en/stable/reference/requirements-file-format/
"""

from __future__ import annotations

import dataclasses
import os
import posixpath
import re
from pathlib import Path
from typing import (
    Any,
    Mapping,
)
from urllib.parse import (
    parse_qs,
    unquote,
    urljoin,
    urlsplit,
)
from urllib.request import url2pathname

from sd_webui_all_in_one.package_analyzer.errors import (
    Diagnostic,
    InvalidMarker,
    InvalidRequirement,
    InvalidWheelFilename,
    NestedFileNotFound,
    RecursiveInclude,
    RequirementsFileError,
    UnsupportedOption,
)
from sd_webui_all_in_one.package_analyzer.filenames import (
    WheelFilename,
    is_archive_filename,
)
from sd_webui_all_in_one.package_analyzer.local_project import (
    get_local_project_name,
    is_installable_dir,
)
from sd_webui_all_in_one.package_analyzer.markers import Marker
from sd_webui_all_in_one.package_analyzer.names import (
    is_valid_name,
    normalize_name,
)
from sd_webui_all_in_one.package_analyzer.reqfile.lexer import (
    LogicalLine,
    decode_requirements,
    iter_logical_lines,
)
from sd_webui_all_in_one.package_analyzer.reqfile.model import (
    EntryKind,
    RequirementEntry,
    RequirementsFile,
    SourceLocation,
)
from sd_webui_all_in_one.package_analyzer.reqfile.options import (
    ParsedOption,
    parse_options,
    split_args_and_options,
)
from sd_webui_all_in_one.package_analyzer.requirement import Requirement


_URL_REGEX = re.compile(r"^(?:(?:git|hg|svn|bzr)\+[a-z0-9.+-]+|https?|ftp|file):", re.IGNORECASE)
_INCLUDE_URL_REGEX = re.compile(r"^(http|https|file):", re.IGNORECASE)
_EXTRAS_REGEX = re.compile(r"^(.+)(\[[^\]]+\])$")
_URL_MARKER_SEPARATOR_REGEX = re.compile(r"\s+;\s*|;\s+")
_HASH_NAMES: tuple[str, ...] = ("sha1", "sha224", "sha256", "sha384", "sha512", "md5")


def is_url(
    text: str,
) -> bool:
    """判断文本是否为 pip 可识别的 URL (含 ``git+https://`` 等 VCS URL)

    Args:
        text (str):
            待判断文本

    Returns:
        bool: 文本为 URL 时返回 ``True``
    """
    return _URL_REGEX.match(text) is not None


def looks_like_path(
    text: str,
) -> bool:
    """判断文本是否看起来像本地路径

    包含路径分隔符或以 ``.`` 开头时视为路径 (与 pip 的判断一致).

    Args:
        text (str):
            待判断文本

    Returns:
        bool: 文本看起来像路径时返回 ``True``
    """
    if os.path.sep in text or "/" in text:
        return True
    if os.path.altsep is not None and os.path.altsep in text:
        return True
    return text.startswith(".")


def _strip_extras(
    text: str,
) -> tuple[str, tuple[str, ...]]:
    """拆分路径 (或 egg 名) 末尾的 ``[extras]``

    Args:
        text (str):
            形如 ``./pkg[dev,test]`` 的文本

    Returns:
        tuple[str, tuple[str, ...]]: ``(去除 extras 的文本, extras 列表)``
    """
    match = _EXTRAS_REGEX.match(text)
    if match is None:
        return text, ()
    extras = tuple(extra.strip() for extra in match.group(2)[1:-1].split(",") if extra.strip())
    return match.group(1), extras


def _update_control(
    value: str,
    target: set[str],
    other: set[str],
) -> None:
    """更新 ``--no-binary`` / ``--only-binary`` 这类互斥的软件包名集合

    Args:
        value (str):
            选项值: 逗号分隔的软件包名, ``:all:`` 或 ``:none:``
        target (set[str]):
            选项对应的集合
        other (set[str]):
            与之互斥的集合
    """
    names = value.split(",")
    while ":all:" in names:
        other.clear()
        target.clear()
        target.add(":all:")
        del names[: names.index(":all:") + 1]
        if ":none:" not in names:
            return
    for name in names:
        if name == ":none:":
            target.clear()
            continue
        if not name:
            continue
        name = normalize_name(name)
        other.discard(name)
        target.add(name)


class _FileParser:
    """依赖文件解析过程的状态与实现"""

    def __init__(
        self,
        base_dir: Path,
        strict: bool,
        environ: Mapping[str, str] | None,
        expand_env: bool,
        follow_includes: bool,
    ) -> None:
        """初始化解析器

        Args:
            base_dir (Path):
                解析依赖条目中相对路径的基准目录
            strict (bool):
                是否在遇到无效内容时立即抛出异常
            environ (Mapping[str, str] | None):
                用于展开 ``${VAR}`` 的环境变量映射
            expand_env (bool):
                是否展开环境变量
            follow_includes (bool):
                是否读取 ``-r`` / ``-c`` 引用的嵌套文件
        """
        self.base_dir = base_dir
        self.strict = strict
        self.environ = environ
        self.expand_env = expand_env
        self.follow_includes = follow_includes
        self.result = RequirementsFile()
        self._stack: list[str] = []

    def warn(
        self,
        message: str,
        path: str | None,
        lineno: int | None,
    ) -> None:
        """记录警告. 警告表示条目有效但无法完全处理, 任何模式下都不会中断解析

        Args:
            message (str):
                警告内容
            path (str | None):
                相关文件路径
            lineno (int | None):
                相关行号
        """
        self.result.diagnostics.append(Diagnostic("warning", message, path, lineno))

    def fail(
        self,
        message: str,
        path: str | None,
        lineno: int | None,
        error_type: type[RequirementsFileError] = RequirementsFileError,
    ) -> None:
        """记录错误. 严格模式下抛出异常, 否则记录后继续解析

        Args:
            message (str):
                错误内容
            path (str | None):
                相关文件路径
            lineno (int | None):
                相关行号
            error_type (type[RequirementsFileError]):
                严格模式下抛出的异常类型

        Raises:
            RequirementsFileError:
                严格模式下
        """
        if self.strict:
            raise error_type(message, path, lineno)
        self.result.diagnostics.append(Diagnostic("error", message, path, lineno))

    def parse_file(
        self,
        path: str,
        constraint: bool,
        parent: SourceLocation | None = None,
    ) -> None:
        """读取并解析一个依赖文件

        Args:
            path (str):
                依赖文件路径
            constraint (bool):
                文件中的条目是否为约束
            parent (SourceLocation | None):
                引用此文件的位置, 根文件为 ``None``

        Raises:
            OSError:
                根文件无法读取时
            UnicodeDecodeError:
                根文件无法解码时
            RequirementsFileError:
                严格模式下遇到无效内容时
        """
        parent_path = parent.path if parent is not None else None
        parent_lineno = parent.lineno if parent is not None else None

        resolved = os.path.normpath(os.path.abspath(path))
        if resolved in self._stack:
            chain = " -> ".join([*self._stack, resolved])
            self.fail(f"依赖文件存在循环引用: {chain}", parent_path, parent_lineno, RecursiveInclude)
            return

        try:
            data = Path(resolved).read_bytes()
        except OSError as e:
            if parent is None:
                raise
            self.fail(f"无法读取嵌套依赖文件 '{resolved}': {e}", parent_path, parent_lineno, NestedFileNotFound)
            return

        try:
            text = decode_requirements(data)
        except UnicodeDecodeError as e:
            if parent is None:
                raise
            self.fail(f"无法解码嵌套依赖文件 '{resolved}': {e}", parent_path, parent_lineno, NestedFileNotFound)
            return

        if parent is not None:
            self.result.includes.append(resolved)

        self._stack.append(resolved)
        try:
            self.parse_text(text, resolved, constraint)
        finally:
            self._stack.pop()

    def parse_text(
        self,
        text: str,
        path: str | None,
        constraint: bool,
    ) -> None:
        """解析依赖文件文本

        Args:
            text (str):
                依赖文件文本
            path (str | None):
                文本对应的文件路径
            constraint (bool):
                文本中的条目是否为约束
        """
        for line in iter_logical_lines(text, self.environ, self.expand_env):
            self._parse_line(line, path, constraint)

    def _parse_line(
        self,
        line: LogicalLine,
        path: str | None,
        constraint: bool,
    ) -> None:
        """解析一条逻辑行

        Args:
            line (LogicalLine):
                逻辑行
            path (str | None):
                所在文件路径
            constraint (bool):
                所在文件是否为约束文件
        """
        args, options_text = split_args_and_options(line.text)

        options: list[ParsedOption] = []
        leftovers: list[str] = []
        try:
            options, leftovers = parse_options(options_text)
        except UnsupportedOption as e:
            self.fail(e.message, path, line.lineno, UnsupportedOption)
            if not args:
                return

        if leftovers:
            self.warn(f"已忽略选项之后的多余内容: {' '.join(leftovers)}", path, line.lineno)

        def values(dest: str) -> list[str]:
            return [option.value for option in options if option.dest == dest and option.value is not None]

        source = SourceLocation(path, line.lineno)

        if args:
            ignored = [option.name for option in options if not option.per_requirement]
            if ignored:
                self.warn(f"依赖声明所在行的全局选项已忽略: {' '.join(ignored)}", path, line.lineno)
            self._add_entry(args, line, source, constraint, False, tuple(values("hashes")), tuple(values("config_settings")))
            return

        editables = values("editables")
        if editables:
            self._add_entry(editables[0], line, source, constraint, True, (), tuple(values("config_settings")))
            return

        requirements = values("requirements")
        if requirements:
            self._include(requirements[0], source, False)
            return

        constraints = values("constraints")
        if constraints:
            self._include(constraints[0], source, True)
            return

        for option in options:
            self._apply_global_option(option)

    def _apply_global_option(
        self,
        option: ParsedOption,
    ) -> None:
        """将全局选项写入解析结果

        Args:
            option (ParsedOption):
                解析后的选项
        """
        file_options = self.result.options
        value = option.value or ""
        if option.dest == "index_url":
            file_options.index_url = value
        elif option.dest == "extra_index_urls":
            file_options.extra_index_urls.append(value)
        elif option.dest == "no_index":
            file_options.no_index = True
        elif option.dest == "find_links":
            file_options.find_links.append(value)
        elif option.dest == "no_binary":
            _update_control(value, file_options.no_binary, file_options.only_binary)
        elif option.dest == "only_binary":
            _update_control(value, file_options.only_binary, file_options.no_binary)
        elif option.dest == "prefer_binary":
            file_options.prefer_binary = True
        elif option.dest == "require_hashes":
            file_options.require_hashes = True
        elif option.dest == "no_require_hashes":
            file_options.require_hashes = False
        elif option.dest == "pre":
            file_options.pre = True
        elif option.dest == "all_releases":
            _update_control(value, file_options.all_releases, file_options.only_final)
        elif option.dest == "only_final":
            _update_control(value, file_options.only_final, file_options.all_releases)
        elif option.dest == "trusted_hosts":
            file_options.trusted_hosts.append(value)
        elif option.dest == "features":
            file_options.features.append(value)

    def _include(
        self,
        target: str,
        source: SourceLocation,
        constraint: bool,
    ) -> None:
        """处理 ``-r`` / ``-c`` 引用的嵌套文件

        嵌套文件的相对路径相对于引用它的文件所在目录解析.

        Args:
            target (str):
                嵌套文件路径或 URL
            source (SourceLocation):
                引用位置
            constraint (bool):
                是否为约束文件 (``-c``)
        """
        option = "-c" if constraint else "-r"
        if not self.follow_includes:
            self.warn(f"未读取嵌套依赖文件: {option} {target}", source.path, source.lineno)
            return

        if _INCLUDE_URL_REGEX.match(target):
            resolved = target
        elif source.path is not None and _INCLUDE_URL_REGEX.match(source.path):
            resolved = urljoin(source.path, target)
        elif source.path is not None:
            resolved = os.path.join(os.path.dirname(source.path), target)
        else:
            resolved = os.path.join(self.base_dir, target)

        scheme_match = _INCLUDE_URL_REGEX.match(resolved)
        if scheme_match is not None:
            if scheme_match.group(1).lower() != "file":
                self.warn(f"未读取远程依赖文件: {option} {resolved}", source.path, source.lineno)
                return
            resolved = url2pathname(unquote(urlsplit(resolved).path))

        self.parse_file(resolved, constraint, parent=source)

    def _add_entry(
        self,
        text: str,
        line: LogicalLine,
        source: SourceLocation,
        constraint: bool,
        editable: bool,
        hashes: tuple[str, ...],
        config_settings: tuple[str, ...],
    ) -> None:
        """将依赖声明文本转换为依赖条目并加入解析结果

        Args:
            text (str):
                依赖声明文本 (不含选项)
            line (LogicalLine):
                所在逻辑行
            source (SourceLocation):
                所在位置
            constraint (bool):
                是否为约束条目
            editable (bool):
                是否为可编辑条目
            hashes (tuple[str, ...]):
                ``--hash`` 选项的值
            config_settings (tuple[str, ...]):
                ``--config-settings`` 选项的值
        """
        common: dict[str, Any] = {
            "raw": text,
            "source": source,
            "editable": editable,
            "constraint": constraint,
            "hashes": hashes,
            "config_settings": config_settings,
            "directives": line.directives,
        }
        entry = self._classify(text, common)
        if entry is None:
            return

        if constraint:
            problem: str | None = None
            if entry.editable:
                problem = "可编辑条目不能作为约束"
            elif entry.name is None:
                problem = "未命名的条目不能作为约束"
            elif entry.extras:
                problem = "约束不能带有 extras"
            if problem is not None:
                self.fail(f"{problem}: {text}", source.path, source.lineno)
                return
            self.result.constraints.append(entry)
        else:
            self.result.entries.append(entry)

    def _classify(
        self,
        text: str,
        common: dict[str, Any],
    ) -> RequirementEntry | None:
        """判断依赖声明文本的类别并构造依赖条目

        Args:
            text (str):
                依赖声明文本
            common (dict[str, Any]):
                各类条目共用的字段

        Returns:
            RequirementEntry | None: 依赖条目, 文本无效时为 ``None``
        """
        source: SourceLocation = common["source"]

        if common["editable"]:
            target, extras = _strip_extras(text)
            if is_url(target):
                return self._url_entry(target, extras, None, common)
            return self._path_entry(target, extras, None, common)

        if is_url(text):
            parts = _URL_MARKER_SEPARATOR_REGEX.split(text, maxsplit=1)
        else:
            parts = text.split(";", 1)
        body = parts[0].strip()
        marker: Marker | None = None
        if len(parts) > 1:
            try:
                marker = Marker.parse(parts[1])
            except InvalidMarker as e:
                self.fail(f"环境标记不合法: {str(e).splitlines()[0]}", source.path, source.lineno)
                return None

        if is_url(body):
            return self._url_entry(body, (), marker, common)

        stripped, extras = _strip_extras(body)
        candidate = self._resolve_path(stripped)
        if looks_like_path(stripped) and candidate.is_dir():
            return self._path_entry(stripped, extras, marker, common)
        if is_archive_filename(stripped):
            if candidate.is_file():
                return self._path_entry(stripped, extras, marker, common)
            # "name @ path.whl" 形式的直接引用仍按依赖声明解析
            if "@" not in body or looks_like_path(body.split("@", 1)[0]):
                return self._path_entry(stripped, extras, marker, common)

        try:
            requirement = Requirement.parse(body)
        except InvalidRequirement as e:
            if looks_like_path(body):
                self.fail(f"'{body}' 看起来是一个路径, 但该路径不存在", source.path, source.lineno)
            else:
                self.fail(f"无法解析依赖声明 '{text}': {e.message}", source.path, source.lineno)
            return None

        if marker is not None:
            requirement = dataclasses.replace(requirement, marker=marker)

        return RequirementEntry(
            kind=EntryKind.NAMED,
            requirement=requirement,
            name=requirement.name,
            extras=requirement.extras,
            url=requirement.url,
            marker=requirement.marker,
            **common,
        )

    def _resolve_path(
        self,
        target: str,
    ) -> Path:
        """将依赖条目中的路径解析为绝对路径

        Args:
            target (str):
                路径文本

        Returns:
            Path: 规范化后的绝对路径
        """
        return Path(os.path.normpath(os.path.join(self.base_dir, target)))

    def _url_entry(
        self,
        url: str,
        extras: tuple[str, ...],
        marker: Marker | None,
        common: dict[str, Any],
    ) -> RequirementEntry | None:
        """构造 URL 条目

        Args:
            url (str):
                URL
            extras (tuple[str, ...]):
                请求的 extras
            marker (Marker | None):
                环境标记
            common (dict[str, Any]):
                各类条目共用的字段

        Returns:
            RequirementEntry | None: 依赖条目, URL 无效时为 ``None``
        """
        source: SourceLocation = common["source"]
        split = urlsplit(url)
        scheme = split.scheme.lower()

        if scheme == "file":
            return self._path_entry(url2pathname(unquote(split.path)), extras, marker, common)

        vcs = scheme.split("+", 1)[0] if "+" in scheme else None
        if common["editable"] and vcs is None:
            self.fail(f"可编辑条目必须是本地项目路径或 VCS URL: {url}", source.path, source.lineno)
            return None

        fragment = parse_qs(split.fragment, keep_blank_values=True)
        hashes = tuple(f"{name}:{fragment[name][0]}" for name in _HASH_NAMES if name in fragment)
        subdirectory = fragment["subdirectory"][0] if "subdirectory" in fragment else None

        url_path = split.path
        revision: str | None = None
        if vcs is not None and "@" in url_path:
            url_path, revision = url_path.rsplit("@", 1)

        name: str | None = None
        version = None
        if "egg" in fragment:
            egg_name, egg_extras = _strip_extras(fragment["egg"][0])
            if is_valid_name(egg_name):
                name = egg_name
                extras = extras or egg_extras
            else:
                self.warn(f"URL 中的 '#egg=' 片段不是合法的软件包名: {fragment['egg'][0]}", source.path, source.lineno)
        elif vcs is None:
            filename = posixpath.basename(unquote(url_path))
            if filename.endswith(".whl"):
                try:
                    wheel = WheelFilename.parse(filename)
                except InvalidWheelFilename as e:
                    self.fail(str(e), source.path, source.lineno)
                    return None
                name = wheel.distribution
                version = wheel.version

        merged = dict(common)
        merged["hashes"] = tuple(common["hashes"]) + hashes
        return RequirementEntry(
            kind=EntryKind.URL,
            name=name,
            extras=extras,
            version=version,
            url=url,
            vcs=vcs,
            revision=revision,
            subdirectory=subdirectory,
            marker=marker,
            **merged,
        )

    def _path_entry(
        self,
        target: str,
        extras: tuple[str, ...],
        marker: Marker | None,
        common: dict[str, Any],
    ) -> RequirementEntry | None:
        """构造本地路径条目

        路径不存在或目录不可安装时只产生警告, 条目仍会保留.

        Args:
            target (str):
                路径文本
            extras (tuple[str, ...]):
                请求的 extras
            marker (Marker | None):
                环境标记
            common (dict[str, Any]):
                各类条目共用的字段

        Returns:
            RequirementEntry | None: 依赖条目, Wheel 文件名无效时为 ``None``
        """
        source: SourceLocation = common["source"]
        path = self._resolve_path(target)

        name: str | None = None
        version = None
        if path.is_dir():
            if not is_installable_dir(path):
                self.warn(f"目录 '{path}' 不可安装: 未找到 pyproject.toml 或 setup.py", source.path, source.lineno)
            name = get_local_project_name(path)
        elif path.is_file():
            if common["editable"]:
                self.warn(f"可编辑条目应为本地项目目录, 而 '{path}' 是一个文件", source.path, source.lineno)
            if path.name.endswith(".whl"):
                try:
                    wheel = WheelFilename.parse(path.name)
                except InvalidWheelFilename as e:
                    self.fail(str(e), source.path, source.lineno)
                    return None
                name = wheel.distribution
                version = wheel.version
        else:
            self.warn(f"路径 '{path}' 不存在", source.path, source.lineno)

        return RequirementEntry(
            kind=EntryKind.PATH,
            name=name,
            extras=extras,
            version=version,
            path=path,
            marker=marker,
            **common,
        )


def parse_requirements_file(
    path: str | Path,
    constraint: bool = False,
    strict: bool = False,
    environ: Mapping[str, str] | None = None,
    expand_env: bool = True,
    base_dir: str | Path | None = None,
    follow_includes: bool = True,
) -> RequirementsFile:
    """解析依赖文件

    使用示例:
        ```python
        parsed = parse_requirements_file("requirements.txt")
        for entry in parsed.entries:
            print(entry.source, entry.kind, entry.name)
        for diagnostic in parsed.diagnostics:
            print(diagnostic.severity, diagnostic)
        ```

    Args:
        path (str | Path):
            依赖文件路径
        constraint (bool):
            是否将文件作为约束文件解析
        strict (bool):
            是否在遇到无效内容 (无法解析的依赖声明, 不支持的选项, 循环引用,
            无法读取的嵌套文件) 时立即抛出异常. 默认记录为诊断信息并继续解析.
            无法验证但有效的条目 (如路径不存在的 ``-e .``) 在任何模式下都只产生警告
        environ (Mapping[str, str] | None):
            用于展开 ``${VAR}`` 的环境变量映射, 为 ``None`` 时使用 ``os.environ``
        expand_env (bool):
            是否展开 ``${VAR}`` 环境变量引用
        base_dir (str | Path | None):
            解析依赖条目中相对路径的基准目录, 为 ``None`` 时使用依赖文件所在目录
        follow_includes (bool):
            是否读取 ``-r`` / ``-c`` 引用的嵌套文件

    Returns:
        RequirementsFile: 解析结果

    Raises:
        OSError:
            依赖文件不存在或无法读取时
        UnicodeDecodeError:
            依赖文件无法解码时
        RequirementsFileError:
            严格模式下遇到无效内容时
    """
    resolved = os.path.normpath(os.path.abspath(os.fspath(path)))
    parser = _FileParser(
        base_dir=Path(base_dir) if base_dir is not None else Path(resolved).parent,
        strict=strict,
        environ=environ,
        expand_env=expand_env,
        follow_includes=follow_includes,
    )
    parser.result.path = resolved
    parser.parse_file(resolved, constraint)
    return parser.result


def parse_requirements_text(
    text: str,
    path: str | Path | None = None,
    constraint: bool = False,
    strict: bool = False,
    environ: Mapping[str, str] | None = None,
    expand_env: bool = True,
    base_dir: str | Path | None = None,
    follow_includes: bool = True,
) -> RequirementsFile:
    """解析依赖文件格式的文本

    Args:
        text (str):
            依赖文件格式的文本
        path (str | Path | None):
            文本对应的文件路径, 用于诊断信息以及解析嵌套文件的相对路径
        constraint (bool):
            是否将文本作为约束文件解析
        strict (bool):
            是否在遇到无效内容时立即抛出异常
        environ (Mapping[str, str] | None):
            用于展开 ``${VAR}`` 的环境变量映射, 为 ``None`` 时使用 ``os.environ``
        expand_env (bool):
            是否展开 ``${VAR}`` 环境变量引用
        base_dir (str | Path | None):
            解析相对路径的基准目录. 为 ``None`` 时使用 ``path`` 所在目录, ``path`` 也未提供时使用当前工作目录
        follow_includes (bool):
            是否读取 ``-r`` / ``-c`` 引用的嵌套文件

    Returns:
        RequirementsFile: 解析结果

    Raises:
        RequirementsFileError:
            严格模式下遇到无效内容时
    """
    resolved = os.path.normpath(os.path.abspath(os.fspath(path))) if path is not None else None
    if base_dir is not None:
        base = Path(base_dir)
    elif resolved is not None:
        base = Path(resolved).parent
    else:
        base = Path.cwd()

    parser = _FileParser(
        base_dir=base,
        strict=strict,
        environ=environ,
        expand_env=expand_env,
        follow_includes=follow_includes,
    )
    parser.result.path = resolved
    if resolved is not None:
        parser._stack.append(resolved)
    parser.parse_text(text, resolved, constraint)
    return parser.result
