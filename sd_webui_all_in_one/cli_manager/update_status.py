"""WebUI 更新检查命令行输出工具。"""

from dataclasses import asdict
from typing import Any

from sd_webui_all_in_one.base_manager.snapshot import json_safe
from sd_webui_all_in_one.base_manager.version_manager import WebUiUpdateStatus


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
            WebUI 更新检查函数返回的结果。

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


def output_update_check_result(status: WebUiUpdateStatus) -> dict[str, Any]:
    """输出 WebUI 更新检查结果。

    Args:
        status (WebUiUpdateStatus): 真实 WebUI 更新检查函数的返回值。

    Returns:
        dict[str, Any]: 结构化更新检查结果。

    Raises:
        TypeError: 当序列化结果不是字典时。
    """
    serialized = json_safe(asdict(status))
    if not isinstance(serialized, dict):
        raise TypeError("Expected update status object")
    result = serialized
    print(format_update_check_result(result))
    return result
