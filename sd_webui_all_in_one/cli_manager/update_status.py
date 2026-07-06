"""WebUI 更新检查命令行输出工具。"""

from pathlib import Path
from typing import Any

from sd_webui_all_in_one.api_server.adapters import WebUiApiType, get_webui_adapter


def _short_value(value: Any) -> str:
    if value is None or value == "":
        return "-"
    text = str(value)
    return text[:12] if len(text) > 12 and all(char in "0123456789abcdefABCDEF" for char in text[:12]) else text


def _format_git_status(item: dict[str, Any]) -> list[str]:
    status = "有更新" if item.get("has_update") else "已是最新"
    if item.get("error"):
        status = f"无法检查: {item['error']}"
    if item.get("ahead", 0) and item.get("behind", 0):
        status = f"本地和远程都有变更, 本地领先 {item.get('ahead')} 个提交, 落后 {item.get('behind')} 个提交"
    elif item.get("behind", 0):
        status = f"有更新, 落后 {item.get('behind')} 个提交"
    elif item.get("ahead", 0):
        status = f"本地领先远程 {item.get('ahead')} 个提交"

    return [
        f"  {item.get('name') or '-'}: {status}",
        f"    branch: {item.get('branch') or '-'}",
        f"    remote: {item.get('remote_branch') or '-'}",
        f"    local:  {_short_value(item.get('current_commit'))}",
        f"    remote: {_short_value(item.get('remote_commit'))}",
    ]


def _format_pypi_status(item: dict[str, Any]) -> list[str]:
    if item.get("error"):
        status = f"无法检查: {item['error']}"
    elif item.get("has_update"):
        status = "有更新"
    else:
        status = "已是最新"
    return [
        f"  {item.get('name') or item.get('package_name') or '-'}: {status}",
        f"    current: {item.get('current_version') or '-'}",
        f"    latest:  {item.get('latest_version') or '-'}",
    ]


def format_update_check_result(result: dict[str, Any]) -> str:
    """格式化更新检查结果。

    Args:
        result (dict[str, Any]):
            API adapter 返回的更新检查结果。

    Returns:
        str: 命令行显示文本。
    """
    lines: list[str] = []
    kernel = result.get("kernel")
    if isinstance(kernel, dict):
        lines.append("Kernel:")
        if kernel.get("source_type") == "pypi":
            lines.extend(_format_pypi_status(kernel))
        else:
            lines.extend(_format_git_status(kernel))

    extensions = result.get("extensions")
    if isinstance(extensions, list):
        if lines:
            lines.append("")
        lines.append("Extensions:")
        if extensions:
            for item in extensions:
                if isinstance(item, dict):
                    lines.extend(_format_git_status(item))
        else:
            lines.append("  无扩展或当前 WebUI 不支持扩展更新检查")

    raw_summary = result.get("summary")
    summary: dict[str, Any] = raw_summary if isinstance(raw_summary, dict) else {}
    if lines:
        lines.append("")
    lines.append("Summary:")
    lines.append(f"  has_update: {bool(summary.get('has_update', False))}")
    lines.append(f"  kernel_has_update: {bool(summary.get('kernel_has_update', False))}")
    lines.append(f"  extension_update_count: {int(summary.get('extension_update_count', 0))}")
    lines.append(f"  skipped_count: {int(summary.get('skipped_count', 0))}")
    lines.append(f"  error_count: {int(summary.get('error_count', 0))}")
    return "\n".join(lines)


def check_webui_updates(
    webui_type: WebUiApiType,
    webui_path: Path,
    include_kernel: bool = True,
    include_extensions: bool = True,
    use_github_mirror: bool = False,
    custom_github_mirror: str | list[str] | None = None,
    use_pypi_mirror: bool = False,
    fetch: bool = True,
) -> dict[str, Any]:
    """检查 WebUI 内核和扩展更新并输出文本结果。

    Args:
        webui_type (WebUiApiType):
            WebUI 类型。
        webui_path (Path):
            WebUI 根目录。
        include_kernel (bool):
            是否检查内核。
        include_extensions (bool):
            是否检查扩展。
        use_github_mirror (bool):
            是否启用 GitHub 镜像源。
        custom_github_mirror (str | list[str] | None):
            自定义 GitHub 镜像源。
        use_pypi_mirror (bool):
            是否启用 PyPI 镜像源。
        fetch (bool):
            是否拉取远程引用。

    Returns:
        dict[str, Any]: 结构化更新检查结果。
    """
    result = get_webui_adapter(webui_type).check_updates(
        webui_path,
        options={
            "include_kernel": include_kernel,
            "include_extensions": include_extensions,
            "use_github_mirror": use_github_mirror,
            "custom_github_mirror": custom_github_mirror,
            "use_pypi_mirror": use_pypi_mirror,
            "fetch": fetch,
        },
    )
    print(format_update_check_result(result))
    return result
