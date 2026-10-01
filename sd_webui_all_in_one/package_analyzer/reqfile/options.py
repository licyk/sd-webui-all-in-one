"""依赖文件中的命令行风格选项解析

选项表与 pip 的 ``pip._internal.req.req_file`` 中的 ``SUPPORTED_OPTIONS`` /
``SUPPORTED_OPTIONS_REQ`` 保持一致.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from sd_webui_all_in_one.package_analyzer.errors import UnsupportedOption


@dataclass(frozen=True)
class OptionSpec:
    """选项定义

    Attributes:
        dest (str):
            选项的归属字段名
        takes_value (bool):
            选项是否需要参数值
        per_requirement (bool):
            是否为附加在单个依赖声明上的选项
    """

    dest: str
    takes_value: bool = True
    per_requirement: bool = False


LONG_OPTIONS: dict[str, OptionSpec] = {
    "--index-url": OptionSpec("index_url"),
    "--pypi-url": OptionSpec("index_url"),
    "--extra-index-url": OptionSpec("extra_index_urls"),
    "--no-index": OptionSpec("no_index", takes_value=False),
    "--constraint": OptionSpec("constraints"),
    "--requirement": OptionSpec("requirements"),
    "--editable": OptionSpec("editables"),
    "--find-links": OptionSpec("find_links"),
    "--no-binary": OptionSpec("no_binary"),
    "--only-binary": OptionSpec("only_binary"),
    "--prefer-binary": OptionSpec("prefer_binary", takes_value=False),
    "--require-hashes": OptionSpec("require_hashes", takes_value=False),
    "--no-require-hashes": OptionSpec("no_require_hashes", takes_value=False),
    "--pre": OptionSpec("pre", takes_value=False),
    "--all-releases": OptionSpec("all_releases"),
    "--only-final": OptionSpec("only_final"),
    "--trusted-host": OptionSpec("trusted_hosts"),
    "--use-feature": OptionSpec("features"),
    "--hash": OptionSpec("hashes", per_requirement=True),
    "--config-settings": OptionSpec("config_settings", per_requirement=True),
}
"""依赖文件支持的长选项"""

SHORT_OPTIONS: dict[str, OptionSpec] = {
    "-i": LONG_OPTIONS["--index-url"],
    "-c": LONG_OPTIONS["--constraint"],
    "-r": LONG_OPTIONS["--requirement"],
    "-e": LONG_OPTIONS["--editable"],
    "-f": LONG_OPTIONS["--find-links"],
    "-C": LONG_OPTIONS["--config-settings"],
}
"""依赖文件支持的短选项"""


@dataclass(frozen=True)
class ParsedOption:
    """解析后的单个选项

    Attributes:
        name (str):
            选项的规范长名称, 如 ``--index-url``
        dest (str):
            选项的归属字段名
        value (str | None):
            选项参数值, 开关型选项为 ``None``
        per_requirement (bool):
            是否为附加在单个依赖声明上的选项
    """

    name: str
    dest: str
    value: str | None
    per_requirement: bool


def split_args_and_options(
    line: str,
) -> tuple[str, str]:
    """将逻辑行拆分为依赖声明部分与选项部分

    从第一个以 ``-`` 开头的空格分隔片段开始, 之后的内容均视为选项.

    使用示例:
        ```python
        split_args_and_options("foo==1.0 --hash=sha256:abc")
        # ("foo==1.0", "--hash=sha256:abc")
        split_args_and_options("-e ./local")
        # ("", "-e ./local")
        ```

    Args:
        line (str):
            逻辑行内容

    Returns:
        tuple[str, str]: ``(依赖声明部分, 选项部分)``
    """
    tokens = line.split(" ")
    args: list[str] = []
    options = tokens[:]
    for token in tokens:
        if token.startswith("-"):
            break
        args.append(token)
        options.pop(0)
    return " ".join(args).strip(), " ".join(options).strip()


def _resolve_long_option(
    name: str,
) -> tuple[str, OptionSpec]:
    """查找长选项, 支持无歧义的前缀缩写 (与 optparse 行为一致)

    Args:
        name (str):
            长选项名, 如 ``--index-url`` 或缩写 ``--index``

    Returns:
        tuple[str, OptionSpec]: ``(规范长名称, 选项定义)``

    Raises:
        UnsupportedOption:
            选项不受支持或缩写存在歧义时
    """
    if name in LONG_OPTIONS:
        return name, LONG_OPTIONS[name]
    candidates = [option for option in LONG_OPTIONS if option.startswith(name)]
    if len(candidates) == 1:
        return candidates[0], LONG_OPTIONS[candidates[0]]
    if candidates:
        raise UnsupportedOption(f"选项 {name!r} 存在歧义, 可能为: {', '.join(sorted(candidates))}")
    raise UnsupportedOption(f"依赖文件不支持的选项: {name!r}")


def parse_options(
    options_text: str,
) -> tuple[list[ParsedOption], list[str]]:
    """解析逻辑行中的选项部分

    支持 ``--opt value``, ``--opt=value``, ``-o value``, ``-ovalue`` 四种写法.

    Args:
        options_text (str):
            选项部分的文本

    Returns:
        tuple[list[ParsedOption], list[str]]: ``(选项列表, 未被任何选项消耗的多余参数)``

    Raises:
        UnsupportedOption:
            选项不受支持, 缺少参数值, 或引号未闭合时
    """
    try:
        tokens = shlex.split(options_text)
    except ValueError as e:
        raise UnsupportedOption(f"选项无法解析: {e}") from e

    options: list[ParsedOption] = []
    leftovers: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1

        value: str | None = None
        if token.startswith("--") and len(token) > 2:
            raw_name, separator, inline_value = token.partition("=")
            name, spec = _resolve_long_option(raw_name)
            if separator:
                value = inline_value
        elif token.startswith("-") and len(token) > 1:
            short_name = token[:2]
            if short_name not in SHORT_OPTIONS:
                raise UnsupportedOption(f"依赖文件不支持的选项: {short_name!r}")
            spec = SHORT_OPTIONS[short_name]
            name = next(long_name for long_name, long_spec in LONG_OPTIONS.items() if long_spec is spec)
            if len(token) > 2:
                value = token[2:]
        else:
            leftovers.append(token)
            continue

        if spec.takes_value:
            if value is None:
                if index >= len(tokens):
                    raise UnsupportedOption(f"选项 {name!r} 缺少参数值")
                value = tokens[index]
                index += 1
        elif value is not None:
            raise UnsupportedOption(f"选项 {name!r} 不接受参数值")

        options.append(ParsedOption(name=name, dest=spec.dest, value=value, per_requirement=spec.per_requirement))

    return options, leftovers
