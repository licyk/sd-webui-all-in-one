"""检查一个 pip 安装目录中的依赖。"""

import sys
from functools import partial
from pathlib import Path

from sd_webui_all_in_one.package_analyzer import CheckStatus, check_requirements_file, get_installed_distribution, parse_requirements_file


def check_requirements(file: Path, target: Path) -> None:
    """检查依赖文件, 仅在需要安装时以状态码 3 退出。

    Args:
        file (Path): 依赖声明文件。
        target (Path): pip 的安装目录。

    Raises:
        SystemExit: 无法检查时为 1, 依赖未满足时为 3。
    """
    try:
        parsed = parse_requirements_file(file)
    except (OSError, UnicodeError) as error:
        raise SystemExit(str(error)) from error
    for diagnostic in parsed.diagnostics:
        print(diagnostic, file=sys.stderr)
    if any(item.severity == "error" for item in parsed.diagnostics):
        raise SystemExit(1)
    results = check_requirements_file(parsed, lookup=partial(get_installed_distribution, path=target))
    for result in results:
        if result.status in (CheckStatus.UNKNOWN, CheckStatus.UNSATISFIED):
            print(result, file=sys.stderr)
    if any(not result.ok for result in results):
        raise SystemExit(3)
